"""LLM 统一接入层。基于 litellm, 自动兼容 OpenAI / Anthropic / Gemini /
DeepSeek / 通义 / 智谱 / 月之暗面 / Ollama 等几乎所有在线与本地模型。

只要在模型配置里给出 model 前缀与对应 api_key / api_base,即可自动路由。
"""
from __future__ import annotations

import os
from typing import Any, AsyncIterator, Optional

try:
    import litellm  # type: ignore
    # 避免部分 provider 误判抛错
    litellm.set_verbose = False
    litellm.drop_params = True
    litellm.modify_params = True
except Exception:  # pragma: no cover
    litellm = None  # type: ignore

from .config import ModelConfig


class LLMError(Exception):
    pass


def _prepare_env(cfg: ModelConfig) -> None:
    """根据 provider 前缀把 api_key/base 写入对应环境变量,
    litellm 会自动读取。"""
    provider = cfg.model.split("/", 1)[0].lower() if "/" in cfg.model else "openai"
    if cfg.api_key:
        if provider in ("openai",):
            os.environ["OPENAI_API_KEY"] = cfg.api_key
        elif provider in ("anthropic",):
            os.environ["ANTHROPIC_API_KEY"] = cfg.api_key
        elif provider in ("gemini",):
            os.environ["GEMINI_API_KEY"] = cfg.api_key
        elif provider in ("deepseek",):
            os.environ["DEEPSEEK_API_KEY"] = cfg.api_key
        elif provider in ("dashpipe", "dashscope"):
            os.environ["DASHSCOPE_API_KEY"] = cfg.api_key
        elif provider in ("zhipu", "glm"):
            os.environ["ZHIPUAI_API_KEY"] = cfg.api_key
        elif provider in ("moonshot",):
            os.environ["MOONSHOT_API_KEY"] = cfg.api_key
        elif provider in ("ollama",):
            os.environ["OLLAMA_API_BASE"] = cfg.api_base or "http://localhost:11434"
        elif provider in ("siliconflow",):
            os.environ["SILICONFLOW_API_KEY"] = cfg.api_key
        elif provider in ("openrouter",):
            os.environ["OPENROUTER_API_KEY"] = cfg.api_key
        elif provider in ("together_ai", "together"):
            os.environ["TOGETHERAI_API_KEY"] = cfg.api_key
        elif provider in ("fireworks_ai", "fireworks"):
            os.environ["FIREWORKS_API_KEY"] = cfg.api_key
        # openai 兼容的第三方 (如各厂兼容站) 用 openai/ 前缀 + api_base
    if cfg.api_base and provider in ("openai",):
        os.environ["OPENAI_API_BASE"] = cfg.api_base


async def chat(
    messages: list[dict],
    cfg: ModelConfig,
    *,
    tools: Optional[list[dict]] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    response_format: Optional[dict] = None,
    assistant_prefill: Optional[str] = None,
    stop: Optional[list[str]] = None,
) -> dict:
    """非流式补全。返回 {"content": str, "tool_calls": list}。

    assistant_prefill: 预填充 assistant 开头 (原理6 Prefill),强制模型从指定前缀续写,
        常用于强制只输出 JSON (填 "{")。返回的 content 已拼回 prefill。
    stop: 停止序列 (原理7 Stop Sequence),命中即停并交回控制权,常用于 ReAct loop。
    """
    if litellm is None:
        raise LLMError("litellm 未安装,请先 pip install -r requirements.txt")
    _prepare_env(cfg)
    msgs = list(messages)
    use_prefill = bool(assistant_prefill) and not response_format
    if use_prefill:
        msgs.append({"role": "assistant", "content": assistant_prefill})
    kwargs: dict[str, Any] = {
        "model": cfg.model,
        "messages": msgs,
        "temperature": temperature if temperature is not None else cfg.temperature,
        "max_tokens": max_tokens if max_tokens is not None else cfg.max_tokens,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["parallel_tool_calls"] = False
    if response_format:
        kwargs["response_format"] = response_format
    if stop:
        kwargs["stop"] = stop
    try:
        resp = await litellm.acompletion(**kwargs)
    except Exception as e:
        raise LLMError(f"LLM 调用失败: {e}") from e
    choice = resp.choices[0].message
    # prefill 模式: 模型续写在 prefill 之后,返回的 content 不含 prefill。
    # 这里不把 prefill 拼回 content —— 调用方若需要拼回(如纯文本续写场景)可自行拼。
    # 工具调用场景需要模型吐完整 JSON,拼回反而会产生 {{ 双括号杂质。
    content = choice.content or ""
    return {
        "content": content,
        "tool_calls": getattr(choice, "tool_calls", None) or [],
        "raw": resp,
    }


async def stream(
    messages: list[dict],
    cfg: ModelConfig,
    *,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    stop: Optional[list[str]] = None,
) -> AsyncIterator[str]:
    """流式补全,逐 token 产出文本 (仅文本流;工具调用走非流式)。

    stop: 停止序列 (原理7),命中即停,常用于正文续写到章节结尾标记处。
    """
    if litellm is None:
        raise LLMError("litellm 未安装")
    _prepare_env(cfg)
    # reasoning 模型 (如 agnes-2.0-flash) 会先吐 reasoning_content (思考过程, content=None),
    # 再吐 content (正文)。思考也消耗 max_tokens, 故 stream 时放大额度避免正文被截断。
    eff_max = max_tokens
    if max_tokens is not None and max_tokens < 4000:
        eff_max = max_tokens * 4
    kwargs: dict[str, Any] = {
        "model": cfg.model,
        "messages": messages,
        "temperature": temperature if temperature is not None else cfg.temperature,
        "max_tokens": eff_max if eff_max is not None else cfg.max_tokens,
        "stream": True,
    }
    if stop:
        kwargs["stop"] = stop
    try:
        stream_obj = await litellm.acompletion(**kwargs)
    except Exception as e:
        raise LLMError(f"LLM 流式调用失败: {e}") from e
    async for chunk in stream_obj:
        try:
            delta = chunk.choices[0].delta
        except Exception:
            continue
        # 只 yield 正文 content; reasoning_content (思考过程) 不输出给用户
        content = getattr(delta, "content", None)
        if content:
            yield content

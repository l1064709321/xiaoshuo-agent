"""多 agent 协同的 Codex 式 loop (整合 oh-story 7-agent 架构)。

架构:
- 主 agent (默认 orchestrator 总编) 接收用户输入,通过 delegate_to_agent 工具委派给专家
- 6 位专家 agent (story-architect/narrative-writer/character-designer/
  consistency-checker/story-explorer/worldbuilder) 各司其职,有独立系统提示词与工具子集
- 子 agent 也可再委派其他专家 (如 narrative-writer 需要新增角色 → 委派 character-designer)
- 委派深度限制 MAX_DELEGATE_DEPTH,避免无限递归
- 只读沙盒: consistency-checker 和 story-explorer 不允许调用写入类工具

事件流 (SSE):
- {type:"start", agent, input}     开始,标记当前 agent
- {type:"step", agent, tool, ...}  某个 agent 执行某工具
- {type:"delegate", from, to, task}  委派发生 (供前端展示协同)
- {type:"observation", ...}        工具结果
- {type:"token", ...}              最终回答 token 流
- {type:"done", ...}               结束
- {type:"error", ...}              错误
"""
from __future__ import annotations

import json
from typing import AsyncIterator

from . import agents, store, tools
from .config import get_settings
from .llm import chat


# 写入类工具白名单: 只读 agent 不允许调用这些
WRITE_TOOLS = {
    "generate_outline", "continue_writing", "polish", "add_element", "manage_outline",
}


def _check_sandbox(agent_name: str, tool_name: str) -> str | None:
    """检查工具调用是否符合 agent 沙盒限制。返回错误消息或 None。"""
    if agents.is_readonly(agent_name) and tool_name in WRITE_TOOLS:
        return (f"只读 agent「{agent_name}」不允许调用写入工具「{tool_name}」。"
                "请改用 query_project/load_context/quality_check 查询,或委派其他 agent 处理。")
    return None


def _build_messages(pid: str, agent_name: str = agents.DEFAULT_AGENT) -> list[dict]:
    """组装对话历史 + 项目背景 + 指定 agent 的系统提示词。"""
    msgs: list[dict] = []
    proj = store.get_project(pid)
    if proj:
        msgs.append({
            "role": "system",
            "content": (
                f"当前项目: {proj.get('name','未命名')}\n"
                f"类型: {proj.get('genre','')}\n文风: {proj.get('style','')}\n"
                f"核心设定: {proj.get('premise','')}"
            ),
        })
    msgs.append({"role": "system", "content": agents.get_prompt(agent_name)})
    for m in store.list_messages(pid):
        if m["role"] == "tool":
            msgs.append({
                "role": "tool",
                "content": m["content"],
                "name": m["tool_name"] or "",
                "tool_call_id": m["tool_call_id"] or "",
            })
        elif m["role"] == "assistant" and m.get("tool_name"):
            try:
                tc = json.loads(m["content"])
                msgs.append({"role": "assistant", "content": None, "tool_calls": tc})
            except Exception:
                msgs.append({"role": "assistant", "content": m["content"]})
        else:
            msgs.append({"role": m["role"], "content": m["content"]})
    return msgs


def _event(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


async def _exec_tool(
    pid: str, fname: str, fargs: dict, *,
    depth: int, emit, agent_name: str = agents.DEFAULT_AGENT,
) -> str:
    """执行工具;对 delegate_to_agent 走子 agent 运行循环。

    emit: async 回调,用于把委派/步骤事件外抛给 SSE 流。
    depth: 当前委派深度。
    agent_name: 调用方 agent 名 (用于沙盒检查)。
    """
    # 沙盒检查: 只读 agent 不允许调用写入类工具
    sandbox_err = _check_sandbox(agent_name, fname)
    if sandbox_err:
        return json.dumps({"error": sandbox_err}, ensure_ascii=False)
    if fname == "delegate_to_agent":
        target = fargs.get("agent", "")
        task = fargs.get("task", "")
        if not agents.is_valid(target) or target == agents.DEFAULT_AGENT:
            return json.dumps({"error": f"无法委派给 {target}"}, ensure_ascii=False)
        if depth >= agents.MAX_DELEGATE_DEPTH:
            return json.dumps({"error": f"已达最大委派深度 {agents.MAX_DELEGATE_DEPTH}"}, ensure_ascii=False)
        await emit({"type": "delegate", "from": agent_name, "to": target, "task": task, "depth": depth + 1})
        result = await _run_sub_agent(pid, target, task, depth=depth + 1, emit=emit)
        return json.dumps({"agent": target, "task": task, "result": result}, ensure_ascii=False)
    # 普通工具直接走 dispatch
    return await tools.dispatch(pid, fname, fargs)


async def _run_sub_agent(
    pid: str, agent_name: str, task: str, *,
    depth: int, emit,
) -> str:
    """运行子 agent 的 agentic loop,返回最终文本回答(不产出 token 流)。

    子 agent 用自己的系统提示词 + 工具子集,可继续委派(受 depth 限制)。
    事件通过 emit 外抛,主流程不存子 agent 的消息到 store(避免污染主对话历史)。
    """
    s = get_settings()
    tool_schema = tools.schema_for(agents.get_tools(agent_name))
    messages: list[dict] = []
    proj = store.get_project(pid)
    if proj:
        messages.append({
            "role": "system",
            "content": (
                f"当前项目: {proj.get('name','未命名')}\n"
                f"类型: {proj.get('genre','')}\n文风: {proj.get('style','')}\n"
                f"核心设定: {proj.get('premise','')}"
            ),
        })
    messages.append({"role": "system", "content": agents.get_prompt(agent_name)})
    messages.append({"role": "user", "content": f"[来自上级 agent 的委派任务]\n{task}"})

    # 子 agent 步数限制更紧(避免单次委派吃满所有步数)
    sub_max_steps = max(3, s.max_steps // 2)
    for step in range(sub_max_steps):
        try:
            resp = await chat(messages, s.default_model, tools=tool_schema)
        except Exception as e:
            return f"(子 agent {agent_name} 调用失败: {e})"

        tool_calls = resp["tool_calls"]
        content = resp["content"]

        if not tool_calls:
            # 终态:返回最终文本
            await emit({"type": "step", "agent": agent_name, "tool": "(完成)",
                        "args": {}, "thinking": content, "depth": depth})
            return content or ""

        messages.append({
            "role": "assistant",
            "content": content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ],
        })

        for tc in tool_calls:
            fname = tc.function.name
            try:
                fargs = json.loads(tc.function.arguments or "{}")
            except Exception:
                fargs = {}
            await emit({"type": "step", "agent": agent_name, "tool": fname,
                        "args": fargs, "thinking": content, "depth": depth})
            result = await _exec_tool(pid, fname, fargs, depth=depth, emit=emit, agent_name=agent_name)
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "name": fname, "content": result})
            await emit({"type": "observation", "agent": agent_name, "tool": fname,
                        "result": result, "depth": depth})

    return f"(子 agent {agent_name} 达到最大步数 {sub_max_steps},任务未完全完成)"


async def run(
    pid: str, user_input: str, agent_name: str = agents.DEFAULT_AGENT
) -> AsyncIterator[str]:
    """主 agent 运行循环。产出 SSE 事件字符串。

    agent_name: 入口 agent,默认 orchestrator 总编。
    """
    s = get_settings()
    store.add_message(pid, "user", user_input)
    messages = _build_messages(pid, agent_name)
    tool_schema = tools.schema_for(agents.get_tools(agent_name))

    # 事件缓冲:子 agent 委派过程中产生的事件也要吐给前端
    event_queue: list[str] = []

    async def emit(obj: dict):
        event_queue.append(_event(obj))

    yield _event({"type": "start", "agent": agent_name, "input": user_input})

    for step in range(s.max_steps):
        # 先把子 agent 委派过程中累积的事件吐出去
        while event_queue:
            yield event_queue.pop(0)

        try:
            resp = await chat(messages, s.default_model, tools=tool_schema)
        except Exception as e:
            yield _event({"type": "error", "message": str(e)})
            return

        tool_calls = resp["tool_calls"]
        content = resp["content"]

        if not tool_calls:
            store.add_message(pid, "assistant", content)
            yield _event({"type": "answer_start", "agent": agent_name})
            chunk_size = 12
            for i in range(0, len(content), chunk_size):
                yield _event({"type": "token", "text": content[i: i + chunk_size]})
            yield _event({"type": "answer_end"})
            yield _event({
                "type": "done", "agent": agent_name,
                "steps": step + 1, "stats": store.stats(pid),
            })
            return

        messages.append({
            "role": "assistant",
            "content": content,
            "tool_calls": [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ],
        })
        store.add_message(
            pid, "assistant",
            json.dumps([
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ], ensure_ascii=False),
            tool_name="tool_calls",
        )

        for tc in tool_calls:
            fname = tc.function.name
            try:
                fargs = json.loads(tc.function.arguments or "{}")
            except Exception:
                fargs = {}
            yield _event({
                "type": "step", "agent": agent_name, "tool": fname,
                "args": fargs, "thinking": content,
            })
            result = await _exec_tool(pid, fname, fargs, depth=0, emit=emit, agent_name=agent_name)
            # 若该工具触发过子 agent,事件已累积在队列里,这里先吐队列
            while event_queue:
                yield event_queue.pop(0)
            messages.append({
                "role": "tool", "tool_call_id": tc.id,
                "name": fname, "content": result,
            })
            store.add_message(pid, "tool", result, tool_name=fname, tool_call_id=tc.id)
            yield _event({
                "type": "observation", "agent": agent_name,
                "tool": fname, "result": result,
            })

    store.add_message(pid, "assistant", "(已达最大步骤数,请继续指示。)")
    yield _event({
        "type": "done", "agent": agent_name,
        "steps": s.max_steps, "stats": store.stats(pid),
        "note": "达到最大步骤",
    })

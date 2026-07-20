"""FastAPI 服务:REST + SSE 流式。挂载静态前端。"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import store, tools
from .agent import run
from .config import get_settings, reload_settings
from .exporter import export_project, parse_bytes

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")

app = FastAPI(title="Novel Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    store.init_db()


# ---------- projects ----------
class ProjectIn(BaseModel):
    name: str
    genre: str = ""
    premise: str = ""
    style: str = ""


@app.post("/api/projects")
def create_project(p: ProjectIn):
    pid = store.create_project(p.name, p.genre, p.premise, p.style)
    return {"id": pid, **p.dict()}


@app.get("/api/projects")
def list_projects():
    return store.list_projects()


@app.get("/api/projects/{pid}")
def get_project(pid: str):
    p = store.get_project(pid)
    if not p:
        return {"error": "not found"}, 404
    p["stats"] = store.stats(pid)
    p["chapters"] = store.list_chapters(pid)
    p["elements"] = store.list_elements(pid)
    return p


@app.delete("/api/projects/{pid}")
def delete_project(pid: str):
    store.delete_project(pid)
    return {"ok": True}


# ---------- chapters ----------
class ChapterIn(BaseModel):
    title: str
    idx: Optional[int] = None
    outline: str = ""
    content: str = ""


@app.post("/api/projects/{pid}/chapters")
def add_chapter(pid: str, c: ChapterIn):
    chapters = store.list_chapters(pid)
    idx = c.idx if c.idx is not None else (max([x["idx"] for x in chapters], default=-1) + 1)
    cid = store.add_chapter(pid, c.title, idx, c.outline, c.content)
    return {"id": cid, "idx": idx}


@app.put("/api/chapters/{cid}")
def update_chapter(cid: str, body: dict):
    store.update_chapter(cid, **{k: v for k, v in body.items() if k in ("title", "outline", "content", "status")})
    return {"ok": True}


@app.delete("/api/chapters/{cid}")
def delete_chapter(cid: str):
    store.delete_chapter(cid)
    return {"ok": True}


@app.get("/api/projects/{pid}/chapters")
def list_chapters(pid: str):
    return store.list_chapters(pid)


@app.get("/api/projects/{pid}/sources")
def list_sources(pid: str):
    """已上传素材文件列表(去重 source)。"""
    chunks = store.list_chunks(pid)
    seen = {}
    for ck in chunks:
        src = ck["source"]
        if src not in seen:
            seen[src] = {"source": src, "chunks": 0, "chars": 0}
        seen[src]["chunks"] += 1
        seen[src]["chars"] += len(ck.get("text") or "")
    return list(seen.values())


@app.get("/api/projects/{pid}/search")
def search_chunks(pid: str, q: str = "", k: int = 8):
    """在已上传素材分块中检索与 q 相关的内容。"""
    results = tools.search_chunks(pid, q, k=k)
    return {"results": results, "total": len(store.list_chunks(pid))}


# ---------- elements ----------
class ElementIn(BaseModel):
    kind: str
    name: str
    detail: str


@app.post("/api/projects/{pid}/elements")
def add_element(pid: str, e: ElementIn):
    eid = store.add_element(pid, e.kind, e.name, e.detail)
    return {"id": eid, **e.dict()}


@app.get("/api/projects/{pid}/elements")
def list_elements(pid: str, kind: Optional[str] = None):
    return store.list_elements(pid, kind)


@app.delete("/api/elements/{eid}")
def delete_element(eid: str):
    store.delete_element(eid)
    return {"ok": True}


# ---------- messages ----------
@app.get("/api/projects/{pid}/messages")
def list_messages(pid: str):
    return store.list_messages(pid, limit=100)


@app.delete("/api/projects/{pid}/messages")
def clear_messages(pid: str):
    store.clear_messages(pid)
    return {"ok": True}


# ---------- agent (SSE 流式) ----------
class AgentIn(BaseModel):
    input: str
    agent: Optional[str] = None  # 入口 agent,默认 orchestrator


@app.post("/api/projects/{pid}/chat")
async def chat_sse(pid: str, body: AgentIn):
    from . import agents as agents_mod
    agent_name = body.agent or agents_mod.DEFAULT_AGENT
    if not agents_mod.is_valid(agent_name):
        agent_name = agents_mod.DEFAULT_AGENT

    async def gen():
        async for evt in run(pid, body.input, agent_name=agent_name):
            yield evt
    return StreamingResponse(gen(), media_type="text/event-stream")


# ---------- 多 agent 配置 ----------
@app.get("/api/agents")
def list_agents():
    from . import agents as agents_mod
    return {
        "agents": agents_mod.AGENT_META,
        "default": agents_mod.DEFAULT_AGENT,
        "max_delegate_depth": agents_mod.MAX_DELEGATE_DEPTH,
        "workflow_phases": agents_mod.WORKFLOW_PHASES,
        "readonly_agents": list(agents_mod.SANDBOX_READONLY),
    }


# ---------- 技能市场 (Skill Market) ----------
@app.get("/api/skills")
def list_skills():
    """列出所有技能 (内置 + 自定义) + 启用状态 + 调用次数。"""
    from . import skill_market
    return {
        "skills": skill_market.list_skills(),
        "status": skill_market.skill_market_status(),
    }


@app.post("/api/skills/{name}/toggle")
def toggle_skill(name: str):
    """切换某技能的启用/禁用状态。"""
    from . import skill_market
    return skill_market.toggle_skill(name)


@app.post("/api/skills/custom")
def add_custom_skill(body: dict):
    """添加自定义技能 (前端表单: name + label + description + prompt + agents + icon)。"""
    from . import skill_market
    name = body.get("name", "")
    label = body.get("label", "")
    description = body.get("description", "")
    prompt = body.get("prompt", "")
    agents = body.get("agents", ["orchestrator", "narrative-writer"])
    icon = body.get("icon", "⭐")
    return skill_market.add_custom_skill(
        name=name, label=label, description=description,
        prompt=prompt, agents=agents, icon=icon,
    )


@app.delete("/api/skills/custom/{name}")
def delete_custom_skill(name: str):
    """删除自定义技能 (内置技能不可删)。"""
    from . import skill_market
    return skill_market.remove_custom_skill(name)


# ---------- 上传小说 (多格式,供续写) ----------
@app.post("/api/projects/{pid}/upload")
async def upload_novel(
    pid: str,
    file: UploadFile = File(...),
    source_name: Optional[str] = Form(None),
):
    data = await file.read()
    src = source_name or file.filename or "upload"
    try:
        text = parse_bytes(src, data)
    except ValueError as e:
        return {"error": str(e)}
    if not text.strip():
        return {"error": "解析后内容为空"}
    res = tools.ingest_text(pid, text, src)
    res["chars"] = len(text)
    return res


# ---------- 导出 ----------
@app.get("/api/projects/{pid}/export")
def export(pid: str, fmt: str = "txt"):
    p = store.get_project(pid)
    if not p:
        return {"error": "project not found"}, 404
    chapters = store.list_chapters(pid)
    try:
        filename, content, ctype = export_project(p, chapters, fmt)
    except ValueError as e:
        return {"error": str(e)}, 400
    from fastapi.responses import Response
    from urllib.parse import quote

    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or "novel"
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{ascii_name}"; '
            f"filename*=UTF-8''{quote(filename)}"
        )
    }
    return Response(content=content, media_type=ctype, headers=headers)


# ---------- 配置 ----------
def _model_ready(cfg) -> bool:
    """模型是否已配置可用 key(或本地 ollama)。"""
    provider = cfg.model.split("/", 1)[0].lower() if "/" in cfg.model else "openai"
    if provider == "ollama":
        return True
    if cfg.api_key:
        return True
    env_map = {
        "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY", "deepseek": "DEEPSEEK_API_KEY",
        "dashscope": "DASHSCOPE_API_KEY",
        "zai": "ZAI_API_KEY", "zhipu": "ZAI_API_KEY", "glm": "ZAI_API_KEY",
        "moonshot": "MOONSHOT_API_KEY",
        "xai": "XAI_API_KEY", "mistral": "MISTRAL_API_KEY",
        "volcengine": "VOLCENGINE_API_KEY", "ark": "ARK_API_KEY",
        "baidu": "ERNIE_API_KEY", "ernie": "ERNIE_API_KEY", "qianfan": "ERNIE_API_KEY",
    }
    return bool(os.environ.get(env_map.get(provider, "")))


@app.get("/api/config")
def get_config():
    s = get_settings()
    return {
        "default": s.default_model.model,
        "models": [m.model for m in s.models],
        "ready": _model_ready(s.default_model),
        "max_steps": s.max_steps,
    }


@app.get("/api/config/models")
def get_models():
    s = get_settings()
    return {
        "default": s.default_model.model,
        "models": [m.model for m in s.models],
        "ready": _model_ready(s.default_model),
    }


class ModelSwitch(BaseModel):
    model: str


@app.put("/api/config/model")
def switch_model(body: ModelSwitch):
    from .config import set_default_model

    set_default_model(body.model)
    s = get_settings()
    return {"default": s.default_model.model, "ready": _model_ready(s.default_model)}


# ---------- 完整设置 (右侧面板用) ----------
@app.get("/api/settings")
def get_settings_full():
    from .config import PROVIDER_PRESETS

    s = get_settings()
    models = []
    for m in s.models:
        models.append({
            "model": m.model,
            "api_key": m.api_key or "",
            "api_key_set": bool(m.api_key),
            "api_base": m.api_base or "",
            "temperature": m.temperature,
            "max_tokens": m.max_tokens,
            "ready": _model_ready(m),
            "is_default": m.model == s.default_model.model,
        })
    return {
        "default": s.default_model.model,
        "models": models,
        "providers": PROVIDER_PRESETS,
        "max_steps": s.max_steps,
        "chunk_size": s.chunk_size,
        "retrieve_k": s.retrieve_k,
        "ready": _model_ready(s.default_model),
    }


class ModelConfigIn(BaseModel):
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


@app.put("/api/settings/model")
def save_model_cfg(body: ModelConfigIn):
    from .config import update_model_config, PROVIDER_PRESETS

    # 传空 api_base 时,自动用厂商预设默认 base
    api_base = body.api_base
    if not api_base:
        provider = body.model.split("/", 1)[0] if "/" in body.model else ""
        for p in PROVIDER_PRESETS:
            if p["provider"] == provider and p.get("api_base"):
                api_base = p["api_base"]
                break

    update_model_config(
        body.model,
        api_key=body.api_key,
        api_base=api_base,
        temperature=body.temperature,
        max_tokens=body.max_tokens,
    )
    return {"ok": True}


class ModelDelIn(BaseModel):
    model: str


@app.delete("/api/settings/model")
def del_model_cfg(body: ModelDelIn):
    from .config import remove_model_config

    remove_model_config(body.model)
    return {"ok": True}


class AgentParamsIn(BaseModel):
    max_steps: Optional[int] = None
    chunk_size: Optional[int] = None
    retrieve_k: Optional[int] = None


@app.put("/api/settings/agent")
def save_agent_params(body: AgentParamsIn):
    from .config import update_agent_params

    update_agent_params(
        max_steps=body.max_steps,
        chunk_size=body.chunk_size,
        retrieve_k=body.retrieve_k,
    )
    return {"ok": True}


@app.get("/api/health")
def health():
    return {"ok": True}


# ---------- 静态前端 ----------
if os.path.isdir(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    idx = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(idx):
        with open(idx, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Novel Agent</h1><p>web/ 目录未找到</p>"


def main() -> None:
    import uvicorn

    s = get_settings()
    uvicorn.run("app.server:app", host=s.server_host, port=s.server_port, reload=False)


if __name__ == "__main__":
    main()

"""小说创作工具集。每个工具是 agent 可调用的能力,返回结构化结果。

核心能力:
- generate_outline: 生成小说大纲 + 章节结构
- continue_writing: 续写章节 (融合已有章节/上传小说的检索上下文)
- manage_elements: 增删查 角色/世界观/地点/时间线
- polish: 润色/改写/扩写已有正文
- ingest_text: 把上传的小说或已有章节切分入库,供后续续写检索

检索采用轻量关键词评分 (无外部向量库依赖,零配置即可跑)。
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from . import store
from .config import get_settings
from .llm import chat, stream


# ---------------- 通用辅助 ----------------
def _project_brief(pid: str) -> str:
    p = store.get_project(pid) or {}
    parts = []
    if p.get("genre"):
        parts.append(f"类型: {p['genre']}")
    if p.get("style"):
        parts.append(f"文风: {p['style']}")
    if p.get("premise"):
        parts.append(f"核心设定: {p['premise']}")
    return "\n".join(parts) or "(暂无项目设定)"


def _elements_block(pid: str) -> str:
    items = store.list_elements(pid)
    if not items:
        return "(暂无角色/世界观设定)"
    by_kind: dict[str, list[dict]] = {}
    for it in items:
        by_kind.setdefault(it["kind"], []).append(it)
    label = {
        "character": "角色",
        "location": "地点",
        "lore": "世界观/设定",
        "timeline": "时间线",
    }
    lines = []
    for kind, lst in by_kind.items():
        lines.append(f"【{label.get(kind, kind)}】")
        for e in lst:
            lines.append(f"- {e['name']}: {e['detail']}")
    return "\n".join(lines)


def _keyword_score(query: str, text: str) -> float:
    q_tokens = [w for w in re.findall(r"[\w]+", query) if len(w) > 1]
    if not q_tokens:
        return 0.0
    score = 0.0
    low = text.lower()
    for t in q_tokens:
        c = low.count(t.lower())
        if c:
            score += 1.0 / (1 + low.find(t.lower())) * min(c, 5)
    return score


def _retrieve_context(pid: str, query: str, k: int = 6) -> str:
    """从上传小说分块 + 已有章节中检索与 query 最相关的内容。"""
    s = get_settings()
    k = k or s.retrieve_k
    chunks = store.list_chunks(pid)
    scored = []
    for ch in chunks:
        sc = _keyword_score(query, ch["text"])
        if sc > 0:
            scored.append((sc, ch))
    scored.sort(key=lambda x: x[0], reverse=True)
    picked = [c for _, c in scored[:k]]
    # 不足 k 时,补上最近的章节尾部 (保证续写有连续性)
    chapters = store.list_chapters(pid)
    chap_tail = ""
    if chapters:
        last = chapters[-1]
        if last.get("content"):
            chap_tail = last["content"][-1500:]
    parts = []
    if picked:
        parts.append("# 相关上文片段(来自上传/已写内容)")
        for c in picked:
            parts.append(f"〔来源 {c['source']}〕\n{c['text']}")
    if chap_tail:
        parts.append(f"# 最近章节《{chapters[-1]['title']}》结尾\n{chap_tail}")
    return "\n\n".join(parts) if parts else "(无可用上文,将自由创作)"


def search_chunks(pid: str, query: str, k: int = 8) -> list[dict]:
    """公开检索:从上传素材分块中找与 query 最相关的内容,返回结构化结果。"""
    s = get_settings()
    k = k or s.retrieve_k
    chunks = store.list_chunks(pid)
    scored = []
    for ch in chunks:
        sc = _keyword_score(query, ch.get("text", ""))
        if sc > 0:
            scored.append((sc, ch))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "source": c.get("source", ""),
            "idx": c.get("idx", 0),
            "text": c.get("text", ""),
            "score": round(float(sc), 3),
        }
        for sc, c in scored[:k]
    ]


def _split_text(text: str, size: int, overlap: int) -> list[str]:
    if not text:
        return []
    step = max(1, size - overlap)
    return [text[i : i + size] for i in range(0, len(text), step)]


# ---------------- 工具实现 ----------------
async def generate_outline(
    pid: str,
    premise: str,
    *,
    num_chapters: int = 12,
    genre: Optional[str] = None,
) -> dict:
    """生成完整大纲与章节结构,并写入项目与章节。"""
    p = store.get_project(pid) or {}
    genre = genre or p.get("genre") or "通用"
    system = (
        "你是一位资深小说策划。根据用户给定的核心设定,产出结构严谨、有起承转合的"
        "小说大纲。严格只输出 JSON,不要任何额外文字。"
    )
    schema_hint = {
        "title": "小说标题",
        "logline": "一句话梗概",
        "themes": ["主题1"],
        "chapters": [
            {"title": "章节标题", "outline": "该章节情节梗概 100-200 字"}
        ],
    }
    user = (
        f"类型:{genre}\n核心设定:{premise}\n文风:{p.get('style','')}\n"
        f"请生成 {num_chapters} 个章节的完整大纲。\n"
        f"只输出 JSON,结构如下:\n{json.dumps(schema_hint, ensure_ascii=False)}"
    )
    resp = await chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        get_settings().default_model,
        temperature=0.9,
        response_format={"type": "json_object"},
    )
    content = resp["content"].strip()
    # 容错:截取首个 {...}
    m = re.search(r"\{.*\}", content, re.S)
    if m:
        content = m.group(0)
    try:
        data = json.loads(content)
    except Exception:
        return {"error": "大纲解析失败", "raw": content}

    if data.get("title") and not p.get("name"):
        store.update_project(pid, name=data["title"])
    if data.get("logline") and not p.get("premise"):
        store.update_project(pid, premise=data["logline"])

    # 写入章节(若已有则追加 idx)
    existing = store.list_chapters(pid)
    base = max([c["idx"] for c in existing], default=-1) + 1
    created = []
    for i, ch in enumerate(data.get("chapters", [])):
        cid = store.add_chapter(
            pid,
            title=ch.get("title", f"第{base+i+1}章"),
            idx=base + i,
            outline=ch.get("outline", ""),
            content="",
        )
        created.append({"id": cid, "title": ch.get("title"), "outline": ch.get("outline")})
    data["chapters_created"] = created
    return data


async def continue_writing(
    pid: str,
    chapter_id: Optional[str] = None,
    *,
    instruction: str = "",
    length: int = 2000,
) -> dict:
    """续写章节正文。若指定 chapter_id 则续写该章,否则续写最近一章。"""
    chapters = store.list_chapters(pid)
    if not chapter_id and not chapters:
        return {"error": "尚无章节,请先生成大纲"}
    target = None
    if chapter_id:
        target = store.get_chapter(chapter_id)
    if target is None and chapters:
        target = chapters[-1]
    if target is None:
        return {"error": "未找到目标章节"}

    brief = _project_brief(pid)
    elements = _elements_block(pid)
    context = _retrieve_context(pid, target["title"] + " " + target.get("outline", "") + " " + instruction)
    existing_tail = (target.get("content") or "")[-1800:]

    system = (
        "你是一位技艺精湛的小说家。严格延续已有的人物性格、世界观、文风与情节走向,"
        "自然衔接上文结尾,不要重复已有内容,不要输出除正文外的任何说明。"
    )
    user = (
        f"# 项目设定\n{brief}\n\n# 设定资料\n{elements}\n\n"
        f"# 检索到的相关上文\n{context}\n\n"
        f"# 本章信息\n标题:{target['title']}\n本章梗概:{target.get('outline','')}\n"
        f"# 本章已有正文(结尾部分)\n{existing_tail or '(本章尚未开始)'}\n"
        f"# 续写要求\n{instruction or '自然推进情节,保持张力。'}\n"
        f"续写约 {length} 字正文,直接输出小说内容。"
    )
    pieces: list[str] = []
    async for tok in stream(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        get_settings().default_model,
        temperature=0.85,
        max_tokens=max(1024, int(length * 2)),
    ):
        pieces.append(tok)
    new_text = "".join(pieces)

    # 追加到该章节内容
    merged = (target.get("content") or "") + ("\n" if target.get("content") else "") + new_text
    store.update_chapter(target["id"], content=merged, status="writing")
    return {
        "chapter_id": target["id"],
        "title": target["title"],
        "appended": len(new_text),
        "total_chars": len(merged),
    }


async def polish(
    pid: str,
    chapter_id: str,
    *,
    mode: str = "polish",  # polish | rewrite | expand
    instruction: str = "",
) -> dict:
    """润色/改写/扩写某章节正文。"""
    ch = store.get_chapter(chapter_id)
    if not ch:
        return {"error": "未找到章节"}
    desc = {"polish": "润色(修正措辞、增强感染力,保持情节与字数基本不变)",
            "rewrite": "改写(按指令重写该章,情节可调整)",
            "expand": "扩写(在保持原有情节基础上扩充细节与描写,字数增加)"}.get(mode, "润色")
    system = "你是一位资深小说编辑。直接输出处理后的完整章节正文,不要任何解释或前后缀。"
    user = (
        f"任务:{desc}\n项目设定:\n{_project_brief(pid)}\n"
        f"角色/设定:\n{_elements_block(pid)}\n"
        f"额外要求:{instruction or '无'}\n\n"
        f"原章节《{ch['title']}》正文:\n{ch.get('content','')}"
    )
    pieces: list[str] = []
    async for tok in stream(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        get_settings().default_model,
        temperature=0.7,
    ):
        pieces.append(tok)
    new_text = "".join(pieces)
    store.update_chapter(chapter_id, content=new_text, status="polished")
    return {"chapter_id": chapter_id, "title": ch["title"], "chars": len(new_text)}


def ingest_text(pid: str, text: str, source: str) -> dict:
    """把文本(上传的小说或导入的内容)分块入库,供续写检索。"""
    s = get_settings()
    # 删除同源旧分块
    store.delete_chunks_by_source(pid, source)
    blocks = _split_text(text, s.chunk_size, s.chunk_overlap)
    for i, b in enumerate(blocks):
        store.add_chunk(pid, source, i, b)
    return {"source": source, "chunks": len(blocks), "chars": len(text)}


def add_element(pid: str, kind: str, name: str, detail: str) -> dict:
    eid = store.add_element(pid, kind, name, detail)
    return {"id": eid, "kind": kind, "name": name, "detail": detail}


async def scan_bestseller(
    pid: str,
    *,
    genre: str = "通用",
    preference: str = "",
) -> dict:
    """扫榜调研:基于 2026 网文市场数据 + 用户偏好,分析热门题材与流量赛道。"""
    system = (
        "你是网文市场分析师,精通 2026 年各大平台(起点/番茄/晋江/七猫)的热门榜单与流量趋势。"
        "严格只输出 JSON,不要任何额外文字。"
    )
    schema_hint = {
        "market_overview": "2026 当前市场总体趋势(100字)",
        "hot_genres": [
            {"genre": "题材名", "heat": "高/中/低", "platform": "主战场平台", "audience": "读者画像", "why_hot": "为什么火"}
        ],
        "recommended_direction": "结合用户偏好,推荐 1-2 个可写方向(200字)",
        "risk_warning": "红海/同质化风险提示",
    }
    user = (
        f"目标题材:{genre}\n用户偏好:{preference or '(未指定,请推荐当前最热赛道)'}\n"
        f"请基于 2026 年最新市场情况,扫描热门榜单并给出题材方向建议。\n"
        f"只输出 JSON,结构如下:\n{json.dumps(schema_hint, ensure_ascii=False)}"
    )
    resp = await chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        get_settings().default_model,
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    content = resp["content"].strip()
    m = re.search(r"\{.*\}", content, re.S)
    if m:
        content = m.group(0)
    try:
        data = json.loads(content)
    except Exception:
        return {"error": "扫榜结果解析失败", "raw": content}
    # 存为项目设定 (lore 类型)
    summary = "## 扫榜调研结果\n" + json.dumps(data, ensure_ascii=False, indent=2)
    store.add_element(pid, "lore", "扫榜调研", summary)
    return data


async def analyze_novel(
    pid: str,
    *,
    source: str = "",
    focus: str = "all",
) -> dict:
    """拆书解构:拆解已上传的对标书,提取钩子/节奏/人设/文风等可复用模块。"""
    chunks = store.list_chunks(pid)
    if source:
        chunks = [c for c in chunks if c.get("source") == source]
    if not chunks:
        return {"error": "未找到可拆解的素材,请先上传对标书(上传按钮)"}
    # 取前 6000 字作为分析样本
    sample = "\n".join(c["text"] for c in chunks[:8])[:6000]

    focus_map = {
        "all": "开篇钩子、节奏结构、人设套路、文风指纹、核心梗、情绪曲线",
        "hook": "开篇前 500 字的钩子手法",
        "rhythm": "节奏与章节结构 (起承转合)",
        "character": "人设套路与角色关系",
        "style": "文风指纹 (语言风格/叙事姿态/用词偏好)",
        "plot": "核心梗与剧情模块",
    }
    focus_text = focus_map.get(focus, focus_map["all"])

    system = (
        "你是资深拆书编辑,擅长把畅销书拆解成可复用的创作模块。"
        "严格只输出 JSON,不要任何额外文字。"
    )
    schema_hint = {
        "book_type": "书籍类型/题材",
        "hook_analysis": "开篇钩子手法分析",
        "rhythm_structure": "节奏与结构拆解 (起承转合/章节配比)",
        "character_template": "可复用的人设模板",
        "style_fingerprint": "文风指纹 (语言风格/叙事视角/用词特征)",
        "core_gimmick": "核心梗提炼",
        "reusable_modules": ["可复用的剧情模块1", "可复用的剧情模块2"],
        "takeaway": "对本文创作的启示 (150字)",
    }
    user = (
        f"拆解重点:{focus_text}\n\n"
        f"对标书样本:\n{sample}\n\n"
        f"请拆解这本书的可复用模块。只输出 JSON,结构如下:\n{json.dumps(schema_hint, ensure_ascii=False)}"
    )
    resp = await chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        get_settings().default_model,
        temperature=0.6,
        response_format={"type": "json_object"},
    )
    content = resp["content"].strip()
    m = re.search(r"\{.*\}", content, re.S)
    if m:
        content = m.group(0)
    try:
        data = json.loads(content)
    except Exception:
        return {"error": "拆书结果解析失败", "raw": content}
    summary = "## 拆书解构结果\n" + json.dumps(data, ensure_ascii=False, indent=2)
    store.add_element(pid, "lore", f"拆书:{source or '对标书'}", summary)
    return data


# ---------------- 工具注册表 (供 agent 调用) ----------------
TOOL_SCHEMA: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "generate_outline",
            "description": "根据核心设定生成小说大纲与章节结构,并自动入库。",
            "parameters": {
                "type": "object",
                "properties": {
                    "premise": {"type": "string", "description": "小说核心设定/梗概"},
                    "num_chapters": {"type": "integer", "description": "章节数,默认12"},
                    "genre": {"type": "string", "description": "类型(可选)"},
                },
                "required": ["premise"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "continue_writing",
            "description": "续写章节正文。可指定某章,缺省续写最近一章。",
            "parameters": {
                "type": "object",
                "properties": {
                    "chapter_id": {"type": "string", "description": "目标章节id(可选)"},
                    "instruction": {"type": "string", "description": "续写指令/方向(可选)"},
                    "length": {"type": "integer", "description": "目标字数,默认2000"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "polish",
            "description": "润色/改写/扩写某章节已有正文。",
            "parameters": {
                "type": "object",
                "properties": {
                    "chapter_id": {"type": "string", "description": "目标章节id"},
                    "mode": {"type": "string", "enum": ["polish", "rewrite", "expand"],
                             "description": "polish润色/rewrite改写/expand扩写"},
                    "instruction": {"type": "string", "description": "额外要求(可选)"},
                },
                "required": ["chapter_id", "mode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_element",
            "description": "添加角色/地点/世界观/时间线等设定元素。",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string",
                             "enum": ["character", "location", "lore", "timeline"],
                             "description": "元素类型"},
                    "name": {"type": "string", "description": "名称"},
                    "detail": {"type": "string", "description": "详细描述"},
                },
                "required": ["kind", "name", "detail"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_project",
            "description": "查询当前项目的章节、设定与统计信息。",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_to_agent",
            "description": "把任务委派给专家 agent 协同完成 (oh-story 7-agent 架构)。"
            "可用 agent:story-architect(架构师/选题大纲钩子反转)/"
            "narrative-writer(主笔/正文润色去AI味)/"
            "character-designer(角色师/角色档案对话关系)/"
            "consistency-checker(质检员/只读一致性检查)/"
            "story-explorer(资料员/只读上下文加载)/"
            "worldbuilder(设定管理员/地点世界观时间线)。"
            "子 agent 会独立运行 agentic loop 并返回结果。",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent": {"type": "string",
                              "enum": ["story-architect", "narrative-writer",
                                       "character-designer", "consistency-checker",
                                       "story-explorer", "worldbuilder"],
                              "description": "目标专家 agent 名称"},
                    "task": {"type": "string", "description": "委派给该 agent 的具体任务描述"},
                },
                "required": ["agent", "task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_outline",
            "description": "细纲蓝图管理。支持 action:set(创建/更新某章细纲)/get(读取某章细纲)/list(列出所有细纲)。"
            "细纲格式参照 oh-story:核心事件/字数目标/目标情绪/章首钩子/爽点 + 内容概括五段式 + "
            "情节安排多线 + 人物关系出场顺序 + 情节细化(每个情节点标密/疏+字数预算) + 结尾设定和章尾钩子。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["set", "get", "list"],
                               "description": "set=新建/更新细纲;get=读取细纲;list=列出项目所有细纲"},
                    "chapter_id": {"type": "string", "description": "目标章节 id (action=set/get 必填)"},
                    "blueprint": {"type": "string",
                                  "description": "细纲蓝图 markdown 内容 (action=set 必填,按 oh-story 模板)"},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "load_context",
            "description": "加载指定章节的写作上下文包 (oh-story Phase 4 单章写作流程必备)。"
            "返回:写作进度/上一章正文摘要/本章细纲/待回收伏笔/最近时间线/本章涉及角色状态。",
            "parameters": {
                "type": "object",
                "properties": {
                    "chapter_id": {"type": "string",
                                   "description": "目标章节 id;缺省取最近一章作为下一章的上一章"},
                    "query_type": {"type": "string",
                                   "enum": ["context_load", "character_status", "foreshadow_list",
                                            "timeline", "progress"],
                                   "description": "查询类型,默认 context_load(综合上下文)"},
                    "character_name": {"type": "string",
                                       "description": "query_type=character_status 时指定角色名"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "quality_check",
            "description": "执行一致性检查 (oh-story consistency-checker 能力)。"
            "检查维度:实体冲突/设定冲突/时间线冲突/规则边界悖论/设定层级冲突/跨章因果链/规则可滥用漏洞/代价一致性。"
            "返回 S1-S4 分级报告 + 伏笔状态扫描。",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string",
                              "enum": ["all", "latest", "chapter"],
                              "description": "检查范围:all=全书;latest=最近一章;chapter=指定章节"},
                    "chapter_id": {"type": "string",
                                   "description": "scope=chapter 时指定章节 id"},
                    "focus": {"type": "string",
                              "enum": ["consistency", "foreshadow", "timeline", "all"],
                              "description": "检查重点,默认 all"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scan_bestseller",
            "description": "扫榜调研 (阶段1):基于 2026 网文市场热门榜单,分析题材趋势/流量赛道/读者画像,"
            "锁定可写方向。结果自动存为项目设定。",
            "parameters": {
                "type": "object",
                "properties": {
                    "genre": {"type": "string", "description": "目标题材(如 悬疑/玄幻/言情),默认通用"},
                    "preference": {"type": "string", "description": "用户偏好(如 男频/女频/无CP/快节奏),可选"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_novel",
            "description": "拆书解构 (阶段2):拆解已上传的对标畅销书,提取开篇钩子/节奏结构/人设套路/文风指纹/"
            "核心梗等可复用模块。需先通过上传按钮导入对标书。结果自动存为项目设定。",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "对标书素材名(可选,缺省拆最近上传的)"},
                    "focus": {"type": "string",
                              "enum": ["all", "hook", "rhythm", "character", "style", "plot"],
                              "description": "拆解重点:all=全部/hook=开篇钩子/rhythm=节奏/character=人设/style=文风/plot=核心梗"},
                },
            },
        },
    },
]


async def dispatch(pid: str, name: str, args: dict) -> str:
    """执行工具,返回给 LLM 的字符串结果。"""
    try:
        if name == "generate_outline":
            res = await generate_outline(
                pid, args["premise"],
                num_chapters=int(args.get("num_chapters", 12)),
                genre=args.get("genre"),
            )
        elif name == "continue_writing":
            res = await continue_writing(
                pid, args.get("chapter_id"),
                instruction=args.get("instruction", ""),
                length=int(args.get("length", 2000)),
            )
        elif name == "polish":
            res = await polish(
                pid, args["chapter_id"], mode=args.get("mode", "polish"),
                instruction=args.get("instruction", ""),
            )
        elif name == "add_element":
            res = add_element(pid, args["kind"], args["name"], args["detail"])
        elif name == "query_project":
            res = {
                "project": store.get_project(pid),
                "stats": store.stats(pid),
                "chapters": [
                    {"id": c["id"], "title": c["title"], "idx": c["idx"],
                     "chars": len(c.get("content") or ""),
                     "has_outline": bool(c.get("outline"))}
                    for c in store.list_chapters(pid)
                ],
                "elements": store.list_elements(pid),
                "foreshadowings": [
                    {"id": f["id"], "name": f["name"], "status": f["status"],
                     "planted_chapter": f.get("planted_chapter"),
                     "expected_recovery": f.get("expected_recovery")}
                    for f in store.list_foreshadowings(pid)
                ],
                "timeline_events_count": len(store.list_timeline_events(pid)),
                "character_states": [
                    {"name": cs["character_name"], "latest_chapter": cs["latest_chapter"],
                     "current_state": cs["current_state"]}
                    for cs in store.list_character_states(pid)
                ],
            }
        elif name == "manage_outline":
            res = _manage_outline(pid, args)
        elif name == "load_context":
            res = _load_context(pid, args)
        elif name == "quality_check":
            res = _quality_check(pid, args)
        elif name == "scan_bestseller":
            res = await scan_bestseller(
                pid, genre=args.get("genre", "通用"),
                preference=args.get("preference", ""),
            )
        elif name == "analyze_novel":
            res = await analyze_novel(
                pid, source=args.get("source", ""),
                focus=args.get("focus", "all"),
            )
        elif name == "delegate_to_agent":
            # 实际执行由 agent.py 在调用前注入(因为需要访问子 agent 运行循环)
            # 若走到这里说明未注入,返回提示
            res = {"error": "delegate_to_agent 必须由 agent 运行时处理"}
        else:
            res = {"error": f"未知工具 {name}"}
    except Exception as e:
        res = {"error": f"工具执行出错: {e}"}
    return json.dumps(res, ensure_ascii=False)


# ---------------- 新增工具实现 ----------------
def _manage_outline(pid: str, args: dict) -> dict:
    """细纲蓝图管理:set/get/list。"""
    action = args.get("action", "list")
    if action == "list":
        chapters = store.list_chapters(pid)
        return {
            "count": len(chapters),
            "outlines": [
                {"chapter_id": c["id"], "idx": c["idx"], "title": c["title"],
                 "has_outline": bool(c.get("outline")),
                 "outline_chars": len(c.get("outline") or "")}
                for c in chapters
            ],
        }
    cid = args.get("chapter_id")
    if not cid:
        return {"error": "action=set/get 需要提供 chapter_id"}
    if action == "get":
        ch = store.get_chapter(cid)
        if not ch:
            return {"error": "未找到章节"}
        return {
            "chapter_id": cid, "idx": ch["idx"], "title": ch["title"],
            "outline": ch.get("outline") or "(暂无细纲)",
        }
    if action == "set":
        blueprint = args.get("blueprint")
        if not blueprint:
            return {"error": "action=set 需要提供 blueprint (细纲蓝图 markdown)"}
        ch = store.get_chapter(cid)
        if not ch:
            return {"error": "未找到章节"}
        store.set_chapter_outline(cid, blueprint)
        return {
            "chapter_id": cid, "title": ch["title"], "idx": ch["idx"],
            "blueprint_chars": len(blueprint), "status": "outlined",
        }
    return {"error": f"未知 action: {action}"}


def _load_context(pid: str, args: dict) -> dict:
    """加载指定章节的写作上下文包。"""
    qtype = args.get("query_type", "context_load")
    chapters = store.list_chapters(pid)

    if qtype == "progress":
        last_ch = chapters[-1] if chapters else None
        return {
            "query_type": "progress",
            "last_chapter": ({"idx": last_ch["idx"], "title": last_ch["title"]}
                             if last_ch else None),
            "next_chapter_idx": (last_ch["idx"] + 1 if last_ch else 0),
            "stats": store.stats(pid),
        }

    if qtype == "character_status":
        name = args.get("character_name")
        if name:
            cs = store.get_character_state(pid, name)
            if not cs:
                return {"error": f"未找到角色 {name} 的状态记录", "gaps": ["character_state_missing"]}
            return {"query_type": "character_status", "character": cs}
        return {
            "query_type": "character_status",
            "characters": store.list_character_states(pid),
        }

    if qtype == "foreshadow_list":
        return {
            "query_type": "foreshadow_list",
            "foreshadowings": store.list_foreshadowings(pid),
        }

    if qtype == "timeline":
        return {
            "query_type": "timeline",
            "events": store.list_timeline_events(pid),
        }

    # 默认 context_load:综合上下文包
    cid = args.get("chapter_id")
    target = None
    if cid:
        target = store.get_chapter(cid)
    elif chapters:
        target = chapters[-1]
    if not target:
        return {"error": "尚无章节,请先生成大纲"}

    # 找上一章 (idx 最大的小于本章 idx 的)
    prev = None
    for c in chapters:
        if c["idx"] < target["idx"] and (prev is None or c["idx"] > prev["idx"]):
            prev = c

    # 涉及角色状态:从角色设定提取名字,匹配 character_states
    elements = store.list_elements(pid, kind="character")
    char_names = [e["name"] for e in elements]
    char_states = []
    for n in char_names:
        cs = store.get_character_state(pid, n)
        if cs:
            char_states.append(cs)

    return {
        "query_type": "context_load",
        "progress": {
            "last_chapter": {"idx": target["idx"], "title": target["title"]},
            "next_chapter_idx": target["idx"] + 1,
        },
        "chapter_plan": {
            "chapter_id": target["id"], "idx": target["idx"], "title": target["title"],
            "outline": target.get("outline") or "(暂无细纲)",
        },
        "previous_chapter_summary": (
            {"idx": prev["idx"], "title": prev["title"],
             "tail": (prev.get("content") or "")[-1500:]}
            if prev else None
        ),
        "active_foreshadows": store.list_foreshadowings(pid, status="planted"),
        "recent_timeline": store.list_timeline_events(pid)[-10:],
        "characters": [
            {"name": cs["character_name"], "current_state": cs["current_state"],
             "latest_chapter": cs["latest_chapter"]}
            for cs in char_states
        ],
        "gaps": [] if target.get("outline") else ["chapter_outline_missing"],
    }


def _quality_check(pid: str, args: dict) -> dict:
    """执行一致性检查,返回 S1-S4 分级报告。

    此处做轻量级确定性检查 (无需 LLM);需要深度推理的检查由 consistency-checker
    agent 在调用本工具后,基于返回的事实清单自行推理输出 S1-S4 报告。
    """
    scope = args.get("scope", "all")
    focus = args.get("focus", "all")

    chapters = store.list_chapters(pid)
    if not chapters:
        return {"error": "尚无章节,无法检查"}

    # 范围筛选
    if scope == "latest":
        target_chapters = [chapters[-1]]
    elif scope == "chapter":
        cid = args.get("chapter_id")
        if not cid:
            return {"error": "scope=chapter 需要提供 chapter_id"}
        target = store.get_chapter(cid)
        if not target:
            return {"error": "未找到章节"}
        target_chapters = [target]
    else:
        target_chapters = chapters

    findings: list[dict] = []

    # ----- 伏笔扫描 -----
    if focus in ("foreshadow", "all"):
        fs_all = store.list_foreshadowings(pid)
        max_idx = max((c["idx"] for c in chapters), default=0)
        for f in fs_all:
            if f["status"] == "planted":
                planted = f.get("planted_chapter") or 0
                expected = f.get("expected_recovery")
                gap = max_idx - planted
                if expected and max_idx > expected:
                    findings.append({
                        "level": "S2", "type": "foreshadow_overdue",
                        "msg": f"伏笔「{f['name']}」预期第 {expected} 章回收,当前已写到第 {max_idx} 章未回收",
                        "foreshadow_id": f["id"],
                    })
                elif gap > 50:
                    findings.append({
                        "level": "S4", "type": "foreshadow_long_unrecovered",
                        "msg": f"伏笔「{f['name']}」第 {planted} 章埋设,已 {gap} 章未回收 (>50 章)",
                        "foreshadow_id": f["id"],
                    })

        # 伏笔密度
        per_volume = 50  # 假设 50 章/卷
        density = len(fs_all) / max(1, max_idx / per_volume)
        if density < 3 and max_idx > 10:
            findings.append({
                "level": "S4", "type": "foreshadow_low_density",
                "msg": f"伏笔密度 {density:.1f}/卷,低于建议下限 3/卷",
            })
        elif density > 15:
            findings.append({
                "level": "S4", "type": "foreshadow_high_density",
                "msg": f"伏笔密度 {density:.1f}/卷,高于建议上限 15/卷",
            })

    # ----- 时间线检查 -----
    if focus in ("timeline", "all"):
        events = store.list_timeline_events(pid)
        # 简单检查:同一章节有多个事件但 time_in_story 不同 (可能时间线冲突)
        per_chapter: dict[int, list] = {}
        for ev in events:
            ci = ev.get("chapter_idx")
            if ci is not None:
                per_chapter.setdefault(ci, []).append(ev)
        for ci, evs in per_chapter.items():
            times = {e.get("time_in_story") for e in evs if e.get("time_in_story")}
            if len(times) > 1:
                findings.append({
                    "level": "S3", "type": "timeline_multiple_times",
                    "msg": f"第 {ci} 章记录了多个不同时间点: {sorted(times)}",
                })

    # ----- 章节字数检查 -----
    for ch in target_chapters:
        content = ch.get("content") or ""
        chars = len(content)
        # 找细纲中的字数目标
        outline = ch.get("outline") or ""
        target_chars = None
        m = re.search(r"字数目标[::]\s*(\d+)", outline)
        if m:
            target_chars = int(m.group(1))
        if target_chars and chars < target_chars * 0.9:
            findings.append({
                "level": "S2", "type": "chapter_underworded",
                "msg": f"第 {ch['idx']+1} 章《{ch['title']}》字数 {chars} < 目标 {target_chars} 的 90%",
                "chapter_id": ch["id"],
            })
        elif chars < 2000 and ch.get("status") not in ("draft", "outlined"):
            findings.append({
                "level": "S3", "type": "chapter_short",
                "msg": f"第 {ch['idx']+1} 章《{ch['title']}》字数 {chars} < 2000 (长篇最低门槛)",
                "chapter_id": ch["id"],
            })

    # ----- 章节是否有细纲 -----
    for ch in target_chapters:
        if not (ch.get("outline") or "").strip() and ch.get("status") != "draft":
            findings.append({
                "level": "S3", "type": "outline_missing",
                "msg": f"第 {ch['idx']+1} 章《{ch['title']}》无细纲蓝图",
                "chapter_id": ch["id"],
            })

    # ----- 角色状态与设定一致性 (角色有设定但无状态记录) -----
    if focus in ("consistency", "all"):
        char_elements = store.list_elements(pid, kind="character")
        for e in char_elements:
            cs = store.get_character_state(pid, e["name"])
            if not cs:
                findings.append({
                    "level": "S4", "type": "character_state_missing",
                    "msg": f"角色「{e['name']}」已建档但无状态快照记录",
                    "element_id": e["id"],
                })

    # 汇总
    verdict = "APPROVE"
    if any(f["level"] == "S1" for f in findings):
        verdict = "REJECT"
    elif any(f["level"] == "S2" for f in findings):
        verdict = "CONCERNS"

    counts = {"S1": 0, "S2": 0, "S3": 0, "S4": 0}
    for f in findings:
        counts[f["level"]] += 1

    return {
        "verdict": verdict,
        "scope": scope,
        "checked_chapters": [c["idx"] for c in target_chapters],
        "counts": counts,
        "findings": findings,
        "note": ("本工具仅做确定性检查 (字数/伏笔超期/密度/细纲缺失/角色状态缺失)。"
                 "深度推理检查 (规则边界悖论/设定层级冲突/跨章因果链/代价一致性) "
                 "由 consistency-checker agent 基于本结果推理输出。"),
    }


def schema_for(tool_names: list[str]) -> list[dict]:
    """按 agent 工具白名单过滤出对应的 tool schema。"""
    by_name = {t["function"]["name"]: t for t in TOOL_SCHEMA}
    return [by_name[n] for n in tool_names if n in by_name]

"""去AI味检测与标点标准化 (移植自 oh-story-claudecode story-deslop 脚本)。

提供三个核心函数:
- check_ai_patterns(text) -> list[dict]: 检测 AI 味文本模式
- check_degeneration(text) -> list[dict]: 检测模型退化 (复读/截断/元信息泄漏)
- normalize_punctuation(text) -> tuple[str, list[dict]]: 标准化标点符号

每个 finding 包含: line, column, type, severity(blocking|advisory), message, excerpt
"""
from __future__ import annotations

import re
from typing import Tuple

# ═══════════════════════════════════════════════════════════════════
# 通用辅助
# ═══════════════════════════════════════════════════════════════════

QUOTE_PAIRS = [
    ("「", "」"), ("『", "』"), ("【", "】"),
    ('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’"),
]

# 成对引号的正则 (用于去除引号内内容)
_QUOTE_SOURCES = "|".join(
    re.escape(o) + r"[^" + re.escape(c) + r"]*" + re.escape(c)
    for o, c in QUOTE_PAIRS
)
_STRIP_QUOTED_RE = re.compile(_QUOTE_SOURCES)

# 结尾标点
_TERMINAL_RE = re.compile(r'[。！？!?…"”』」）)]$')


def _strip_quoted(text: str) -> str:
    """去掉成对引号内的片段,只留引号外叙述。"""
    return _STRIP_QUOTED_RE.sub("", text)


def _visible_len(text: str) -> int:
    """计算可见字符数 (中日韩 + 字母 + 数字)。"""
    return len(re.findall(r"[一-鿿Ａ-ｚA-Za-z0-9]", text))


def _compact(text: str, max_len: int = 80) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    return t[:max_len - 3] + "..." if len(t) > max_len else t


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[。！？!?]", text) if s.strip()]


def _is_divider(trimmed: str) -> bool:
    return bool(re.match(r"^-{3,}$", trimmed)) or bool(re.match(r"^[*_]{3,}$", trimmed))


def _is_structural(trimmed: str) -> bool:
    return bool(
        re.match(r"^(#{1,6}\s|>\s?|[-*+]\s|\d+[.)]\s|\|)", trimmed)
        or re.match(r"^第[零一二三四五六七八九十百千万\d]+章", trimmed)
    )


def _is_dialogue_like(trimmed: str) -> bool:
    return bool(re.search(r'[“”"\'‘’「」『』【】]', trimmed))


# ═══════════════════════════════════════════════════════════════════
# check_ai_patterns: AI 味文本模式检测
# ═══════════════════════════════════════════════════════════════════

# 高频 AI 对比句式: "不是A, 是B" / "不是A, 而是B"
_NOT_IS_RE = re.compile(
    r"不是[^。！？!?\n]{0,80}(?:而是|(?:[，,、；;：:]?\s*是))"
)

# 破折号
_DASH_RE = re.compile(r"——|—|--+")

# 微动作复读: "V了下/了一下/拍了两下/松了半圈"
_MICRO_TIC_RE = re.compile(r"了(?:[一两三几半])?[下阵圈道声眼口气会]")
_MICRO_TIC_MIN_HITS = 5
_MICRO_TIC_PER_KILO = 6

# 监控摄像头式动作清单
_ACTION_LIST_VERBS = "伸手|抬手|探手|拿起|拿过|取出|取过|掏出|摸出|抓起|攥住|握住|捏住|按住|推开|拉开|打开|关上|放下|递给|挑开|掀开|扯开|拧开|倒出|端起|转身|回头|抬头|低头|弯腰|俯身|走到|走向|坐下|站起|看向|看着|盯着|扫过"
_ACTION_LIST_RE = re.compile(_ACTION_LIST_VERBS)
_ACTION_LIST_MIN_HITS = 5
_ACTION_LIST_MIN_SEPARATORS = 4

# 抽象总结复读
_ABSTRACT_SUMMARY_PATTERNS = [
    re.compile(r"这一刻[，,]?[^\n。！？!?]{0,24}(?:终于|才)(?:明白|意识到)"),
    re.compile(r"从这一刻开始"),
    re.compile(r"(?:命运|宿命)[^\n。！？!?]{0,28}(?:齿轮|棋局|獠牙|改写|推向|安排)"),
    re.compile(r"早已[^\n。！？!?]{0,8}(?:布好|安排好)[^\n。！？!?]{0,8}(?:棋局|局)"),
    re.compile(r"前所未有的(?:决意|清醒|勇气|力量|恐惧|平静|信念)"),
    re.compile(r"(?:反击|复仇|战争|较量|故事|命运)[^\n。！？!?]{0,12}才刚刚开始"),
    re.compile(r"(?:新的开始|全新的开始)"),
]
_ABSTRACT_SUMMARY_MIN_HITS = 3
_ABSTRACT_SUMMARY_PER_KILO = 4

# 套词密度
_CLICHE_PATTERNS = [
    re.compile(r"仿佛|犹如|宛若|如同"),
    re.compile(r"一丝|一抹|些许|几分|隐约"),
    re.compile(r"深吸一口气|缓缓|微微|轻轻|淡淡"),
    re.compile(r"眼中闪过|嘴角勾起|眸光微微一闪|指节泛白|目光锐利|眼神锐利"),
    re.compile(r"心中涌起一股|心头一震|心中一动|心下了然|心中暗道|心中一凛"),
    re.compile(r"不容置疑|不容置喙|不易察觉|显而易见|毫无疑问|不可否认"),
    re.compile(r"声音不大[，,]?却带着|语气平静无波|平静无波|声音平直|听不出情绪"),
    re.compile(r"不知何时|唾手可得|无声翻涌|沉默(?:在[^。！？!?\n]{0,16})?蔓延|难以言说"),
    re.compile(r"散发着一股|冰冷的光|格外刺眼|深邃而冰冷"),
]
_CLICHE_DENSITY_MIN_HITS = 8
_CLICHE_DENSITY_PER_KILO = 12

# 比喻密度
_METAPHOR_MARKER_RE = re.compile(r"好像|像是|仿佛|宛如|如同|犹如|(?<![不头图画影录摄肖])像(?![头像素])")
_METAPHOR_LIKE_RE = re.compile(r"(?:死|水|冰|火|潮水|石头|木头|机器|纸|铁|鬼|死人|刀|针|网|墙)一样")
_METAPHOR_DENSITY_MIN_HITS = 7
_METAPHOR_DENSITY_PER_KILO = 3

# 解释链密度
_REASONING_CHAIN_PATTERNS = [
    (re.compile(r"(?<![不没未无])(?:他|她|我)?(?:知道|明白|意识到|清楚|判断|确认|分析)"), "mental", True),
    (re.compile(r"这意味着|也就是说|换句话说|真正的问题(?:在于)?|问题在于|关键在于|在这种情况下|按照这个逻辑|只有这样|想到这里"), "connector", True),
    (re.compile(r"(?:(?<!不)(?:必须|需要|应该|只要|就会|可能|可以|能够|无法)|不能)[^。！？!?\n]{0,16}(?:判断|确认|承担|维持|稳住|控制|扩大|失控|带来|造成|理解|默认|回家|进门|核对|筛选|减少|建立|风险|结果|秩序|责任)"), "modal", True),
    (re.compile(r"(?:任务|条件|风险|来源|逻辑|局面|结果|责任|秩序|规则|信息不足|决策能力)"), "abstract", False),
]
_REASONING_CHAIN_MIN_HITS = 8
_REASONING_CHAIN_CORE_MIN_HITS = 4
_REASONING_CHAIN_MIN_BUCKETS = 2
_REASONING_CHAIN_PER_KILO = 18

# 碎句号
_STUTTER_MIN_RUN = 6
_STUTTER_MAX_SENTENCE = 5

# 长段落
_LONG_PARAGRAPH_CHARS = 200


def check_ai_patterns(text: str) -> list[dict]:
    """检测 AI 味文本模式,返回 findings 列表。

    每个 finding: {line, column, type, severity, message, excerpt}
    severity: 'blocking' (必须修复) 或 'advisory' (提示)
    """
    lines = text.split("\n")
    # 跳过 YAML front matter
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, min(len(lines), 40)):
            if lines[i].strip() == "---":
                start = i + 1
                break

    findings = []

    # 逐行扫描: 破折号 / 长段落 / 对比句式
    for i in range(start, len(lines)):
        line = lines[i]
        trimmed = line.strip()
        line_no = i + 1

        if not trimmed or _is_divider(trimmed) or _is_structural(trimmed):
            continue

        # 破折号
        for m in _DASH_RE.finditer(line):
            ctx = line[max(0, m.start() - 8):m.end() + 8]
            findings.append({
                "line": line_no, "column": m.start() + 1,
                "type": "em-dash",
                "severity": "blocking",
                "message": "破折号按功能改写:打断→动作 beat/短句,拖长音→省略或动作,插入说明→逗号/冒号;勿一律改句号。",
                "excerpt": _compact(ctx),
            })

        # 长段落
        if len(trimmed) > _LONG_PARAGRAPH_CHARS:
            findings.append({
                "line": line_no, "column": 1,
                "type": "long-paragraph",
                "severity": "advisory",
                "message": f"段落过长({len(trimmed)}字):按镜头/新动作/新线索/视线切换断段,别一段到底。",
                "excerpt": _compact(trimmed[:40]),
            })

        # 对比句式 "不是A,是B"
        narrative = _strip_quoted(line)
        for m in _NOT_IS_RE.finditer(narrative):
            findings.append({
                "line": line_no, "column": m.start() + 1,
                "type": "not-is-comparison",
                "severity": "blocking",
                "message": "高频 AI 对比句式;删掉否定铺垫,直接写后项,或改成动作/细节呈现。",
                "excerpt": _compact(m.group()),
            })

    # 全文级检测: 只统计引号外叙述
    prose_lines = []
    for i in range(start, len(lines)):
        trimmed = lines[i].strip()
        if not trimmed or _is_divider(trimmed) or _is_structural(trimmed):
            continue
        prose_lines.append((trimmed, i + 1))

    findings.extend(_find_period_stutter(prose_lines))
    findings.extend(_find_micro_action_tic(prose_lines))
    findings.extend(_find_action_list_tic(prose_lines))
    findings.extend(_find_abstract_summary_tic(prose_lines))
    findings.extend(_find_cliche_density_tic(prose_lines))
    findings.extend(_find_metaphor_density_tic(prose_lines))
    findings.extend(_find_reasoning_chain_tic(prose_lines))

    findings.sort(key=lambda f: (f["line"], f["column"]))
    return findings


def _find_period_stutter(prose_lines: list[tuple[str, int]]) -> list[dict]:
    """碎句号检测:连续短叙述句。"""
    findings = []
    run_len = 0
    run_start = None
    run_samples = []

    for text, line_no in prose_lines:
        narrative = _strip_quoted(text)
        if _visible_len(narrative) == 0:
            run_len = 0
            run_start = None
            run_samples = []
            continue

        for s in _split_sentences(narrative):
            if _visible_len(s) <= _STUTTER_MAX_SENTENCE:
                if run_len == 0:
                    run_start = line_no
                run_len += 1
                if len(run_samples) < 6:
                    run_samples.append(s)
            else:
                if run_len >= _STUTTER_MIN_RUN:
                    findings.append({
                        "line": run_start, "column": 1,
                        "type": "period-stutter",
                        "severity": "advisory",
                        "message": f"碎句号:连续{run_len}个短句无呼吸;按目标句长把碎句合并成中长句、补回画面与连接。",
                        "excerpt": _compact(" ".join(run_samples)),
                    })
                run_len = 0
                run_start = None
                run_samples = []

    if run_len >= _STUTTER_MIN_RUN:
        findings.append({
            "line": run_start, "column": 1,
            "type": "period-stutter",
            "severity": "advisory",
            "message": f"碎句号:连续{run_len}个短句无呼吸;按目标句长把碎句合并成中长句、补回画面与连接。",
            "excerpt": _compact(" ".join(run_samples)),
        })
    return findings


def _find_micro_action_tic(prose_lines: list[tuple[str, int]]) -> list[dict]:
    """微动作复读检测。"""
    hits = 0
    narrative_chars = 0
    first_line = None
    samples = []

    for text, line_no in prose_lines:
        narrative = _strip_quoted(text)
        narrative_chars += _visible_len(narrative)
        for m in _MICRO_TIC_RE.finditer(narrative):
            hits += 1
            if first_line is None:
                first_line = line_no
            if len(samples) < 6 and m.group() not in samples:
                samples.append(m.group())

    if narrative_chars == 0 or hits < _MICRO_TIC_MIN_HITS:
        return []
    per_kilo = (hits / narrative_chars) * 1000
    if per_kilo < _MICRO_TIC_PER_KILO:
        return []

    return [{
        "line": first_line, "column": 1,
        "type": "micro-action-tic",
        "severity": "advisory",
        "message": f"微动作复读:「了下/了一下」式轻量补语{hits}处({per_kilo:.1f}/千字);同一反应模板高密度复现是机械指纹,合并动作 beat、换具体细节。",
        "excerpt": _compact(" ".join(samples)),
    }]


def _find_action_list_tic(prose_lines: list[tuple[str, int]]) -> list[dict]:
    """监控摄像头式动作清单检测。"""
    findings = []

    for text, line_no in prose_lines:
        narrative = _strip_quoted(text).strip()
        if not narrative:
            continue
        verbs = _ACTION_LIST_RE.findall(narrative)
        if len(verbs) < _ACTION_LIST_MIN_HITS:
            continue
        separators = len(re.findall(r"[，、；;]", narrative))
        if separators < _ACTION_LIST_MIN_SEPARATORS:
            continue

        findings.append({
            "line": line_no, "column": 1,
            "type": "action-list-tic",
            "severity": "advisory",
            "message": f"监控摄像头式动作清单:同段连续动作动词{len(verbs)}个、分隔符{separators}个;合并琐碎步骤,只保留有情绪/情节功能的动作。",
            "excerpt": _compact(" ".join(verbs[:8])),
        })

    return findings


def _find_abstract_summary_tic(prose_lines: list[tuple[str, int]]) -> list[dict]:
    """抽象总结复读检测。"""
    hits = 0
    narrative_chars = 0
    first_line = None
    samples = []

    for text, line_no in prose_lines:
        narrative = _strip_quoted(text)
        narrative_chars += _visible_len(narrative)
        for pat in _ABSTRACT_SUMMARY_PATTERNS:
            for m in pat.finditer(narrative):
                hits += 1
                if first_line is None:
                    first_line = line_no
                sample = _compact(m.group(), 30)
                if len(samples) < 6 and sample not in samples:
                    samples.append(sample)

    if narrative_chars == 0 or hits < _ABSTRACT_SUMMARY_MIN_HITS:
        return []
    per_kilo = (hits / narrative_chars) * 1000
    if per_kilo < _ABSTRACT_SUMMARY_PER_KILO:
        return []

    return [{
        "line": first_line, "column": 1,
        "type": "abstract-summary-tic",
        "severity": "advisory",
        "message": f"抽象总结复读:命运/棋局/这一刻终于明白/才刚刚开始等作者总结{hits}处({per_kilo:.1f}/千字);回到角色当下可见的文件、动作、对话或物理后果。",
        "excerpt": _compact(" | ".join(samples)),
    }]


def _find_cliche_density_tic(prose_lines: list[tuple[str, int]]) -> list[dict]:
    """套词密度检测。"""
    hits = 0
    narrative_chars = 0
    first_line = None
    samples = []

    for text, line_no in prose_lines:
        narrative = _strip_quoted(text)
        narrative_chars += _visible_len(narrative)
        for pat in _CLICHE_PATTERNS:
            for m in pat.finditer(narrative):
                hits += 1
                if first_line is None:
                    first_line = line_no
                if len(samples) < 8 and m.group() not in samples:
                    samples.append(m.group())

    if narrative_chars == 0 or hits < _CLICHE_DENSITY_MIN_HITS:
        return []
    per_kilo = (hits / narrative_chars) * 1000
    if per_kilo < _CLICHE_DENSITY_PER_KILO:
        return []

    return [{
        "line": first_line, "column": 1,
        "type": "cliche-density-tic",
        "severity": "advisory",
        "message": f"套词密度过高:高危 AI 套词{hits}处({per_kilo:.1f}/千字);不要同义词轮换,改成角色当下可见的动作、物件、对话和具体后果。",
        "excerpt": _compact(" ".join(samples)),
    }]


def _find_metaphor_density_tic(prose_lines: list[tuple[str, int]]) -> list[dict]:
    """比喻密度检测。"""
    hits = 0
    narrative_chars = 0
    first_line = None
    samples = []

    for text, line_no in prose_lines:
        narrative = _strip_quoted(text)
        narrative_chars += _visible_len(narrative)
        for m in _METAPHOR_MARKER_RE.finditer(narrative):
            hits += 1
            if first_line is None:
                first_line = line_no
            sample = _compact(narrative[max(0, m.start() - 12):m.end() + 12], 40)
            if len(samples) < 6 and sample not in samples:
                samples.append(sample)
        for m in _METAPHOR_LIKE_RE.finditer(narrative):
            prefix = narrative[max(0, m.start() - 8):m.start()]
            if re.search(r"好像|像是|像|仿佛|宛如|如同|犹如", prefix):
                continue
            hits += 1
            if first_line is None:
                first_line = line_no

    if narrative_chars == 0 or hits < _METAPHOR_DENSITY_MIN_HITS:
        return []
    per_kilo = (hits / narrative_chars) * 1000
    if per_kilo < _METAPHOR_DENSITY_PER_KILO:
        return []

    return [{
        "line": first_line, "column": 1,
        "type": "metaphor-density-tic",
        "severity": "advisory",
        "message": f"比喻密度过高:像/好像/仿佛/如同等比喻标记{hits}处({per_kilo:.1f}/千字);保留最有叙事功能的少数比喻,其余回到具体动作、物件、声音或后果。",
        "excerpt": _compact(" | ".join(samples) if samples else ""),
    }]


def _find_reasoning_chain_tic(prose_lines: list[tuple[str, int]]) -> list[dict]:
    """解释链密度检测。"""
    hits = 0
    core_hits = 0
    narrative_chars = 0
    first_line = None
    samples = []
    buckets = set()

    for text, line_no in prose_lines:
        narrative = _strip_quoted(text)
        narrative_chars += _visible_len(narrative)
        for pat, key, core in _REASONING_CHAIN_PATTERNS:
            for m in pat.finditer(narrative):
                hits += 1
                if core:
                    core_hits += 1
                buckets.add(key)
                if first_line is None:
                    first_line = line_no
                sample = _compact(m.group(), 20)
                if len(samples) < 8 and sample not in samples:
                    samples.append(sample)

    if (narrative_chars == 0 or hits < _REASONING_CHAIN_MIN_HITS
            or core_hits < _REASONING_CHAIN_CORE_MIN_HITS
            or len(buckets) < _REASONING_CHAIN_MIN_BUCKETS):
        return []
    per_kilo = (hits / narrative_chars) * 1000
    if per_kilo < _REASONING_CHAIN_PER_KILO:
        return []

    return [{
        "line": first_line, "column": 1,
        "type": "reasoning-chain-tic",
        "severity": "advisory",
        "message": f"解释链密度过高:知道/明白/这意味着/必须/需要等判断链{hits}处({per_kilo:.1f}/千字);像逻辑报告时,把判断落到角色当下可见的动作、物件、对话和现场反馈。",
        "excerpt": _compact(" | ".join(samples)),
    }]


# ═══════════════════════════════════════════════════════════════════
# check_degeneration: 模型退化检测
# ═══════════════════════════════════════════════════════════════════

_REPEAT_MIN_LEN = 12
_REPEAT_MIN_COUNT = 3
_ADJACENT_MIN_LEN = 8

_PLACEHOLDER_PATTERNS = [
    (re.compile(r"作为(一个)?(AI|人工智能|大?语言模型|智能助手|聊天助手)(?=[，,。、；;：:！!？?\s）)」』\"】]|我|无法|不能|没法|$)"), "元信息泄漏(AI 自指)", False),
    (re.compile(r"\ufffd"), "乱码(替换字符 )", True),
    (re.compile(r"^(Sure|Certainly|Here'?s|As an AI|I (?:cannot|can't|am unable|apologize))"), "元信息泄漏(英文 AI 腔)", True),
    (re.compile(r"[（(](此处|以下|这里|下文|后续)?\s*(省略|略)(去|过)?[^）)]{0,10}[）)]"), "占位符(括号省略)", True),
    (re.compile(r"(未完待续|TODO|占位符|placeholder)"), "占位符", True),
    (re.compile(r"我(无法|不能)(继续(写|创作|生成|下去)|生成(内容|文本|正文)?|创作|续写|完成(这个|本)?(章|篇|创作|请求))"), "元信息泄漏(生成拒绝语)", False),
]

_META_TIER1_RE = re.compile(r"细纲|情节点|卷纲|功能标签|目标情绪|字数目标|章首钩子|章尾钩子")
_META_TIER2_RE = re.compile(r"第[一二三四五六七八九十百千万两0-9]+章|本章|这一章|上一章|下一章|上章|下章|前一章|后一章|前文|后文|伏笔|读者|任务描述")


def check_degeneration(text: str) -> list[dict]:
    """检测模型退化指纹,返回 findings 列表。

    检测维度:复读/打转、截断、占位/拒绝语、工程词泄漏。
    severity: 'blocking' (必须重写) 或 'advisory' (提示)
    """
    lines = text.split("\n")
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, min(len(lines), 40)):
            if lines[i].strip() == "---":
                start = i + 1
                break

    # 提取正文行 (跳过 front matter / fence / 结构行)
    body = []
    for i in range(start, len(lines)):
        trimmed = lines[i].strip()
        if not trimmed or trimmed.startswith("#") or _is_divider(trimmed):
            continue
        body.append({"text": lines[i], "trimmed": trimmed, "line_no": i + 1})

    findings = []
    findings.extend(_find_repetition(body))
    findings.extend(_find_truncation(body))
    findings.extend(_find_placeholders(body))
    findings.extend(_find_meta_leak(body))
    findings.sort(key=lambda f: (f["line"], f["column"]))
    return findings


def _find_repetition(body: list[dict]) -> list[dict]:
    """复读检测:紧邻整行重复 + 长句多次复现。"""
    findings = []

    # (1) 紧邻整行重复
    for i in range(1, len(body)):
        if (body[i]["trimmed"] == body[i - 1]["trimmed"]
                and _visible_len(_strip_quoted(body[i]["trimmed"])) >= _ADJACENT_MIN_LEN):
            findings.append({
                "line": body[i]["line_no"], "column": 1,
                "type": "verbatim-repeat",
                "severity": "blocking",
                "message": "逐行复读(紧邻整行重复):疑似模型打转,重写本段、删掉重复。",
                "excerpt": _compact(body[i]["trimmed"]),
            })

    # (2) 长句多次复现
    counts = {}
    for item in body:
        for s in _strip_quoted(item["trimmed"]).split("。"):
            s = s.strip()
            if _visible_len(s) < _REPEAT_MIN_LEN:
                continue
            entry = counts.get(s, {"count": 0, "first_line": None})
            entry["count"] += 1
            if entry["first_line"] is None:
                entry["first_line"] = item["line_no"]
            counts[s] = entry

    flagged = {s for s, e in counts.items() if e["count"] >= _REPEAT_MIN_COUNT}
    for s, entry in counts.items():
        if s in flagged:
            findings.append({
                "line": entry["first_line"], "column": 1,
                "type": "verbatim-repeat",
                "severity": "blocking",
                "message": f"长句复读(同句出现{entry['count']}次):疑似模型打转,重写、保留一处。",
                "excerpt": _compact(s),
            })
            flagged.discard(s)

    return findings


def _find_truncation(body: list[dict]) -> list[dict]:
    """截断检测:末尾无句末标点。"""
    if not body:
        return []
    last = body[-1]
    if _TERMINAL_RE.search(last["trimmed"]):
        return []
    return [{
        "line": last["line_no"], "column": len(last["trimmed"]),
        "type": "truncated",
        "severity": "blocking",
        "message": "疑似截断:正文末尾未以句末/收尾标点结束,可能被模型中途切断;补完结尾或重写收尾。",
        "excerpt": _compact(last["trimmed"][-24:]),
    }]


def _find_placeholders(body: list[dict]) -> list[dict]:
    """占位/拒绝语/元信息泄漏检测。"""
    findings = []
    for item in body:
        dialogue = _is_dialogue_like(item["trimmed"])
        for pat, label, hard in _PLACEHOLDER_PATTERNS:
            if not hard and dialogue:
                continue
            m = pat.search(item["trimmed"])
            if m:
                findings.append({
                    "line": item["line_no"], "column": (m.start() or 0) + 1,
                    "type": "placeholder-leak",
                    "severity": "blocking",
                    "message": f"{label}:正文混入元信息/拒绝语/占位符,重写本段干净落地。",
                    "excerpt": _compact(item["trimmed"][max(0, (m.start() or 0) - 4):(m.start() or 0) + 20]),
                })
                break
    return findings


def _find_meta_leak(body: list[dict]) -> list[dict]:
    """工程词泄漏检测。"""
    findings = []
    first_content_seen = False
    for item in body:
        if not first_content_seen:
            first_content_seen = True
            if re.match(r"^第[一二三四五六七八九十百千万两0-9]+章", item["trimmed"]):
                continue
        dialogue = _is_dialogue_like(item["trimmed"])
        m = _META_TIER1_RE.search(item["trimmed"])
        if m:
            findings.append({
                "line": item["line_no"], "column": m.start() + 1,
                "type": "meta-leak",
                "severity": "advisory" if dialogue else "blocking",
                "message": f"工程词泄漏:「{m.group()}」是写作流水线术语,正文里不该出现;改成角色/场景内表达。{'例外:角色为作者/编剧、在故事内真实讨论创作时,台词里可能合法。' if dialogue else ''}",
                "excerpt": _compact(item["trimmed"][max(0, m.start() - 6):m.start() + 18]),
            })
            continue
        m = _META_TIER2_RE.search(item["trimmed"])
        if m:
            findings.append({
                "line": item["line_no"], "column": m.start() + 1,
                "type": "meta-leak",
                "severity": "advisory",
                "message": f"元信息泄漏:「{m.group()}」疑似工程/章节结构词混入正文;改成角色当下可感知的事件锚点或相对时间。",
                "excerpt": _compact(item["trimmed"][max(0, m.start() - 6):m.start() + 18]),
            })
    return findings


# ═══════════════════════════════════════════════════════════════════
# normalize_punctuation: 标点标准化
# ═══════════════════════════════════════════════════════════════════

_PAUSE_RE = re.compile(r"…+|\\.{3,}|——|—|--+")


def normalize_punctuation(text: str, quote_mode: str = "keep") -> Tuple[str, list[dict]]:
    """标准化标点符号。返回 (normalized_text, findings)。

    - 替换省略号/破折号/双连字符为中文标点
    - 移除正文中的 markdown 分隔线
    - quote_mode: 'keep'(默认) | 'ascii' | 'yan'
    """
    newline = "\r\n" if "\r\n" in text else "\n"
    trailing_newline = text.endswith("\n")
    lines = text.split("\n")
    if trailing_newline:
        lines = lines[:-1] if lines[-1] == "" else lines

    findings = []
    output_lines = []
    in_fence = False
    in_front_matter = False
    quote_open = False

    # 检测 YAML front matter
    if lines and lines[0].strip() == "---":
        in_front_matter = True

    for i, line in enumerate(lines):
        line_no = i + 1
        trimmed = line.strip()

        if trimmed.startswith("```"):
            in_fence = not in_fence
            output_lines.append(line)
            continue

        if in_front_matter:
            output_lines.append(line)
            if i > 0 and trimmed == "---":
                in_front_matter = False
            continue

        if in_fence:
            output_lines.append(line)
            continue

        # 移除 markdown 分隔线
        if trimmed == "---":
            findings.append({
                "line": line_no, "column": line.index("-") + 1,
                "type": "markdown-divider",
                "message": "正文中不要使用 markdown 分隔线;建议移除该行。",
            })
            continue

        # 标准化停顿标点
        line, pause_findings = _normalize_pause(line, line_no)
        findings.extend(pause_findings)

        # 引号转换
        if quote_mode != "keep":
            line, quote_findings, quote_open = _normalize_quotes(line, quote_mode, quote_open, line_no)
            findings.extend(quote_findings)

        output_lines.append(line)

    result = newline.join(output_lines)
    if trailing_newline:
        result += newline
    return result, findings


def _normalize_pause(line: str, line_no: int) -> Tuple[str, list[dict]]:
    """标准化省略号/破折号/双连字符。"""
    findings = []
    output = ""
    last_idx = 0

    for m in _PAUSE_RE.finditer(line):
        output += line[last_idx:m.start()]
        token = m.group()
        replacement = _choose_pause_replacement(line, m.start(), len(token))
        output += replacement

        ptype = "double-hyphen" if token.startswith("-") else ("em-dash" if "—" in token else "ellipsis")
        findings.append({
            "line": line_no, "column": m.start() + 1,
            "type": ptype,
            "message": f"替换为「{replacement}」。" if replacement else "移除重复标点。",
        })
        last_idx = m.end()

    output += line[last_idx:]
    return output, findings


def _choose_pause_replacement(text: str, start: int, length: int) -> str:
    """选择停顿标点的替换方案。"""
    before = _prev_non_space(text, start - 1)
    after = _next_non_space(text, start + length)
    rest = text[start + length:].lstrip()

    if before == "":
        return ""
    # 紧跟开引号/开括号 → 删空
    if before in "「『（(\"“‘":
        return ""
    # 数字区间
    if before.isdigit() and after.isdigit():
        return "到"
    # 紧接闭引号
    if after in "\"”」』":
        return "" if before in "，,。.!！?？;；:：" else "。"
    if not after:
        return "" if before in "，,。.!！?？;；:：" else "。"
    if before in "，,。.!！?？;；:：" or after in "，,。.!！?？;；:：、…\"\"“”'‘’」』）)]":
        return ""
    # 解释性连接
    if re.match(r"^(因为|原来|这是|那是|也就是|换句话|说白了|所谓|答案|原因|结果|真相|问题在于)", rest):
        return ":"
    if re.search(r"(原因|答案|真相|结果|结论|问题|选择|意思)$", text[:start].rstrip()):
        return ":"
    return "，"


def _prev_non_space(text: str, idx: int) -> str:
    for i in range(idx, -1, -1):
        if not text[i].isspace():
            return text[i]
    return ""


def _next_non_space(text: str, idx: int) -> str:
    for i in range(idx, len(text)):
        if not text[i].isspace():
            return text[i]
    return ""


def _normalize_quotes(line: str, mode: str, quote_open: bool, line_no: int) -> Tuple[str, list[dict], bool]:
    """引号风格转换。"""
    findings = []
    output = ""

    for i, ch in enumerate(line):
        if mode == "ascii" and ch in "「」『』""":
            output += '"'
            findings.append({
                "line": line_no, "column": i + 1,
                "type": "quote-style",
                "message": "按显式 quote-mode 转为半角双引号。",
            })
        elif mode == "yan" and ch in '""“”':
            repl = "」" if quote_open or ch == "”" else "「"
            output += repl
            quote_open = (repl == "「")
            findings.append({
                "line": line_no, "column": i + 1,
                "type": "quote-style",
                "message": "按显式 quote-mode 转为盐言引号。",
            })
        else:
            output += ch

    return output, findings, quote_open


# ═══════════════════════════════════════════════════════════════════
# 便捷汇总函数
# ═══════════════════════════════════════════════════════════════════

def run_full_deai_check(text: str) -> dict:
    """执行完整的去AI味检测流程,返回综合报告。

    返回: {
        "ai_patterns": [...],       # AI 味模式检测
        "degeneration": [...],      # 模型退化检测
        "punctuation": [...],       # 标点标准化
        "normalized_text": str,     # 标准化后的文本
        "blocking_count": int,      # 必须修复的问题数
        "advisory_count": int,      # 建议修复的问题数
    }
    """
    ai = check_ai_patterns(text)
    deg = check_degeneration(text)
    normalized, punct = normalize_punctuation(text)

    blocking = sum(1 for f in ai + deg if f["severity"] == "blocking")
    advisory = sum(1 for f in ai + deg if f["severity"] == "advisory")

    return {
        "ai_patterns": ai,
        "degeneration": deg,
        "punctuation": punct,
        "normalized_text": normalized,
        "blocking_count": blocking,
        "advisory_count": advisory,
        "punctuation_count": len(punct),
    }
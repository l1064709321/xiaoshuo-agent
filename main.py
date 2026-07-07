#!/usr/bin/env python3
"""
网文写作参考工具 - 自包含CLI版
用法:
  python3 main.py list                         # 列出所有作家
  python3 main.py list --category=玄幻仙侠     # 按分类筛选
  python3 main.py search --name=辰东            # 按名字搜索（支持别名，如"土豆"→"天蚕土豆"）
  python3 main.py search --keyword=克苏鲁       # 按关键词搜索
  python3 main.py deconstruct --name=辰东        # 深度拆解某作家风格（基因测序级）
  python3 main.py deconstruct --keyword=武侠      # 按分类/关键词拆解
  python3 main.py audit --file=chapter.txt       # 33维审计章节
  python3 main.py audit --file=chapter.txt --outline=outline.txt  # 带大纲审计
  python3 main.py ai --file=chapter.txt          # AI味检测
  python3 main.py opening --file=chapter.txt     # 黄金三章诊断
  python3 main.py style --file=chapter.txt       # 文风分析（输出风格指纹）
  python3 main.py style --file=chapter.txt --name=辰东  # 文风分析+匹配大神
  python3 main.py imitate --file=sample.txt --topic="修仙世界的拍卖会"  # 文风仿写
  python3 main.py imitate --file=sample.txt --topic="修仙世界的拍卖会" --author=辰东  # 文风仿写+原文参考
  python3 main.py stuck --file=chapter.txt       # 卡文诊断（识别卡点+续写路径）
  python3 main.py scout                          # 扫榜（市场趋势推荐）
  python3 main.py scout --category=玄幻仙侠      # 按分类扫榜
  python3 main.py outline --concept="废柴逆袭"   # 生成大纲
  python3 main.py outline --concept="废柴逆袭" --volumes=5  # 指定卷数
  python3 main.py ghostwrite --outline=outline.txt --chapter=1 --words=3000  # 枪手代笔
  python3 main.py ghostwrite --outline=outline.txt --style=sample.txt        # 指定文风代笔
  python3 main.py ghostwrite --outline=outline.txt --author=辰东            # 代笔+原文语料参考
  python3 main.py pipeline --concept="废柴逆袭"  # 完整编辑部流水线
  python3 main.py pipeline --concept="废柴逆袭" --author=辰东 --rounds=3  # 流水线+迭代
  python3 main.py full --file=chapter.txt        # 完整审计（33维+AI味，一次搞定）
  python3 main.py corpus --author=辰东           # 查看某作者的原文语料
  python3 main.py corpus --keyword=战斗          # 按关键词搜索语料
  python3 main.py check --file=chapter.txt       # 版权检测（检查是否包含原文金句）
"""
import sys
import os
import json
import re

# 导入 skills.py 中的全部模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from skills import (
        NOVEL_DECONSTRUCTION_DB,
        AUTHOR_ALIASES,
        DeconstructionParser,
        DeconstructionMatcher,
        DeconstructionPromptGenerator,
        NovelDeconstructionSkill,
        NovelAuditor,
        AIDetector,
        ContinuationEngine,
        StyleImitator,
        OpeningDiagnosis,
        EditorialPipeline,
    )
    # 导入语料库
    try:
        from corpus.loader import get_corpus_loader
        HAS_CORPUS = True
    except ImportError:
        HAS_CORPUS = False
        def get_corpus_loader():
            return None
except ImportError as e:
    print(f"错误: 导入 skills.py 失败 - {e}")
    print("请确保 skills.py 在同一目录下。")
    sys.exit(1)


def _read_file(filepath, label="文件"):
    """读取文件内容，失败时打印提示并返回 None。"""
    if not filepath or not os.path.exists(filepath):
        print(f"用法错误: 请提供有效的{label}路径 (--file=xxx)")
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def _find_author(name):
    """通过名字或别名查找作家，返回匹配的作者数据或 None。"""
    # 先查别名表
    real_name = AUTHOR_ALIASES.get(name, name)
    for a in NOVEL_DECONSTRUCTION_DB:
        if a["name"] == real_name or real_name in a["name"]:
            return a
    return None


def _parse_kv(args, key, default=None):
    """从命令行参数列表中提取 --key=value 形式的值。"""
    prefix = f"--{key}="
    for arg in args:
        if arg.startswith(prefix):
            return arg.split("=", 1)[1]
    return default


def _format_author_brief(author):
    """格式化作家简要信息。"""
    lines = [f"  {author['name']} | {author.get('genre', '')}"]
    if 'lexicon_logic' in author:
        words = author['lexicon_logic'].get('高频词', [])
        if words:
            lines.append(f"    高频词: {', '.join(words[:6])}")
    if 'environment_logic' in author:
        env = author['environment_logic'].get('典型环境', '')
        if env:
            lines.append(f"    环境: {env[:60]}")
    return "\n".join(lines)


# ============================================================
# 命令实现
# ============================================================

def cmd_list(args):
    """列出作家"""
    category = _parse_kv(args, "category")
    results = NOVEL_DECONSTRUCTION_DB
    if category:
        results = [a for a in results if category in a.get("category", "")]

    if not results:
        print(f"未找到分类: {category}")
        cats = sorted(set(a.get("category", "未分类") for a in NOVEL_DECONSTRUCTION_DB))
        print(f"可用分类: {', '.join(cats)}")
        return

    current_cat = None
    for author in results:
        cat = author.get("category", "未分类")
        if cat != current_cat:
            current_cat = cat
            print(f"\n## {current_cat}\n")
        print(_format_author_brief(author))
        print()


def cmd_search(args):
    """搜索作家（支持别名）"""
    name = _parse_kv(args, "name")
    keyword = _parse_kv(args, "keyword")

    if not name and not keyword:
        print("用法: python3 main.py search --name=辰东  或  --keyword=克苏鲁")
        return

    results = []
    for author in NOVEL_DECONSTRUCTION_DB:
        matched = False
        # 名字匹配（含别名）
        if name:
            real_name = AUTHOR_ALIASES.get(name, name)
            if real_name in author["name"]:
                matched = True
        # 关键词全字段搜索
        if keyword:
            searchable = json.dumps(author, ensure_ascii=False)
            if keyword in searchable:
                matched = True
        if matched:
            results.append(author)

    if not results:
        print("未找到匹配的作家。")
        # 提示相近的
        if name:
            aliases = [k for k, v in AUTHOR_ALIASES.items() if name in k or name in v]
            if aliases:
                print(f"你是否想找: {', '.join(aliases)}")
        return

    for author in results:
        print(f"\n【{author['name']}】{author.get('category', '')} / {author.get('genre', '')}")
        if 'lexicon_logic' in author:
            words = author['lexicon_logic'].get('高频词', [])
            print(f"  高频词: {', '.join(words[:8])}")
            print(f"  词汇拆析: {author['lexicon_logic'].get('拆析', '')[:100]}")
        if 'quotes_and_actions' in author:
            for qa in author['quotes_and_actions'][:2]:
                if 'quote' in qa:
                    print(f"  经典台词: 「{qa['quote']}」")
                elif 'action' in qa:
                    print(f"  经典动作: {qa['action'][:60]}")
        print()


def cmd_deconstruct(args):
    """深度拆解作家风格"""
    name = _parse_kv(args, "name")
    keyword = _parse_kv(args, "keyword")

    # 如果输入的是别名，先转换
    if name:
        real_name = AUTHOR_ALIASES.get(name, name)
        user_input = f"帮我拆解{real_name}的风格"
    elif keyword:
        user_input = f"帮我拆解{keyword}类作者的风格"
    else:
        print("用法: python3 main.py deconstruct --name=辰东  或  --keyword=武侠")
        return

    skill = NovelDeconstructionSkill()
    result = skill.execute(user_input, return_prompt_only=True)
    print(result)


def cmd_audit(args):
    """33维审计"""
    filepath = _parse_kv(args, "file")
    outline_path = _parse_kv(args, "outline")

    text = _read_file(filepath, "章节文件")
    if text is None:
        return

    outline = None
    if outline_path:
        outline = _read_file(outline_path, "大纲文件")

    auditor = NovelAuditor()
    report = auditor.audit(text, outline)
    print(auditor.format_report(report))


def cmd_ai(args):
    """AI味检测"""
    filepath = _parse_kv(args, "file")
    text = _read_file(filepath, "章节文件")
    if text is None:
        return

    detector = AIDetector()
    issues = detector.detect(text)
    print(detector.format_report(issues))


def cmd_opening(args):
    """黄金三章诊断"""
    filepath = _parse_kv(args, "file")
    text = _read_file(filepath, "章节文件")
    if text is None:
        return

    opener = OpeningDiagnosis()
    report = opener.diagnose(text)
    print(opener.format_report(report))


def cmd_style(args):
    """文风分析"""
    filepath = _parse_kv(args, "file")
    author_name = _parse_kv(args, "name")
    text = _read_file(filepath, "章节文件")
    if text is None:
        return

    imitator = StyleImitator(NOVEL_DECONSTRUCTION_DB)
    analysis = imitator.analyze_style(text, author_name)

    print("=" * 50)
    print("  🔍 文风指纹分析")
    print("=" * 50)
    print(f"  总字数: {analysis['word_count']}")
    print(f"  平均句长: {analysis['sentence_avg_len']:.1f}字")
    print(f"  对话占比: {analysis['dialogue_ratio']:.0%}")
    print(f"  段落平均长度: {analysis['paragraph_avg_len']:.0f}字")
    print(f"  形容词密度: {analysis['adjective_density']:.4f}")
    print(f"  感叹号频率: {analysis['exclamation_rate']:.4f}")
    print(f"  省略号频率: {analysis['ellipsis_rate']:.4f}")
    print(f"  疑问号频率: {analysis.get('question_rate', 0):.4f}")
    print(f"  动作密度: {analysis.get('action_density', 0):.4f}")
    print(f"  心理描写密度: {analysis.get('mind_density', 0):.4f}")
    print()
    print(f"  风格标签: {', '.join(analysis['style_tags'])}")
    print(f"  高频词: {', '.join(analysis['top_words'][:10])}")

    if author_name and analysis.get("matched_author", {}).get("match") != "none":
        ma = analysis["matched_author"]
        print(f"\n  匹配大神: {ma['name']} ({ma.get('genre', '')})")
    elif author_name:
        print(f"\n  ⚠ 未在数据库中找到大神「{author_name}」的风格参照")
    print()


def cmd_imitate(args):
    """文风仿写（支持原文语料参考）"""
    filepath = _parse_kv(args, "file")
    topic = _parse_kv(args, "topic")
    author_name = _parse_kv(args, "author")
    word_count = int(_parse_kv(args, "words", "800"))

    text = _read_file(filepath, "样本文件")
    if text is None:
        return
    if not topic:
        print("用法: python3 main.py imitate --file=sample.txt --topic='修仙世界的拍卖会' [--author=辰东]")
        return

    imitator = StyleImitator(NOVEL_DECONSTRUCTION_DB)
    analysis = imitator.analyze_style(text)
    prompt = imitator.generate_imitation(analysis, topic, word_count, author_name=author_name)

    print("=" * 50)
    print("  ✍️  仿写 Prompt（可直接喂给AI）")
    if author_name:
        print(f"  📚 原文语料参考：{author_name}")
    print("=" * 50)
    print(prompt)


def cmd_stuck(args):
    """卡文诊断"""
    filepath = _parse_kv(args, "file")
    text = _read_file(filepath, "章节文件")
    if text is None:
        return

    engine = ContinuationEngine(NOVEL_DECONSTRUCTION_DB)

    # 先做五维分析
    report = engine.analyze(text)
    print("=" * 50)
    print("  🩺 卡文诊断报告")
    print("=" * 50)
    print(f"  结构: {report['structure']}")
    print(f"  人物: {report['characters']}")
    print(f"  风格: {report['style']}")
    print(f"  伏笔: {report['foreshadowing']}")
    print(f"  爽点: {report['satisfaction']}")
    print()

    # 诊断卡点
    diagnosis = engine.diagnose_stuck(text)
    print(f"  🔴 卡文类型: {diagnosis['stuck_type']}")
    print()
    print("  📋 推荐续写路径:")
    for i, path in enumerate(diagnosis["paths"], 1):
        print(f"    {i}. 【{path['name']}】{path['desc']}")
        print(f"       优点: {path['pros']} | 风险: {path['cons']}")
    print()


def cmd_scout(args):
    """扫榜"""
    category = _parse_kv(args, "category")
    pipeline = EditorialPipeline(NOVEL_DECONSTRUCTION_DB)
    report = pipeline.scout(genre=category)
    print(pipeline.format_scout_report(report))


def cmd_outline(args):
    """生成大纲"""
    concept = _parse_kv(args, "concept")
    volumes = int(_parse_kv(args, "volumes", "3"))

    if not concept:
        print("用法: python3 main.py outline --concept='废柴逆袭' [--volumes=3]")
        return

    pipeline = EditorialPipeline(NOVEL_DECONSTRUCTION_DB)
    prompt = pipeline.outline(concept, volumes)
    print("=" * 50)
    print("  📝 大纲生成 Prompt（可直接喂给AI）")
    print("=" * 50)
    print(prompt)


def cmd_ghostwrite(args):
    """枪手代笔（支持原文语料参考）"""
    outline_path = _parse_kv(args, "outline")
    style_path = _parse_kv(args, "style")
    author_name = _parse_kv(args, "author")
    chapter = int(_parse_kv(args, "chapter", "1"))
    words = int(_parse_kv(args, "words", "3000"))

    outline_text = _read_file(outline_path, "大纲文件")
    if outline_text is None:
        return

    style_ref = None
    if style_path:
        style_ref = _read_file(style_path, "文风参考文件")

    pipeline = EditorialPipeline(NOVEL_DECONSTRUCTION_DB)
    prompt = pipeline.ghostwriter(outline_text, style_ref, chapter, words, author_name=author_name)
    print("=" * 50)
    print(f"  📖 枪手代笔 Prompt（第{chapter}章，约{words}字）")
    if author_name:
        print(f"  📚 原文语料参考：{author_name}")
    print("=" * 50)
    print(prompt)


def cmd_pipeline(args):
    """完整编辑部流水线（含迭代机制）"""
    concept = _parse_kv(args, "concept")
    author_name = _parse_kv(args, "author")
    max_rounds = int(_parse_kv(args, "rounds", "3"))

    if not concept:
        print("用法: python3 main.py pipeline --concept='废柴逆袭' [--author=辰东] [--rounds=3]")
        return

    pipeline = EditorialPipeline(NOVEL_DECONSTRUCTION_DB)
    results = pipeline.run_pipeline(concept, author_name=author_name, max_rounds=max_rounds)

    print("=" * 50)
    print("  🏭 AI编辑部流水线（迭代版）")
    if author_name:
        print(f"  📚 原文语料参考：{author_name}")
    print(f"  🔄 最大迭代轮次：{max_rounds}")
    print("=" * 50)
    print()
    print(pipeline.format_scout_report(results["scout"]))
    print()
    print("=" * 50)
    print("  📝 大纲生成 Prompt")
    print("=" * 50)
    print(results["outline_prompt"])
    print()
    print("=" * 50)
    print("  📋 流水线步骤（含迭代）")
    print("=" * 50)
    for i, step in enumerate(results["next_steps"], 1):
        print(f"  {i}. {step}")
    print()
    if author_name:
        print("=" * 50)
        print("  💡 迭代写作说明")
        print("=" * 50)
        print("  1. 用 ghostwrite 生成初稿（自动注入原文参考）")
        print("  2. 用 audit 审计初稿")
        print("  3. 有严重问题则用 rewriter 修改")
        print("  4. 重复2-3，直到没有严重问题")
        print()


def cmd_corpus(args):
    """查看原文语料库"""
    if not HAS_CORPUS:
        print("⚠️ 语料库模块未安装，请确保 corpus/ 目录存在。")
        return

    author_name = _parse_kv(args, "author")
    keyword = _parse_kv(args, "keyword")
    scene_type = _parse_kv(args, "scene")

    loader = get_corpus_loader()

    if author_name:
        passages = loader.get_passages(author_name, scene_type=scene_type)
        if not passages:
            print(f"未找到 {author_name} 的语料。")
            print(f"可用作者：{', '.join(loader.get_all_authors())}")
            return
        print("=" * 50)
        print(f"  📚 {author_name} 原文语料库")
        if scene_type:
            print(f"  🏷️ 场景类型：{scene_type}")
        print("=" * 50)
        for i, p in enumerate(passages, 1):
            tags = "·".join(p.get("tags", []))
            source = p.get("source", "")
            quality = "⭐" * p.get("quality", 3)
            print(f"\n【片段{i}】{tags} {quality}")
            if source:
                print(f"来源：{source}")
            print("-" * 40)
            print(p["text"])
    elif keyword:
        results = loader.search_by_keyword(keyword)
        if not results:
            print(f"未找到包含'{keyword}'的语料。")
            return
        print("=" * 50)
        print(f"  🔍 搜索结果：{keyword}")
        print("=" * 50)
        for r in results:
            print(f"\n【{r['author']}】{'·'.join(r['tags'])}")
            print(r["text"])
    else:
        authors = loader.get_all_authors()
        print("=" * 50)
        print("  📚 原文语料库")
        print("=" * 50)
        print(f"\n已收录 {len(authors)} 位作者：")
        for a in authors:
            count = len(loader.get_passages(a))
            print(f"  • {a}（{count}个段落）")
        print(f"\n用法：python3 main.py corpus --author=辰东")
        print(f"       python3 main.py corpus --keyword=战斗")
        print(f"       python3 main.py corpus --author=辰东 --scene=battle")


def cmd_full(args):
    """完整审计（33维 + AI味检测）"""
    filepath = _parse_kv(args, "file")
    outline_path = _parse_kv(args, "outline")

    text = _read_file(filepath, "章节文件")
    if text is None:
        return

    outline = None
    if outline_path:
        outline = _read_file(outline_path, "大纲文件")

    skill = NovelDeconstructionSkill()
    result = skill.full_audit(text, outline)

    print(result["audit"])
    print()
    print(result["ai_flavor"])


def cmd_check(args):
    """版权检测：检查文本中是否包含已知原文金句"""
    filepath = _parse_kv(args, "file")

    text = _read_file(filepath, "章节文件")
    if text is None:
        return

    from skills import check_copyright_violation, format_copyright_report
    violations = check_copyright_violation(text)
    print(format_copyright_report(violations))


# ============================================================
# 入口
# ============================================================

COMMANDS = {
    "list": cmd_list,
    "search": cmd_search,
    "deconstruct": cmd_deconstruct,
    "audit": cmd_audit,
    "ai": cmd_ai,
    "opening": cmd_opening,
    "style": cmd_style,
    "imitate": cmd_imitate,
    "stuck": cmd_stuck,
    "scout": cmd_scout,
    "outline": cmd_outline,
    "ghostwrite": cmd_ghostwrite,
    "pipeline": cmd_pipeline,
    "corpus": cmd_corpus,
    "check": cmd_check,
    "full": cmd_full,
}


def main():
    args = sys.argv[1:]
    if len(args) < 1:
        print(__doc__)
        return

    command = args[0]
    if command in COMMANDS:
        COMMANDS[command](args[1:])
    else:
        print(f"未知命令: {command}")
        print(f"可用命令: {', '.join(COMMANDS.keys())}")
        print(__doc__)


if __name__ == "__main__":
    main()

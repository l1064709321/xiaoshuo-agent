#!/usr/bin/env python3
"""
网文写作参考工具 - 自包含CLI版
用法:
  python3 main.py list                         # 列出所有作家
  python3 main.py list --category=玄幻仙侠     # 按分类筛选
  python3 main.py search --name=辰东            # 按名字搜索
  python3 main.py search --keyword=克苏鲁       # 按关键词搜索
  python3 main.py audit --file=chapter.txt      # 审计章节
  python3 main.py style --name=辰东 --file=chapter.txt  # 用某作家风格改写参考
"""
import sys
import os
import json
import re

# 导入作家数据库（假设 skills.py 在同一目录，并定义了 AUTHOR_DATABASE）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from skills import AUTHOR_DATABASE
except ImportError:
    print("错误: 需要 skills.py 文件并在其中定义 AUTHOR_DATABASE 列表")
    sys.exit(1)


def cmd_list(args):
    """列出作家"""
    category = None
    for arg in args:
        if arg.startswith("--category="):
            category = arg.split("=", 1)[1]

    results = AUTHOR_DATABASE
    if category:
        results = [a for a in results if category in a["category"]]

    if not results:
        print(f"未找到分类: {category}")
        cats = sorted(set(a["category"] for a in AUTHOR_DATABASE))
        print(f"可用分类: {', '.join(cats)}")
        return

    current_cat = None
    for author in results:
        if author["category"] != current_cat:
            current_cat = author["category"]
            print(f"\n## {current_cat}\n")
        print(f"  {author['name']} | {author['genre']}")
        print(f"    {author['features']}")
        print(f"    适用: {author['scenarios']}")
        print()


def cmd_search(args):
    """搜索作家"""
    name = None
    keyword = None
    for arg in args:
        if arg.startswith("--name="):
            name = arg.split("=", 1)[1]
        elif arg.startswith("--keyword="):
            keyword = arg.split("=", 1)[1]

    results = []
    for author in AUTHOR_DATABASE:
        if name and name in author["name"]:
            results.append(author)
        elif keyword:
            searchable = json.dumps(author, ensure_ascii=False)
            if keyword in searchable:
                results.append(author)

    if not results:
        print("未找到匹配的作家。")
        return

    for author in results:
        print(f"\n【{author['name']}】{author['category']} / {author['genre']}")
        print(f"  风格: {author['features']}")
        print(f"  适用: {author['scenarios']}")


def cmd_audit(args):
    """多维度审计章节（33维审计简化版）"""
    filepath = None
    for arg in args:
        if arg.startswith("--file="):
            filepath = arg.split("=", 1)[1]

    if not filepath or not os.path.exists(filepath):
        print("用法: python3 main.py audit --file=chapter.txt")
        print("请提供有效的章节文件路径。")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    issues = []
    line_count = text.count("\n") + 1
    char_count = len(text)

    # 1. AI味检测
    ai_phrases = [
        "值得一提的是", "需要指出的是", "不禁让人", "引发了广泛关注",
        "众所周知", "不可否认", "总而言之", "综上所述",
        "首先.*其次.*最后", "一方面.*另一方面",
        "让我们", "接下来让我们",
    ]
    for phrase in ai_phrases:
        matches = re.findall(phrase, text)
        if matches:
            issues.append(f"[AI味] 检测到套话 '{phrase}' x{len(matches)}，建议替换为具体动作或对话")

    # 2. 感叹号密度
    excl_count = text.count("！") + text.count("!")
    if excl_count > line_count * 0.3:
        issues.append(f"[节奏] 感叹号过多({excl_count}个/{line_count}行)，密度偏高，建议减少以增强冲击力")

    # 3. 对话比例
    dialog_lines = len(re.findall(r'[""「」『』]', text)) // 2
    dialog_ratio = dialog_lines / max(line_count, 1)
    if dialog_ratio < 0.1:
        issues.append(f"[节奏] 对话比例偏低({dialog_ratio:.0%})，建议增加对话推动情节")
    elif dialog_ratio > 0.6:
        issues.append(f"[节奏] 对话比例偏高({dialog_ratio:.0%})，建议增加描写和叙述")

    # 4. 省略号/破折号滥用
    ellipsis_count = text.count("……") + text.count("...")
    dash_count = text.count("——")
    if ellipsis_count > line_count * 0.2:
        issues.append(f"[文风] 省略号过多({ellipsis_count}个)，建议用动作或沉默代替")
    if dash_count > line_count * 0.15:
        issues.append(f"[文风] 破折号过多({dash_count}个)，建议精简")

    # 5. 重复词检测
    words = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
    word_freq = {}
    for w in words:
        word_freq[w] = word_freq.get(w, 0) + 1
    repeats = [(w, c) for w, c in word_freq.items() if c >= 5 and len(w) >= 2]
    repeats.sort(key=lambda x: -x[1])
    if repeats[:5]:
        top = ", ".join(f"'{w}'x{c}" for w, c in repeats[:5])
        issues.append(f"[词汇] 高频重复词: {top}，建议替换同义表达")

    # 6. 段落长度
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    long_paras = [i for i, p in enumerate(paragraphs) if len(p) > 500]
    if long_paras:
        issues.append(f"[结构] 第{', '.join(str(i+1) for i in long_paras[:3])}段过长(>500字)，建议拆分")

    # 7. 五感缺失检测
    senses = {
        "视觉": ["看", "见", "望", "盯", "瞧", "目光", "眼神", "眼里"],
        "听觉": ["听", "声", "响", "叫", "喊", "吼", "鸣", "嗡", "咔"],
        "嗅觉": ["闻", "味", "气息", "臭", "香", "腥", "糊"],
        "触觉": ["摸", "触", "烫", "冷", "热", "疼", "痛", "硬", "软"],
        "味觉": ["尝", "苦", "甜", "咸", "辣", "涩"],
    }
    missing_senses = []
    for sense, keywords in senses.items():
        if not any(k in text for k in keywords):
            missing_senses.append(sense)
    if missing_senses:
        issues.append(f"[五感] 缺少{', '.join(missing_senses)}描写，建议加入感官细节增强代入感")

    # 8. 章节钩子检测（最后100字）
    last_chars = text[-100:]
    hook_signals = ["突然", "忽然", "就在这时", "不料", "然而", "……", "——"]
    has_hook = any(s in last_chars for s in hook_signals)
    if not has_hook:
        issues.append("[钩子] 章节结尾缺乏悬念或转折钩子，建议加入意外元素吸引读者继续阅读")

    # 9. 平均句长
    sentences = re.split(r'[。！？\n]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if sentences:
        avg_len = sum(len(s) for s in sentences) / len(sentences)
        if avg_len > 80:
            issues.append(f"[文笔] 平均句长{avg_len:.0f}字，偏长，建议拆分长句，增强节奏感")
        elif avg_len < 15:
            issues.append(f"[文笔] 平均句长{avg_len:.0f}字，偏短，可能需要添加细节")

    # 输出报告
    print(f"\n{'='*50}")
    print(f"审计报告: {filepath}")
    print(f"总字数: {char_count} | 行数: {line_count} | 段落数: {len(paragraphs)}")
    print(f"{'='*50}")
    if not issues:
        print("✅ 未发现明显问题，继续保持！")
    else:
        print(f"发现 {len(issues)} 个潜在问题:\n")
        for idx, issue in enumerate(issues, 1):
            print(f"  [{idx}] {issue}")
    print()


def cmd_style(args):
    """根据作家风格对文本进行改写建议"""
    name = None
    filepath = None
    for arg in args:
        if arg.startswith("--name="):
            name = arg.split("=", 1)[1]
        elif arg.startswith("--file="):
            filepath = arg.split("=", 1)[1]

    if not name or not filepath or not os.path.exists(filepath):
        print("用法: python3 main.py style --name=辰东 --file=chapter.txt")
        print("请提供作家姓名和章节文件路径。")
        return

    # 查找作家
    author = None
    for a in AUTHOR_DATABASE:
        if name in a["name"]:
            author = a
            break
    if not author:
        print(f"未找到作家: {name}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    # 简单风格建议（基于特征关键词）
    print(f"\n{'='*50}")
    print(f"风格参考: {author['name']} ({author['genre']})")
    print(f"核心特征: {author['features']}")
    print(f"{'='*50}\n")

    # 基础分析
    tips = []

    genre = author["genre"]
    features = author["features"]

    # 针对不同流派给出通用建议
    if "史诗" in genre or "史诗" in features:
        tips.append("增加宏大场景描写，用壮阔的自然景观或战争场面烘托气势")
    if "爽文" in genre:
        tips.append("强化打脸节奏，每章至少安排一个小高潮或实力展示")
    if "凡人流" in genre:
        tips.append("突出资源匮乏感，主角获得每件物品都要付出代价")
    if "克苏鲁" in genre or "诡异" in genre:
        tips.append("添加不可名状的细节描写，用未知感和心理恐惧取代直观惊吓")
    if "搞笑" in genre or "吐槽" in genre:
        tips.append("加入内心吐槽独白，用反差和意外制造笑点")
    if "治愈" in genre:
        tips.append("增加日常温馨场景，用细节动作传递温暖")
    if "虐恋" in genre or "残酷" in genre:
        tips.append("强化情感冲突，用不得已的选择制造悲剧美感")
    if "种田" in genre:
        tips.append("细化日常生活细节，用真实感营造沉浸体验")

    # 通用建议
    tips.extend([
        "检查开篇是否在300字内出现核心冲突或悬念",
        "确保每章结尾有钩子（悬念/反转/新信息）",
        "对话尽量带上动作和表情，避免纯对白",
    ])

    print("【改写建议】")
    for i, tip in enumerate(tips[:7], 1):  # 最多7条
        print(f"  {i}. {tip}")

    # 给出范文片段风格分析
    print("\n【风格关键词】")
    keywords = re.findall(r'[\u4e00-\u9fff]{2,4}', features)
    print(f"  {', '.join(keywords[:8])}")

    print("\n【章节快速诊断】")
    # 复用部分审计逻辑
    lines = text.split("\n")
    print(f"  当前字数: {len(text)}")
    print(f"  段落数: {len([l for l in lines if l.strip()])}")
    dialog_count = len(re.findall(r'[""「」『』]', text)) // 2
    print(f"  对话行数估计: {dialog_count}")

    if "爽文" in genre and len(text) < 2000:
        print("  ⚠️ 章节较短，爽文建议每章至少2500字以维持信息密度")
    if "史诗" in genre and len(text) > 5000:
        print("  ⚠️ 史诗类章节不宜过长，建议控制在3500字左右，保持节奏")
    print()


def main():
    """命令行入口"""
    args = sys.argv[1:]

    if len(args) < 1:
        print(__doc__)
        return

    command = args[0]
    cmd_args = args[1:]

    if command == "list":
        cmd_list(cmd_args)
    elif command == "search":
        cmd_search(cmd_args)
    elif command == "audit":
        cmd_audit(cmd_args)
    elif command == "style":
        cmd_style(cmd_args)
    else:
        print(f"未知命令: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
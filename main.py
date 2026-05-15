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

# 导入作家数据库
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skills import AUTHOR_DATABASE


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
        print(f"可用分类: {', '.join(sorted(set(a['category'] for a in AUTHOR_DATABASE)))}")
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
    """多维度审计章节"""
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

    # 7. 五感检测
    senses = {
        "视觉": ["看", "见", "望", "盯", "瞧", "目光", "眼神", "眼里"],
        "听觉": ["听", "声", "响", "叫", "喊", "吼", "鸣", "嗡", "咔"],
        "嗅觉": ["闻", "味", "气息", "臭", "香", "腥", "糊"],
        "触觉": ["摸", "触", "烫", "冷", "热", "疼", "痛", "硬", "软"],
        "味觉": ["尝", "苦", "甜", "咸", "辣", "涩"],
    }
    missing = []
    for sense, keywords in senses.items():
        if not any(k in text for k in keywords):
            missing.append(sense)
    if missing:
        issues.append(f"[五感] 缺少{', '.join(missing)}描写，建议补充以增强沉浸感")

    # 8. 标点异常
    if "。。" in text or "！！" in text:
        issues.append("[标点] 检测到重复标点(。。/！！)，请检查")

    # 输出
    print(f"=== 审计报告 ===")
    print(f"文件: {filepath}")
    print(f"字数: {char_count} | 行数: {line_count}")
    print()

    if not issues:
        print("✅ 未发现明显问题，质量良好。")
    else:
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print(f"\n共发现 {len(issues)} 个问题。")


def cmd_style(args):
    """根据作家风格给出改写建议"""
    name = None
    filepath = None
    for arg in args:
        if arg.startswith("--name="):
            name = arg.split("=", 1)[1]
        elif arg.startswith("--file="):
            filepath = arg.split("=", 1)[1]

    if not name:
        print("用法: python3 main.py style --name=辰东 [--file=chapter.txt]")
        print("请指定参考作家。")
        return

    # 搜索作家
    author = None
    for a in AUTHOR_DATABASE:
        if name in a["name"]:
            author = a
            break

    if not author:
        print(f"未找到作家: {name}")
        return

    print(f"【{author['name']}】风格参考")
    print(f"分类: {author['category']} / {author['genre']}")
    print(f"核心特点: {author['features']}")
    print(f"适用场景: {author['scenarios']}")
    print()

    if filepath and os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        print(f"已读取文件 ({len(text)}字)，请基于上述风格特点对文本进行改写参考。")
    else:
        print("提示: 加上 --file=chapter.txt 可读取具体章节进行风格对照分析。")


def cmd_help():
    print("""网文写作参考工具

用法:
  python3 main.py list [--category=分类]     列出/筛选作家
  python3 main.py search --name=名字          按名字搜索
  python3 main.py search --keyword=关键词     按关键词搜索
  python3 main.py audit --file=chapter.txt    审计章节
  python3 main.py style --name=作家 [--file=章节]  风格参考

可用分类: 玄幻仙侠, 都市现代, 悬疑科幻, 历史架空, 女频言情, 经典文学
""")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        cmd_help()
    elif args[0] == "list":
        cmd_list(args[1:])
    elif args[0] == "search":
        cmd_search(args[1:])
    elif args[0] == "audit":
        cmd_audit(args[1:])
    elif args[0] == "style":
        cmd_style(args[1:])
    else:
        print(f"未知命令: {args[0]}")
        cmd_help()

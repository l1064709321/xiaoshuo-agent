# 起点白金大神创作技能库

覆盖111位顶尖网文作家的风格定位与核心技法，内置原文语料库、33维审计系统、AI编辑部流水线，支持迭代写作。

## 核心能力

| 能力 | 说明 |
|:---|:---|
| **原文语料库** | 111位作者、800+精选段落，按场景标签索引（战斗/对话/环境/心理/开篇/高潮/幽默/悬疑） |
| **风格拆解** | 词汇指纹、环境逻辑、经典台词、结构蓝图，基因测序级分析 |
| **文风仿写** | 喂一段样本，自动匹配大神+注入原文参考，输出仿写 Prompt |
| **33维审计** | 角色一致性、战力崩坏、伏笔遗忘、AI味检测等36个维度 |
| **迭代写作** | 写完→审→改→再审→再改，最多N轮，直到没有严重问题 |
| **编辑部流水线** | 扫榜→大纲→枪手代笔→毒舌审稿→改稿，全自动化 |

## 快速开始

```bash
# 列出所有作家
python3 main.py list

# 查看某作者的原文语料
python3 main.py corpus --author=[作者名]

# 深度拆解某作家风格（含原文精读）
python3 main.py deconstruct --name=[作者名]

# 枪手代笔（自动注入原文参考）
python3 main.py ghostwrite --outline=大纲.txt --author=[作者名] --chapter=1

# 完整审计
python3 main.py full --file=chapter.txt

# 完整流水线（含迭代）
python3 main.py pipeline --concept="废柴逆袭" --author=[作者名] --rounds=3
```

## 原文语料库

核心升级：不再只存统计摘要，而是存**原文精选段落**。Prompt 直接塞原文做 few-shot，让模型从原文里学句式节奏、信息密度、断句习惯。

### 场景标签

| 标签 | 含义 | 适用场景 |
|:---|:---|:---|
| `battle` | 战斗/打斗 | 写战斗场面时参考 |
| `dialogue` | 对话/嘴炮 | 写对话时参考 |
| `environment` | 环境/场景描写 | 写环境时参考 |
| `psychology` | 心理/内心独白 | 写心理活动时参考 |
| `opening` | 开篇/出场 | 写开篇时参考 |
| `climax` | 高潮/燃点 | 写高潮时参考 |
| `humor` | 幽默/搞笑 | 写轻松段落时参考 |
| `suspense` | 悬疑/惊悚 | 写悬疑氛围时参考 |

### 效果对比

- 旧版：`请用[作者]风格写` → 模板废话，AI味重
- 新版：直接塞3段[作者]原文 → 模型自己"看"出文风

## 33维审计系统

| 类别 | 检查内容 |
|:---|:---|
| 角色一致性 | 性格矛盾、配角工具化、关系进展、智商在线、口头禅统一 |
| 物资与战力 | 法宝遗忘、战力崩坏、物资数量、资源使用、突破代价 |
| 伏笔与逻辑 | 伏笔遗忘、逻辑漏洞、巧合过多、时间线、反派逻辑 |
| 文风与表达 | AI味检测、描写冗长、战斗枯燥、情绪到位、幽默自然 |
| 结构与节奏 | 章节钩子、爽点密度、开篇抓人、高潮燃度、支线挤压 |

### 去AI味速查

| AI味表达 | 替换方向 |
|:---|:---|
| "心中不由得一惊" | 直接写动作："他瞳孔微缩，后退半步" |
| "仿佛失去了灵魂一般" | 用具体动作："他的手指在屏幕上一下一下地滑" |
| "一股暖流涌上心头" | 用行动："他别过脸，没让师父看见自己发红的眼眶" |
| "深吸一口气" | "胸口起伏了一下"或"攥紧了拳头" |
| 每章结尾"人生感悟" | 删掉，用悬念或动作收尾 |

## 迭代写作流程

```
初稿生成（枪手代笔 + 原文语料参考）
    ↓
33维审计 + AI味检测（毒舌编辑）
    ↓
有问题？→ 改稿编辑修改 → 再审 → 再改...
    ↓
最多N轮，直到没有严重问题
    ↓
最终拍板（你确认发布）
```

## CLI 命令速查

```bash
# 基础
python3 main.py list [--category=玄幻仙侠]
python3 main.py search --name=[作者名] | --keyword=克苏鲁
python3 main.py deconstruct --name=[作者名] | --keyword=武侠

# 语料库
python3 main.py corpus [--author=[作者名]] [--scene=battle] [--keyword=血]

# 审计
python3 main.py audit --file=chapter.txt [--outline=outline.txt]
python3 main.py ai --file=chapter.txt
python3 main.py opening --file=chapter.txt
python3 main.py full --file=chapter.txt

# 创作
python3 main.py style --file=chapter.txt [--name=[作者名]]
python3 main.py imitate --file=sample.txt --topic="拍卖会" [--author=[作者名]]
python3 main.py stuck --file=chapter.txt
python3 main.py scout [--category=玄幻仙侠]
python3 main.py outline --concept="废柴逆袭" [--volumes=5]

# 流水线
python3 main.py ghostwrite --outline=大纲.txt [--author=[作者名]] [--chapter=1] [--words=3000]
python3 main.py pipeline --concept="废柴逆袭" [--author=[作者名]] [--rounds=3]
```


## 项目结构

```
Online-writing-skill/
├── skills.py              # 核心代码（5600+行）
├── main.py                # CLI入口
├── SKILL.md               # 技能说明文档
├── README.md              # 本文件
├── corpus/                # 原文语料库
│   ├── loader.py          # 语料库检索引擎
│   └── authors/           # 111位作者的语料文件（JSON）
└── .git/
```

## 许可

![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)
![License: AGPLv3](https://img.shields.io/badge/License-AGPLv3-blue.svg)
![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)
![License: 定制协议](https://img.shields.io/badge/License-定制协议-brightgreen.svg)

### 小说创作技能 - 使用许可协议

**允许**：
- 使用本技能生成小说内容，并自由发表、出版、改编这些生成内容（版权归你所有）。

**禁止**：
- 删除或篡改本技能中的版权声明、作者信息和本协议文本；
- 将本技能用于任何违法违规活动（如生成违禁内容、侵犯他人版权等）。

**免责声明**：
- 本技能按“现状”（AS IS）提供，作者不作任何明示或暗示的保证。
- 因使用本技能生成的小说内容引发的版权纠纷、抄袭争议等，由使用者自行承担，作者概不负责。
- 作者保留对本协议的一切最终解释权。

**修改建议**：
如果你对本技能进行了修改（新增功能、性能优化、修复Bug等），建议（非强制）：
- 将修改内容通过GitHub Issue或邮件通知作者；
- 保留你的修改日志，便于作者参考和合并。

**授权申请**：
如需将本技能用于**小说创作以外的场景**，或进行本协议禁止的其他行为，请联系作者申请授权：
- 邮箱：1064709321@qq.com

**终止**：
若你违反本协议的任何条款，作者授予你的所有权利将立即自动终止。作者保留追究法律责任的权利。

---

**生效日期**：2026年7月7日
**版权所有** © 2026 Lord of the Stars

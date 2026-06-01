import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


# ==========================================
# 1. 完整数据结构化：白金大神作家风格知识库 (全量 60 条记录)
# ==========================================
AUTHOR_DATABASE = [
    # --- 一、玄幻仙侠类 (17条) ---
    {"name": "辰东", "category": "玄幻仙侠", "genre": "玄幻史诗派", "features": "宏大世界观构建、天马行空的想象力、热血磅礴的笔法。在《遮天》中走向成熟，擅长描绘英雄群像的悲欢离合。", "scenarios": "学习构建庞大严谨的玄幻世界、铺垫史诗感"},
    {"name": "天蚕土豆", "category": "玄幻仙侠", "genre": "爽文教科书", "features": "开创并完善"退婚流"与"打脸流"，节奏平稳，练级体系清晰，爽点密度极高。", "scenarios": "学习爽文节奏、逆袭期待感建立"},
    {"name": "我吃西红柿", "category": "玄幻仙侠", "genre": "升级流典范", "features": "升级节奏掌控力极强，行文流畅，爽感连绵不绝。", "scenarios": "学习升级文节奏把控、成长型主角塑造"},
    {"name": "忘语", "category": "玄幻仙侠", "genre": "凡人流开创者", "features": "开创"凡人流"，设定严密的修仙等级世界，塑造谨慎、算计、资源至上的韩立式主角。", "scenarios": "学习凡人流主角塑造、资源匮乏驱动力"},
    {"name": "季越人", "category": "玄幻仙侠", "genre": "家族修仙史诗派", "features": "00后新锐，首作《玄鉴仙族》均订破十万。无主角、无系统、反套路，强调代际传承的史诗感。", "scenarios": "学习家族群像、代际史诗构建"},
    {"name": "滚开", "category": "玄幻仙侠", "genre": "滚开流 / 克系科幻", "features": "超大世界观、超展开、主角杀伐果断。惊悚感和氛围感极强。", "scenarios": "学习高概念设定、超展开叙事"},
    {"name": "黑山老鬼", "category": "玄幻仙侠", "genre": "诡异流", "features": "文笔细腻，描绘秩序崩坏后人性的挣扎与异变。", "scenarios": "学习悬疑惊悚氛围、复杂人性刻画"},
    {"name": "狐尾的笔", "category": "玄幻仙侠", "genre": "点子型作家 / 克苏鲁本土化", "features": "实现克苏鲁东方化，节奏癫狂，专注主线推进。", "scenarios": "学习传统题材创新融合、高信息量叙事"},
    {"name": "轻泉流响", "category": "玄幻仙侠", "genre": "御兽流", "features": "注重"治愈系"日常，强调人与宠兽的情感刻画与期待感塑造。", "scenarios": "学习轻松日常、人宠羁绊"},
    {"name": "最白的乌鸦", "category": "玄幻仙侠", "genre": "法治修仙流", "features": "将法治观念融入修仙，文风轻松幽默，开创"法制修仙"风格。", "scenarios": "学习跨界融合、幽默反套路"},
    {"name": "阎ZK", "category": "玄幻仙侠", "genre": "玄骨侠心", "features": "玄幻为骨、侠心为核，兼具江湖快意与庙堂深度，注重家国情怀。", "scenarios": "学习玄幻中融入家国侠义"},
    {"name": "远瞳", "category": "玄幻仙侠", "genre": "科幻种田流", "features": "科幻元素与轻松日常结合，构建独特世界观。", "scenarios": "学习科幻背景下的种田文写法"},
    {"name": "鹅是老五", "category": "玄幻仙侠", "genre": "凡人流", "features": "底层杀出、金手指、升级快，情感描写细腻。", "scenarios": "学习凡人流成长路径与情感描写"},
    {"name": "爱潜水的乌贼", "category": "玄幻仙侠", "genre": "类型文革新者", "features": "提炼网文类型并熔铸新意，兼具市井细腻与史诗叙事。", "scenarios": "学习类型创新、精密世界观设定"},
    {"name": "老鹰吃小鸡", "category": "玄幻仙侠", "genre": "高武热血", "features": "燃点、笑点、泪点兼具，塑造有烟火气的英雄，长篇驾驭力强。", "scenarios": "学习长篇节奏、多线叙事"},
    {"name": "飞天鱼", "category": "玄幻仙侠", "genre": "玄幻架构", "features": "结构严谨、世界观宏大，细腻展现庞大设定中的细节。", "scenarios": "学习复杂设定展开、长篇架构"},
    {"name": "佛前献花", "category": "玄幻仙侠", "genre": "灵异规则流开创者", "features": "《神秘复苏》开创"鬼不可杀死、只可驾驭、洞察规律"核心设定，战斗强调智谋博弈。", "scenarios": "学习规则系世界观构建、恐怖氛围营造"},

    # --- 二、都市现代类 (8条) ---
    {"name": "会说话的肘子", "category": "都市现代", "genre": "搞笑吐槽流", "features": "轻松搞笑的吐槽文风，巧妙的架构与人物支撑。", "scenarios": "学习搞笑文风、吐槽式对话"},
    {"name": "熊狼狗", "category": "都市现代", "genre": "社会派荒诞流 / 赛博修仙开创者", "features": "黑色幽默与社会批判为核心，代表作《没钱修什么仙？》以"修仙贷"解构内卷与资本异化。", "scenarios": "学习社会议题娱乐化表达、极端世界观构建"},
    {"name": "丛林狼", "category": "都市现代", "genre": "现代军事", "features": "冷静热血笔触描写特种兵生活，密集战斗推动成长，充满家国情怀。", "scenarios": "学习军事题材、战斗场面描写"},
    {"name": "志鸟村", "category": "都市现代", "genre": "硬核技术流 / 行业文", "features": ""网文科学天王"，语言简洁，专注凸显人物高超技能。", "scenarios": "学习行业文写法、硬核知识融入"},
    {"name": "晨星LL", "category": "都市现代", "genre": "科幻穿越 / 现代科幻", "features": "擅长科幻时空穿越，脑洞大开，将极尽真实的细节与宏大世界结合。", "scenarios": "学习科幻与真实细节结合、双视角叙事"},
    {"name": "我会修空调", "category": "都市现代", "genre": "治愈系悬疑", "features": "悬疑中带有温情，紧张中穿插幽默，讲述平凡人成长与救赎。", "scenarios": "学习平衡悬疑、搞笑与温情"},
    {"name": "王梓钧", "category": "都市现代", "genre": "都市重生 / 历史文娱", "features": "文笔朴实精准，节奏紧凑，擅长考据，快速带入特定时代。", "scenarios": "学习都市爽文技巧、历史考据"},
    {"name": "陈词懒调", "category": "都市现代", "genre": "轻松治愈", "features": "起点男频女白金，风格轻松治愈，擅长动物、原始、未来等多元视角。", "scenarios": "学习跨题材创作、轻松文风"},

    # --- 三、悬疑科幻类 (8条) ---
    {"name": "我会修空调", "category": "悬疑科幻", "genre": "治愈系悬疑", "features": "悬疑惊悚与温馨搞笑融合，讲述离奇故事中的平凡人成长。", "scenarios": "学习悬疑氛围构建、张弛节奏"},
    {"name": "纯洁滴小龙", "category": "悬疑科幻", "genre": "暗黑悬疑", "features": "笔锋精准犀利，剖开人性褶皱，善于社会观察。", "scenarios": "学习从真实案件取材、刻画复杂人性"},
    {"name": "黑山老鬼", "category": "悬疑科幻", "genre": "诡异流", "features": "描绘秩序崩坏后人性的挣扎与异变，作品充满诡异感和想象力。", "scenarios": "学习埋设惊悚伏笔、营造诡异氛围"},
    {"name": "滚开", "category": "悬疑科幻", "genre": "克系科幻", "features": "想象力丰富，惊悚感和氛围感拉满，科幻作品投向人性深渊。", "scenarios": "学习科幻背景下的悬疑惊悚营造"},
    {"name": "狐尾的笔", "category": "悬疑科幻", "genre": "克苏鲁本土化", "features": "克苏鲁东方化、本土化，节奏癫狂，设定新奇。", "scenarios": "学习外来题材本土化创新"},
    {"name": "晨星LL", "category": "悬疑科幻", "genre": "废土科幻", "features": "《这游戏也太真实了》带有《辐射》风格，通过"玩家"视角描绘废土史诗。", "scenarios": "学习废土世界构建、双视角叙事"},
    {"name": "志鸟村", "category": "悬疑科幻", "genre": "科幻行业", "features": "科幻设定与历史、经济、生物等专业知识结合。", "scenarios": "学习科幻与硬核知识结合"},
    {"name": "佛前献花", "category": "悬疑科幻", "genre": "灵异规则流", "features": "规则系恐怖流派，厉鬼不可杀死、只可驾驭，强调规律洞察与智谋。", "scenarios": "学习规则系世界观、单元剧融合"},

    # --- 四、历史架空类 (3条) ---
    {"name": "王梓钧", "category": "历史架空", "genre": "历史文娱", "features": "擅长考据，语言朴实精准，节奏紧凑，爽点频发。", "scenarios": "学习历史考据方法、科普与娱乐结合"},
    {"name": "榴弹怕水", "category": "历史架空", "genre": "架空历史", "features": "天马行空又冷静克制，追求历史逻辑，人物极具英雄气。", "scenarios": "学习平衡爽感与厚重感、英雄塑造"},
    {"name": "孑与2", "category": "历史架空", "genre": "历史生活", "features": "文笔朴实，擅长通过小发明和历史故事让历史文不刻板。", "scenarios": "学习生活化细节融入历史背景"},

    # --- 五、女频言情类 (18条) ---
    {"name": "冬天的柳叶", "category": "女频言情", "genre": "古言天后", "features": "擅长古代言情，文笔老练，文风爽利，历史正剧中穿插幽默。", "scenarios": "学习古言整体构架、剧情节奏"},
    {"name": "偏方方", "category": "女频言情", "genre": "古言爽文 / 种田宅斗", "features": "种田宅斗，文风幽默，笔触细腻，人物鲜活立体。", "scenarios": "学习宅斗剧情设计、群像塑造"},
    {"name": "顾南西", "category": "女频言情", "genre": "暖宠治愈", "features": "暖宠、治愈风格，文风温馨细腻，题材多变。", "scenarios": "学习甜宠氛围营造、情感互动"},
    {"name": "西子情", "category": "女频言情", "genre": "古言虐恋", "features": "文笔清新华丽，情感细腻，情节跌宕起伏。", "scenarios": "学习情节起伏牵动读者情感"},
    {"name": "云芨", "category": "女频言情", "genre": "仙侠言情", "features": "恢弘大气，在宏大仙侠世界中描写女性独立自强。", "scenarios": "学习女频仙侠构建、大女主形象"},
    {"name": "MS芙子", "category": "女频言情", "genre": "玄幻言情", "features": "玄幻言情代表人物，文笔细腻，注重心理与家庭元素。", "scenarios": "学习女频玄幻、人物关系刻画"},
    {"name": "萧七爷", "category": "女频言情", "genre": "玄情天后 / 女强逆袭", "features": "玄幻言情，文风大气，女强逆袭爽文，节奏畅快。", "scenarios": "学习女强爽文节奏、逆袭打脸"},
    {"name": "恍若晨曦", "category": "女频言情", "genre": "残酷情爱", "features": ""残酷情爱系"代表，风格大气，悬念迭起，豪门恩怨描写出色。", "scenarios": "学习强情节、强冲突设计"},
    {"name": "意千重", "category": "女频言情", "genre": "古代言情（细腻）", "features": "文风细腻，情感真挚动人，故事性强。", "scenarios": "学习古典言情细腻情感表达"},
    {"name": "吉祥夜", "category": "女频言情", "genre": "现代言情", "features": "现代都市情感题材，文笔流畅，情感真挚。", "scenarios": "学习现代都市情感刻画"},
    {"name": "战七少", "category": "女频言情", "genre": "古代言情", "features": "古代背景，情节设计巧妙，人物形象鲜明。", "scenarios": "学习古代背景下人物与情节构思"},
    {"name": "苏小暖", "category": "女频言情", "genre": "现代言情", "features": "贴近生活，情感真实，引发共鸣。", "scenarios": "学习现代生活情感描写"},
    {"name": "叶非夜", "category": "女频言情", "genre": "现代言情", "features": "文笔细腻，描绘现代都市男女情感世界。", "scenarios": "学习现代情感细腻描绘"},
    {"name": "吱吱", "category": "女频言情", "genre": "古代言情（古典）", "features": "描写古代闺阁生活，文风古典雅致，细节丰富。", "scenarios": "学习古代生活细节与古典文风"},
    {"name": "油爆香菇", "category": "女频言情", "genre": "女强争霸", "features": "文风诙谐幽默，架构严谨考究，擅长女性角色刻画。", "scenarios": "学习幽默文风、女性群像塑造"},
    {"name": "郁雨竹", "category": "女频言情", "genre": "古言种田", "features": "种田文代表，语言诙谐接地气，擅长生活化细节制造笑点与温情。", "scenarios": "学习种田文日常感、生活细节"},
    {"name": "夏染雪", "category": "女频言情", "genre": "克制的深情", "features": "文风清澈又暗流涌动，用平实语言勾勒复杂心绪。", "scenarios": "学习克制笔触表达深情、增强代入感"},
    {"name": "油爆香菇", "category": "女频言情", "genre": "女强争霸", "features": "文风诙谐幽默，架构严谨考究，擅长女性角色刻画。", "scenarios": "学习幽默文风、女性群像塑造"},

    # --- 六、经典文学类 (7条) ---
    {"name": "古龙", "category": "经典文学", "genre": "武侠革新者", "features": "诗化短句、分行留白，融入推理与禅意，塑造真实侠客。", "scenarios": "学习语言精炼、悬疑感营造"},
    {"name": "还珠楼主", "category": "经典文学", "genre": "仙侠鼻祖", "features": "文白夹杂、华丽笔触、天马行空想象力，开创奇幻仙侠世界。", "scenarios": "学习超凡想象力运用、宏大场景描绘"},
    {"name": "梁羽生", "category": "经典文学", "genre": "儒雅名士风", "features": "提出"以侠胜武"，文史底蕴深厚，语言典雅，塑造诗剑并举的名士侠客。", "scenarios": "学习传统文化底蕴融入作品"},
    {"name": "吴承恩", "category": "经典文学", "genre": "神魔浪漫主义", "features": "高度幻想性与理想化，风格诙谐怪诞，塑造贯彻始终的神话英雄。", "scenarios": "学习浪漫主义手法、幻想世界构建"},
    {"name": "施耐庵", "category": "经典文学", "genre": "英雄传奇", "features": "串联式结构统一个体与群体史诗，语言走向白话，群像塑造生动。", "scenarios": "学习群像塑造、多线叙事"},
    {"name": "曹雪芹", "category": "经典文学", "genre": "现实主义巅峰", "features": "写实与诗化融合，打破脸谱化，塑造"真的人物"，取材现实。", "scenarios": "学习人物真实复杂性、生活诗意化处理"},
    {"name": "罗贯中", "category": "经典文学", "genre": "历史演义", "features": ""七分实事，三分虚构"，虚实相生，描绘形象化历史兴亡。", "scenarios": "学习历史题材处理、虚实平衡"},
]


# ==========================================
# 2. 33维审计系统
# ==========================================

class Severity(Enum):
    """问题严重程度"""
    CRITICAL = "🔴 严重"
    WARNING = "🟡 中等"
    INFO = "🟢 轻微"
    HIGHLIGHT = "✅ 亮点"


@dataclass
class AuditIssue:
    """审计问题"""
    dimension_id: int
    dimension_name: str
    category: str
    severity: Severity
    description: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class AuditReport:
    """审计报告"""
    total_issues: int = 0
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    highlight_count: int = 0
    issues: List[AuditIssue] = field(default_factory=list)
    ai_flavor_score: float = 0.0  # AI味评分，越低越好

    def summary(self) -> str:
        return (
            f"审计完成：共发现 {self.total_issues} 个问题 | "
            f"🔴{self.critical_count} 🟡{self.warning_count} 🟢{self.info_count} | "
            f"AI味评分: {self.ai_flavor_score}/10"
        )


class AuditSystem:
    """
    33维审计系统
    对小说文本进行全方位质量检查，覆盖角色一致性、物资战力、伏笔逻辑、
    文风表达、结构节奏、大纲偏离六大类别，共计33个审计维度。
    """

    # 完整的33个审计维度定义
    DIMENSIONS = {
        # --- 角色一致性 (1-7) ---
        1: {"category": "角色一致性", "name": "主角性格一致性", "check": "主角性格是否前后矛盾"},
        2: {"category": "角色一致性", "name": "配角工具化检测", "check": "配角是否沦为工具人"},
        3: {"category": "角色一致性", "name": "人物关系自然度", "check": "人物关系进展是否自然"},
        4: {"category": "角色一致性", "name": "角色智商在线", "check": "角色智商是否在线"},
        5: {"category": "角色一致性", "name": "语气口头禅统一", "check": "人物语气/口头禅是否统一"},
        6: {"category": "角色一致性", "name": "外貌衣着一致性", "check": "外貌/衣着描写是否前后冲突"},
        7: {"category": "角色一致性", "name": "年龄时间线", "check": "年龄/时间线是否错乱"},

        # --- 物资与战力 (8-13) ---
        8: {"category": "物资与战力", "name": "法宝技能遗忘", "check": "主角的法宝/技能是否被遗忘"},
        9: {"category": "物资与战力", "name": "战力体系崩坏", "check": "战力体系是否崩坏"},
        10: {"category": "物资与战力", "name": "物资数量一致性", "check": "物资数量是否前后对不上"},
        11: {"category": "物资与战力", "name": "丹药资源合理性", "check": "丹药/资源的使用是否合理"},
        12: {"category": "物资与战力", "name": "突破代价削弱", "check": "境界突破的代价和难度是否被随意削弱"},
        13: {"category": "物资与战力", "name": "货币体系混乱", "check": "金钱/货币体系是否混乱"},

        # --- 伏笔与逻辑 (14-20) ---
        14: {"category": "伏笔与逻辑", "name": "伏笔遗忘", "check": "埋下的伏笔是否被遗忘"},
        15: {"category": "伏笔与逻辑", "name": "伏笔回收生硬", "check": "伏笔回收是否过于生硬"},
        16: {"category": "伏笔与逻辑", "name": "逻辑漏洞", "check": "剧情是否存在逻辑漏洞"},
        17: {"category": "伏笔与逻辑", "name": "巧合过多", "check": "巧合是否过多"},
        18: {"category": "伏笔与逻辑", "name": "时间线合理性", "check": "时间线是否合理"},
        19: {"category": "伏笔与逻辑", "name": "信息获取合理性", "check": "信息获取是否合理"},
        20: {"category": "伏笔与逻辑", "name": "反派行为逻辑", "check": "反派的行为逻辑是否成立"},

        # --- 文风与表达 (21-27) ---
        21: {"category": "文风与表达", "name": "AI味-机械句式", "check": "是否存在机械重复的句式"},
        22: {"category": "文风与表达", "name": "AI味-过度升华", "check": "是否存在过度总结/升华"},
        23: {"category": "文风与表达", "name": "AI味-对话僵硬", "check": "对话是否像两个AI在互相谦让"},
        24: {"category": "文风与表达", "name": "描写冗长", "check": "描写是否过于冗长"},
        25: {"category": "文风与表达", "name": "战斗描写枯燥", "check": "战斗描写是否枯燥"},
        26: {"category": "文风与表达", "name": "情绪描写不足", "check": "情绪描写是否到位"},
        27: {"category": "文风与表达", "name": "幽默感自然度", "check": "幽默感是否自然"},

        # --- 结构与节奏 (28-32) ---
        28: {"category": "结构与节奏", "name": "章节钩子", "check": "章节结尾是否有钩子"},
        29: {"category": "结构与节奏", "name": "爽点密度", "check": "爽点密度是否足够"},
        30: {"category": "结构与节奏", "name": "开篇抓人", "check": "开篇是否足够抓人"},
        31: {"category": "结构与节奏", "name": "高潮燃度", "check": "高潮部分是否足够燃"},
        32: {"category": "结构与节奏", "name": "支线挤压主线", "check": "支线是否挤压了主线空间"},

        # --- 大纲与偏离 (33-36) ---
        33: {"category": "大纲与偏离", "name": "大纲偏离度", "check": "当前剧情是否偏离了大纲设定"},
        34: {"category": "大纲与偏离", "name": "对话过密", "check": "当前角色对话是否过于密集"},
        35: {"category": "大纲与偏离", "name": "背景描写过多", "check": "当前章节是否过多着笔描写背景"},
        36: {"category": "大纲与偏离", "name": "旁白过多", "check": "当前章节是否过多加入旁白"},
    }

    # AI味典型症状 → 替换建议
    AI_FLAVOR_PATTERNS = {
        "他的心中不由得一惊": "删除"不由得"，直接写动作："他瞳孔微缩，后退半步。"",
        "这一切说来复杂，实则只发生在电光火石之间": "直接删掉，用短句推进节奏。",
        "他知道，自己必须变强": "换成具体的念头："再这样下去，下次死的就不是别人了。"",
        "一股暖流涌上心头": "用行动代替感受："他别过脸，没让师父看见自己发红的眼眶。"",
        "人生感悟式结尾": "删掉，用悬念或动作收尾。",
        "综上所述": "删除，网文不需要学术论文式的总结。",
        "不仅……而且……": "拆成两个短句，避免关联词堆砌。",
        "与此同时": "考虑是否真的需要强调时间同步，大多数情况下可以省略。",
    }

    @classmethod
    def get_all_dimensions(cls) -> Dict:
        """获取全部审计维度定义"""
        return cls.DIMENSIONS

    @classmethod
    def get_dimension_by_id(cls, dim_id: int) -> Optional[Dict]:
        """根据编号获取单个维度"""
        return cls.DIMENSIONS.get(dim_id)

    @classmethod
    def get_dimensions_by_category(cls, category: str) -> List[Dict]:
        """按类别获取维度列表"""
        return [
            {"id": k, **v}
            for k, v in cls.DIMENSIONS.items()
            if v["category"] == category
        ]

    @classmethod
    def audit_text(cls, text: str, title: str = "未命名章节") -> AuditReport:
        """
        对文本执行全维度审计，返回审计报告。
        实际使用时，这里应接入具体的检测逻辑/NLP模型。
        当前提供框架和基础规则检测。
        """
        report = AuditReport()
        issues = []

        # --- 基础规则检测示例 ---

        # 维度21：AI味-机械句式检测
        ai_issues = cls._detect_ai_flavor(text)
        issues.extend(ai_issues)

        # 维度28：章节钩子检测（检查最后一段是否有悬念/疑问/动作中断）
        hook_issue = cls._check_hook(text)
        if hook_issue:
            issues.append(hook_issue)

        # 维度29：爽点密度（粗略估算：检查情绪高点关键词）
        density_issue = cls._check_pleasure_density(text)
        if density_issue:
            issues.append(density_issue)

        # 维度34：对话过密检测
        dialogue_issue = cls._check_dialogue_density(text)
        if dialogue_issue:
            issues.append(dialogue_issue)

        # 汇总
        report.issues = issues
        report.total_issues = len(issues)
        report.critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        report.warning_count = sum(1 for i in issues if i.severity == Severity.WARNING)
        report.info_count = sum(1 for i in issues if i.severity == Severity.INFO)
        report.highlight_count = sum(1 for i in issues if i.severity == Severity.HIGHLIGHT)

        # AI味评分（0-10，越低越好，基于检测到的问题数量）
        ai_issue_count = len(ai_issues)
        report.ai_flavor_score = round(min(ai_issue_count * 2.5, 10), 1)

        return report

    @classmethod
    def _detect_ai_flavor(cls, text: str) -> List[AuditIssue]:
        """检测AI味表达"""
        issues = []
        for pattern, suggestion in cls.AI_FLAVOR_PATTERNS.items():
            if pattern in text and pattern != "人生感悟式结尾" and pattern != "综上所述":
                issues.append(AuditIssue(
                    dimension_id=21,
                    dimension_name="AI味-机械句式",
                    category="文风与表达",
                    severity=Severity.WARNING,
                    description=f"检测到AI味表达："{pattern}"",
                    suggestion=suggestion
                ))

        # 检测章节结尾的人生感悟
        lines = text.strip().split("\n")
        if lines:
            last_para = lines[-1]
            if any(kw in last_para for kw in ["人生", "生命", "终究", "或许这就是", "原来"]):
                if len(last_para) > 20:
                    issues.append(AuditIssue(
                        dimension_id=22,
                        dimension_name="AI味-过度升华",
                        category="文风与表达",
                        severity=Severity.WARNING,
                        description="章节结尾疑似AI式人生感悟",
                        suggestion=cls.AI_FLAVOR_PATTERNS["人生感悟式结尾"]
                    ))

        return issues

    @classmethod
    def _check_hook(cls, text: str) -> Optional[AuditIssue]:
        """检测章节结尾钩子"""
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        if not lines:
            return None

        last_line = lines[-1]
        # 检查是否以动作、对话中断、悬念结尾
        has_hook = any([
            last_line.endswith("……"),
            last_line.endswith("——"),
            "突然" in last_line,
            "忽然" in last_line,
            "?" in last_line,
            "！" in last_line and len(last_line) < 30,
        ])

        if not has_hook:
            return AuditIssue(
                dimension_id=28,
                dimension_name="章节钩子",
                category="结构与节奏",
                severity=Severity.WARNING,
                description="章节结尾缺乏钩子，建议用悬念、动作中断或反转收尾",
                suggestion="在结尾加入突发事件、对话中断、新信息揭示等元素，制造"然后呢？"的阅读冲动"
            )
        return None

    @classmethod
    def _check_pleasure_density(cls, text: str) -> Optional[AuditIssue]:
        """粗略检测爽点密度"""
        pleasure_keywords = ["突破", "碾压", "打脸", "震惊", "不可思议", "逆袭", "反转", "竟然是"]
        count = sum(text.count(kw) for kw in pleasure_keywords)
        # 假设每2000字为1章，低于2个爽点关键词视为密度偏低
        if count < 2:
            return AuditIssue(
                dimension_id=29,
                dimension_name="爽点密度",
                category="结构与节奏",
                severity=Severity.INFO,
                description=f"爽点关键词出现 {count} 次，密度可能偏低",
                suggestion="考虑在章节中增加小高潮：实力突破、打脸对手、获得稀有物品、揭开秘密等"
            )
        return None

    @classmethod
    def _check_dialogue_density(cls, text: str) -> Optional[AuditIssue]:
        """检测对话是否过密"""
        lines = text.split("\n")
        dialogue_lines = [l for l in lines if l.strip().startswith(""") or l.strip().startswith(""")]
        total_lines = len([l for l in lines if l.strip()])
        if total_lines > 0 and len(dialogue_lines) / total_lines > 0.7:
            return AuditIssue(
                dimension_id=34,
                dimension_name="对话过密",
                category="大纲与偏离",
                severity=Severity.INFO,
                description=f"对话占比约 {len(dialogue_lines)/total_lines*100:.0f}%，可能过于密集",
                suggestion="适当穿插动作描写、环境描写或内心独白，打破对话连篇的节奏"
            )
        return None


# ==========================================
# 3. 作家匹配引擎
# ==========================================

class AuthorMatcher:
    """根据用户需求匹配推荐作家"""

    CATEGORY_KEYWORDS = {
        "玄幻仙侠": ["玄幻", "仙侠", "修仙", "修真", "异界", "魔法", "斗气"],
        "都市现代": ["都市", "现代", "重生", "职场", "校花", "兵王", "神医"],
        "悬疑科幻": ["悬疑", "科幻", "恐怖", "诡异", "克苏鲁", "末世", "废土"],
        "历史架空": ["历史", "架空", "穿越古代", "争霸", "科举"],
        "女频言情": ["言情", "古言", "现言", "甜宠", "虐恋", "宅斗", "宫斗", "女强"],
        "经典文学": ["经典", "武侠", "传统"],
    }

    @classmethod
    def match_by_category(cls, user_input: str, top_k: int = 3) -> List[Dict]:
        """根据用户输入匹配推荐作家"""
        scored = []
        for author in AUTHOR_DATABASE:
            score = 0
            # 类别匹配
            category_keywords = cls.CATEGORY_KEYWORDS.get(author["category"], [])
            for kw in category_keywords:
                if kw in user_input:
                    score += 3
            # 流派匹配
            if author["genre"] in user_input:
                score += 2
            # 特征关键词匹配
            feature_words = author["features"].replace("、", " ").replace("，", " ").split()
            for word in feature_words:
                if len(word) >= 2 and word in user_input:
                    score += 1
            if score > 0:
                scored.append((score, author))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [author for _, author in scored[:top_k]]

    @classmethod
    def get_by_category(cls, category: str) -> List[Dict]:
        """按类别获取全部作家"""
        return [a for a in AUTHOR_DATABASE if a["category"] == category]

    @classmethod
    def get_all_categories(cls) -> List[str]:
        """获取所有类别"""
        return list(dict.fromkeys(a["category"] for a in AUTHOR_DATABASE))


# ==========================================
# 4. 使用示例
# ==========================================
if __name__ == "__main__":
    # 示例1：匹配作家
    print("=" * 50)
    print("【作家匹配】")
    matcher = AuthorMatcher()
    results = matcher.match_by_category("我想写一个修仙题材，主角是凡人流，想要克苏鲁元素")
    for i, author in enumerate(results, 1):
        print(f"\n{i}. {author['name']} [{author['category']}] - {author['genre']}")
        print(f"   特点: {author['features']}")
        print(f"   推荐: {author['scenarios']}")

    # 示例2：33维审计
    print("\n" + "=" * 50)
    print("【33维审计】")
    sample_text = """
    李明站在山巅之上，感受着体内汹涌的灵力。他知道，自己终于突破了。
    这半年来的苦修没有白费，从筑基到金丹，他付出了常人难以想象的努力。
    他的心中不由得一惊，因为远处的天空中突然出现了一道裂缝。
    裂缝中走出一位白衣老者，老者看着李明，微微一笑。
    "年轻人，你很不错。"老者说道。
    "多谢前辈夸奖。"李明恭敬地回答。
    "不过，这只是开始。"老者意味深长地说。
    人生就像一场修行，永远不会知道下一秒会发生什么。
    """

    report = AuditSystem.audit_text(sample_text, "示例章节")
    print(f"\n{report.summary()}\n")
    for issue in report.issues:
        print(f"  {issue.severity.value} | 维度{issue.dimension_id} {issue.dimension_name}")
        print(f"         {issue.description}")
        if issue.suggestion:
            print(f"         💡 {issue.suggestion}")
        print()

    # 示例3：查看全部审计维度
    print("=" * 50)
    print("【33维审计维度清单】")
    for dim_id, dim_info in AuditSystem.get_all_dimensions().items():
        print(f"  维度{dim_id:2d} | {dim_info['category']} | {dim_info['name']} | {dim_info['check']}")
import json
from typing import List, Dict
# ==========================================
# 1. 完整数据结构化：白金大神作家风格知识库 (全量 60 条记录)
# ==========================================
AUTHOR_DATABASE = [
    # --- 一、玄幻仙侠类 ---
    {"name": "辰东", "category": "玄幻仙侠", "genre": "玄幻史诗派", "features": "宏大世界观构建、天马行空的想象力、热血磅礴的笔法。在《遮天》中走向成熟，擅长描绘英雄群像的悲欢离合。", "scenarios": "学习构建庞大严谨的玄幻世界、铺垫史诗感"},
    {"name": "天蚕土豆", "category": "玄幻仙侠", "genre": "爽文教科书", "features": "开创并完善“退婚流”与“打脸流”，节奏平稳，练级体系清晰，爽点密度极高。", "scenarios": "学习爽文节奏、逆袭期待感建立"},
    {"name": "我吃西红柿", "category": "玄幻仙侠", "genre": "升级流典范", "features": "升级节奏掌控力极强，行文流畅，爽感连绵不绝。", "scenarios": "学习升级文节奏把控、成长型主角塑造"},
    {"name": "忘语", "category": "玄幻仙侠", "genre": "凡人流开创者", "features": "开创“凡人流”，设定严密的修仙等级世界，塑造谨慎、算计、资源至上的韩立式主角。", "scenarios": "学习凡人流主角塑造、资源匮乏驱动力"},
    {"name": "季越人", "category": "玄幻仙侠", "genre": "家族修仙史诗派", "features": "00后新锐，首作《玄鉴仙族》均订破十万。无主角、无系统、反套路，强调代际传承的史诗感。", "scenarios": "学习家族群像、代际史诗构建"},
    {"name": "滚开", "category": "玄幻仙侠", "genre": "滚开流 / 克系科幻", "features": "超大世界观、超展开、主角杀伐果断。惊悚感和氛围感极强。", "scenarios": "学习高概念设定、超展开叙事"},
    {"name": "黑山老鬼", "category": "玄幻仙侠", "genre": "诡异流", "features": "文笔细腻，描绘秩序崩坏后人性的挣扎与异变。", "scenarios": "学习悬疑惊悚氛围、复杂人性刻画"},
    {"name": "狐尾的笔", "category": "玄幻仙侠", "genre": "点子型作家 / 克苏鲁本土化", "features": "实现克苏鲁东方化，节奏癫狂，专注主线推进。", "scenarios": "学习传统题材创新融合、高信息量叙事"},
    {"name": "轻泉流响", "category": "玄幻仙侠", "genre": "御兽流", "features": "注重“治愈系”日常，强调人与宠兽的情感刻画与期待感塑造。", "scenarios": "学习轻松日常、人宠羁绊"},
    {"name": "最白的乌鸦", "category": "玄幻仙侠", "genre": "法治修仙流", "features": "将法治观念融入修仙，文风轻松幽默，开创“法制修仙”风格。", "scenarios": "学习跨界融合、幽默反套路"},
    {"name": "阎 ZK", "category": "玄幻仙侠", "genre": "玄骨侠心", "features": "玄幻为骨、侠心为核，兼具江湖快意与庙堂深度，注重家国情怀。", "scenarios": "学习玄幻中融入家国侠义"},
    {"name": "远瞳", "category": "玄幻仙侠", "genre": "科幻种田流", "features": "科幻元素与轻松日常结合，构建独特世界观。", "scenarios": "学习科幻背景下的种田文写法"},
    {"name": "鹅是老五", "category": "玄幻仙侠", "genre": "凡人流", "features": "底层杀出、金手指、升级快，情感描写细腻。", "scenarios": "学习凡人流成长路径与情感描写"},
    {"name": "爱潜水的乌贼", "category": "玄幻仙侠", "genre": "类型文革新者", "features": "提炼网文类型并熔铸新意，兼具市井细腻与史诗叙事。", "scenarios": "学习类型创新、精密世界观设定"},
    {"name": "老鹰吃小鸡", "category": "玄幻仙侠", "genre": "高武热血", "features": "燃点、笑点、泪点兼具，塑造有烟火气的英雄，长篇驾驭力强。", "scenarios": "学习长篇节奏、多线叙事"},
    {"name": "飞天鱼", "category": "玄幻仙侠", "genre": "玄幻架构", "features": "结构严谨、世界观宏大，细腻展现庞大设定中的细节。", "scenarios": "学习复杂设定展开、长篇架构"},
    {"name": "佛前献花", "category": "玄幻仙侠", "genre": "灵异规则流开创者", "features": "《神秘复苏》开创“鬼不可杀死、只可驾驭、洞察规律”核心设定，战斗强调智谋博弈。", "scenarios": "学习规则系世界观构建、恐怖氛围营造"},

    # --- 二、都市现代类 ---
    {"name": "会说话的肘子", "category": "都市现代", "genre": "搞笑吐槽流", "features": "轻松搞笑的吐槽文风，巧妙的架构与人物支撑。", "scenarios": "学习搞笑文风、吐槽式对话"},
    {"name": "熊狼狗", "category": "都市现代", "genre": "社会派荒诞流 / 赛博修仙开创者", "features": "黑色幽默与社会批判为核心，代表作《没钱修什么仙？》以“修仙贷”解构内卷与资本异化。", "scenarios": "学习社会议题娱乐化表达、极端世界观构建"},
    {"name": "丛林狼", "category": "都市现代", "genre": "现代军事", "features": "冷静热血笔触描写特种兵生活，密集战斗推动成长，充满家国情怀。", "scenarios": "学习军事题材、战斗场面描写"},
    {"name": "志鸟村", "category": "都市现代", "genre": "硬核技术流 / 行业文", "features": "“网文科学天王”，语言简洁，专注凸显人物高超技能。", "scenarios": "学习行业文写法、硬核知识融入"},
    {"name": "晨星 LL", "category": "都市现代", "genre": "科幻穿越 / 现代科幻", "features": "擅长科幻时空穿越，脑洞大开，将极尽真实的细节与宏大世界结合。", "scenarios": "学习科幻与真实细节结合、双视角叙事"},
    {"name": "我会修空调", "category": "都市现代", "genre": "治愈系悬疑", "features": "悬疑中带有温情，紧张中穿插幽默，讲述平凡人成长与救赎。", "scenarios": "学习平衡悬疑、搞笑与温情"},
    {"name": "王梓钧", "category": "都市现代", "genre": "都市重生 / 历史文娱", "features": "文笔朴实精准，节奏紧凑，擅长考据，快速带入特定时代。", "scenarios": "学习都市爽文技巧、历史考据"},
    {"name": "陈词懒调", "category": "都市现代", "genre": "轻松治愈", "features": "起点男频女白金，风格轻松治愈，擅长动物、原始、未来等多元视角。", "scenarios": "学习跨题材创作、轻松文风"},

    # --- 三、悬疑科幻类 ---
    {"name": "我会修空调", "category": "悬疑科幻", "genre": "治愈系悬疑", "features": "悬疑惊悚与温馨搞笑融合，讲述离奇故事中的平凡人成长。", "scenarios": "学习悬疑氛围构建、张弛节奏"},
    {"name": "纯洁滴小龙", "category": "悬疑科幻", "genre": "暗黑悬疑", "features": "笔锋精准犀利，剖开人性褶皱，善于社会观察。", "scenarios": "学习从真实案件取材、刻画复杂人性"},
    {"name": "黑山老鬼", "category": "悬疑科幻", "genre": "诡异流", "features": "描绘秩序崩坏后人性的挣扎与异变，作品充满诡异感和想象力。", "scenarios": "学习埋设惊悚伏笔、营造诡异氛围"},
    {"name": "滚开", "category": "悬疑科幻", "genre": "克系科幻", "features": "想象力丰富，惊悚感和氛围感拉满，科幻作品投向人性深渊。", "scenarios": "学习科幻背景下的悬疑惊悚营造"},
    {"name": "狐尾的笔", "category": "悬疑科幻", "genre": "克苏鲁本土化", "features": "克苏鲁东方化、本土化，节奏癫狂，设定新奇。", "scenarios": "学习外来题材本土化创新"},
    {"name": "晨星 LL", "category": "悬疑科幻", "genre": "废土科幻", "features": "《这游戏也太真实了》带有《辐射》风格，通过“玩家”视角描绘废土史诗。", "scenarios": "学习废土世界构建、双视角叙事"},
    {"name": "志鸟村", "category": "悬疑科幻", "genre": "科幻行业", "features": "科幻设定与历史、经济、生物等专业知识结合。", "scenarios": "学习科幻与硬核知识结合"},
    {"name": "佛前献花", "category": "悬疑科幻", "genre": "灵异规则流", "features": "规则系恐怖流派，厉鬼不可杀死、只可驾驭，强调规律洞察与智谋。", "scenarios": "学习规则系世界观、单元剧融合"},

    # --- 四、历史架空类 ---
    {"name": "王梓钧", "category": "历史架空", "genre": "历史文娱", "features": "擅长考据，语言朴实精准，节奏紧凑，爽点频发。", "scenarios": "学习历史考据方法、科普与娱乐结合"},
    {"name": "榴弹怕水", "category": "历史架空", "genre": "架空历史", "features": "天马行空又冷静克制，追求历史逻辑，人物极具英雄气。", "scenarios": "学习平衡爽感与厚重感、英雄塑造"},
    {"name": "孑与 2", "category": "历史架空", "genre": "历史生活", "features": "文笔朴实，擅长通过小发明和历史故事让历史文不刻板。", "scenarios": "学习生活化细节融入历史背景"},

    # --- 五、女频言情类 ---
    {"name": "冬天的柳叶", "category": "女频言情", "genre": "古言天后", "features": "擅长古代言情，文笔老练，文风爽利，历史正剧中穿插幽默。", "scenarios": "学习古言整体构架、剧情节奏"},
    {"name": "偏方方", "category": "女频言情", "genre": "古言爽文", "features": "种田宅斗，文风幽默，笔触细腻，人物鲜活立体。", "scenarios": "学习宅斗剧情设计、群像塑造"},
    {"name": "顾南西", "category": "女频言情", "genre": "暖宠治愈", "features": "暖宠、治愈风格，文风温馨细腻，题材多变。", "scenarios": "学习甜宠氛围营造、情感互动"},
    {"name": "西子情", "category": "女频言情", "genre": "古言虐恋", "features": "文笔清新华丽，情感细腻，情节跌宕起伏。", "scenarios": "学习情节起伏牵动读者情感"},
    {"name": "云芨", "category": "女频言情", "genre": "仙侠言情", "features": "恢弘大气，在宏大仙侠世界中描写女性独立自强。", "scenarios": "学习女频仙侠构建、大女主形象"},
    {"name": "MS 芙子", "category": "女频言情", "genre": "玄幻言情", "features": "玄幻言情代表人物，文笔细腻，注重心理与家庭元素。", "scenarios": "学习女频玄幻、人物关系刻画"},
    {"name": "萧七爷", "category": "女频言情", "genre": "玄情天后", "features": "玄幻言情，文风大气，女强逆袭爽文，节奏畅快。", "scenarios": "学习女强爽文节奏、逆袭打脸"},
    {"name": "恍若晨曦", "category": "女频言情", "genre": "残酷情爱", "features": "“残酷情爱系”代表，风格大气，悬念迭起，豪门恩怨描写出色。", "scenarios": "学习强情节、强冲突设计"},
    {"name": "意千重", "category": "女频言情", "genre": "古代言情", "features": "文风细腻，情感真挚动人，故事性强。", "scenarios": "学习古典言情细腻情感表达"},
    {"name": "吉祥夜", "category": "女频言情", "genre": "现代言情", "features": "现代都市情感题材，文笔流畅，情感真挚。", "scenarios": "学习现代都市情感刻画"},
    {"name": "战七少", "category": "女频言情", "genre": "古代言情", "features": "古代背景，情节设计巧妙，人物形象鲜明。", "scenarios": "学习古代背景下人物与情节构思"},
    {"name": "苏小暖", "category": "女频言情", "genre": "现代言情", "features": "贴近生活，情感真实，引发共鸣。", "scenarios": "学习现代生活情感描写"},
    {"name": "叶非夜", "category": "女频言情", "genre": "现代言情", "features": "文笔细腻，描绘现代都市男女情感世界。", "scenarios": "学习现代情感细腻描绘"},
    {"name": "吱吱", "category": "女频言情", "genre": "古代言情", "features": "描写古代闺阁生活，文风古典雅致，细节丰富。", "scenarios": "学习古代生活细节与古典文风"},
    {"name": "油爆香菇", "category": "女频言情", "genre": "女强争霸", "features": "文风诙谐幽默，架构严谨考究，擅长女性角色刻画。", "scenarios": "学习幽默文风、女性群像塑造"},
    {"name": "郁雨竹", "category": "女频言情", "genre": "古言种田", "features": "种田文代表，语言诙谐接地气，擅长生活化细节制造笑点与温情。", "scenarios": "学习种田文日常感、生活细节"},
    {"name": "夏染雪", "category": "女频言情", "genre": "克制的深情", "features": "文风清澈又暗流涌动，用平实语言勾勒复杂心绪。", "scenarios": "学习克制笔触表达深情、增强代入感"},

    # --- 六、经典文学类 ---
    {"name": "古龙", "category": "经典文学", "genre": "武侠革新者", "features": "诗化短句、分行留白，融入推理与禅意，塑造真实侠客。", "scenarios": "学习语言精炼、悬疑感营造"},
    {"name": "还珠楼主", "category": "经典文学", "genre": "仙侠鼻祖", "features": "文白夹杂、华丽笔触、天马行空想象力，开创奇幻仙侠世界。", "scenarios": "学习超凡想象力运用、宏大场景描绘"},
    {"name": "梁羽生", "category": "经典文学", "genre": "儒雅名士风", "features": "提出“以侠胜武”，文史底蕴深厚，语言典雅，塑造诗剑并举的名士侠客。", "scenarios": "学习传统文化底蕴融入作品"},
    {"name": "吴承恩", "category": "经典文学", "genre": "神魔浪漫主义", "features": "高度幻想性与理想化，风格诙谐怪诞，塑造贯彻始终的神话英雄。", "scenarios": "学习浪漫主义手法、幻想世界构建"},
    {"name": "施耐庵", "category": "经典文学", "genre": "英雄传奇", "features": "串联式结构统一个体与群体史诗，语言走向白话，群像塑造生动。", "scenarios": "学习群像塑造、多线叙事"},
    {"name": "曹雪芹", "category": "经典文学", "genre": "现实主义巅峰", "features": "写实与诗化融合，打破脸谱化，塑造“真的人物”，取材现实。", "scenarios": "学习人物真实复杂性、生活诗意化处理"},
    {"name": "罗贯中", "category": "经典文学", "genre": "历史演义", "features": "“七分实事，三分虚构”，虚实相生，描绘形象化历史兴亡。", "scenarios": "学习历史题材处理、虚实平衡"},
]


# ==========================================
# 2. 意图识别模块 (同前)
# ==========================================
class IntentParser:
    """基于词典与同义词扩展的轻量级意图识别器"""
    def __init__(self):
        self.category_dict = {
            "玄幻仙侠": ["玄幻", "仙侠", "修仙", "修真", "奇幻", "东方", "高武", "凡人", "御兽"],
            "都市现代": ["都市", "现代", "重生", "文娱", "职场", "行业", "赛博", "现实"],
            "悬疑科幻": ["悬疑", "科幻", "克苏鲁", "诡异", "惊悚", "废土", "规则", "神秘", "恐怖"],
            "历史架空": ["历史", "架空", "朝代", "考据", "庙堂", "争霸", "种田"],
            "女频言情": ["女频", "言情", "古言", "现言", "甜宠", "宅斗", "虐恋", "大女主", "女强"],
            "经典文学": ["经典", "武侠", "名著", "文学", "传统"],
        }
        self.element_dict = {
            "金手指": ["金手指", "外挂", "系统", "老爷爷", "开挂", "超能力"],
            "开篇": ["开篇", "开头", "黄金三章", "切入", "开局"],
            "人设": ["人设", "主角", "反派", "配角", "群像", "人物塑造", "性格"],
            "爽点": ["爽点", "打脸", "逆袭", "装逼", "期待感", "爽文", "燃点"],
            "氛围": ["氛围", "惊悚", "恐怖", "诡异", "压迫感", "环境"],
            "节奏": ["节奏", "拖沓", "紧凑", "高潮", "升级流", "推进"],
            "世界观": ["世界观", "设定", "架构", "体系", "背景", "地图"],
            "情感": ["情感", "感情戏", "恋爱", "cp", "互动", "甜宠", "虐心"],
        }

    def parse(self, user_input: str) -> Dict:
        parsed = {"category": None, "elements": [], "raw_input": user_input}
        for cat, keywords in self.category_dict.items():
            if any(kw in user_input for kw in keywords):
                parsed["category"] = cat
                break
        for elem, keywords in self.element_dict.items():
            if any(kw in user_input for kw in keywords):
                parsed["elements"].append(elem)
        return parsed


# ==========================================
# 3. 作家匹配模块 (同前)
# ==========================================
class AuthorMatcher:
    def __init__(self, database: List[Dict]):
        self.db = database

    def match(self, intent: Dict, top_k: int = 3) -> List[Dict]:
        scored_authors = []
        for author in self.db:
            score = 0
            if intent["category"] and author["category"] == intent["category"]:
                score += 50
            search_text = author["scenarios"] + author["features"]
            for element in intent["elements"]:
                if element in search_text:
                    score += 20
            for word in intent["raw_input"]:
                if len(word) > 1 and word in author["genre"]:
                    score += 10
            if score > 0:
                scored_authors.append({"author": author, "score": score})
                
        scored_authors.sort(key=lambda x: x["score"], reverse=True)
        seen, result = set(), []
        for item in scored_authors:
            if item["author"]["name"] not in seen:
                seen.add(item["author"]["name"])
                result.append(item["author"])
            if len(result) >= top_k:
                break
        return result


# ==========================================
# 4. 提示词生成模块 (同前)
# ==========================================
class PromptGenerator:
    @staticmethod
    def generate(intent: Dict, matched_authors: List[Dict]) -> str:
        if not matched_authors:
            return f"用户问题：{intent['raw_input']}\n\n未找到匹配的作家风格，请直接给出通用建议。"
            
        prompt_sections = []
        for idx, author in enumerate(matched_authors, 1):
            section = f"""
#### 参考作家 {idx}：{author['name']} ({author['genre']})
- **核心创作特点**：{author['features']}
- **针对当前需求的建议方向**：{author['scenarios']}
"""
            prompt_sections.append(section.strip())
        
        authors_intro = "\n\n".join(prompt_sections)
        
        final_prompt = f"""
# 角色设定
你是一位精通网文与类型文学创作的宗师级导师，你特别擅长汲取顶尖白金大神的流派精髓，并将其转化为具体的实操指导。

# 用户当前需求
{intent['raw_input']}

# 为你匹配的作家风格库（请严格基于以下作家的核心特点给出实操建议，不可偏离其流派精髓）
{authors_intro}

# 输出要求
请基于上述匹配的作家风格，按以下结构输出你的指导建议：
1. **痛点分析**：一针见血地指出用户当前需求在网文创作中的核心难点。
2. **风格借鉴方法论**：分别说明如何运用上述作家的特点来解决痛点，给出具体、可落地的操作步骤（例如：如何设计系统、如何铺垫氛围）。
3. **实操范例**：结合用户的需求，写一段 150-250 字的示范文本，并在文末用【】批注体现的作家风格技巧。
"""
        return final_prompt


# ==========================================
# 5. 统一调度 Skill 门面类
# ==========================================
class PlatinumAuthorSkill:
    def __init__(self):
        self.parser = IntentParser()
        self.matcher = AuthorMatcher(AUTHOR_DATABASE)
        self.generator = PromptGenerator()

    def execute(self, user_input: str, return_prompt_only: bool = True) -> str:
        intent = self.parser.parse(user_input)
        matched_authors = self.matcher.match(intent, top_k=3)
        final_prompt = self.generator.generate(intent, matched_authors)
        
        if return_prompt_only:
            return final_prompt
        else:
            return json.dumps({
                "intent": intent,
                "matched_authors": [a["name"] for a in matched_authors],
                "final_prompt": final_prompt
            }, ensure_ascii=False, indent=2)


# ==========================================
# 运行测试
# ==========================================
if __name__ == "__main__":
    skill = PlatinumAuthorSkill()
    
    print("="*60 + "\n测试用例 1：规则系悬疑\n" + "="*60)
    test_1 = "我想写一本悬疑小说，需要设计一个基于规则的金手指，怎么营造恐怖氛围？"
    print(skill.execute(test_1))
    
    print("\n" + "="*60 + "\n测试用例 2：女频宅斗群像\n" + "="*60)
    test_2 = "女频古言怎么写宅斗群像？人物容易脸谱化怎么办？"
    print(skill.execute(test_2))

    print("\n" + "="*60 + "\n测试用例 3：调试模式（查看中间匹配过程）\n" + "="*60)
    test_3 = "历史架空小说怎么写出生活感？"
    print(skill.execute(test_3, return_prompt_only=False))

# FastAPI server code removed - use main.py CLI instead

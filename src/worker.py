# -*- coding: utf-8 -*-
"""
AI Learning - Cloudflare Worker
提供 REST API 接口，支持句子分析、例句生成、练习题生成
"""

import json
import re
from js import URL, Response, fetch, Headers, Date, Math

# Cloudflare Workers 环境下从环境变量获取 API Key
API_KEY = None

# ============ DashScope 配置 ============
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_API_KEY = "sk-9e6be88fab044f719313ce6bba59b759"
# 多模型互备列表（按优先级排序，依次尝试）
DASHSCOPE_MODELS = [
    "qwen-max",
    "qwen-plus",
    "deepseek-r1-0528",
]

# ============ 提示词定义 ============

STRUCTURE_ANALYSIS_PROMPT = """你是一个专业的语言学分析助手，精通英语和汉语的句子结构分析。
任务：分析用户输入的句子，提取其语法结构，并以JSON格式返回。
支持语言：英语 (en) 和 汉语 (zh)
分析维度：句子类型、句子成分、语法结构、时态/语态、关键词汇、结构模式、翻译
返回JSON格式必须包含：language, original, translation, sentence_type, structure_type, components, tense_aspect, key_phrases, structure_pattern, difficulty
其中 components 是数组，每项包含 role（成分角色名称）和 text（对应原文文本片段），例如：
[{"role": "主语", "text": "I"}, {"role": "谓语", "text": "love"}, {"role": "宾语", "text": "learning new languages"}]
重要：只返回JSON，不要包含任何思考过程、分析说明或Markdown标记。不要使用代码块包裹，直接输出纯JSON。"""

EXAMPLE_GENERATION_PROMPT = """你是一个语言学习助手，根据给定的句子结构生成同类例句。
任务：基于提供的句子结构，生成多个同类结构的例句。
要求：
1. 每条例句必须是不同主题、不同场景的内容（如：教育、旅行、科技、生活、工作、文化、健康、环境等），严禁全部围绕同一个主题。
2. 根据难度级别控制例句的复杂度——"一般"使用简单词汇和基础语法，"偏难"使用稍复杂词汇和复合句，"极难"使用高级词汇和复杂句式。
3. **每次生成必须创造全新的例句内容**，不要重复之前生成过的任何例句。
4. 内容实用、贴近生活。
返回JSON格式：{"structure_pattern": "...", "examples": [{"sentence": "...", "translation": "...", "components": [{"role": "主语", "text": "..."}], "difficulty": "intermediate"}], "learning_tips": "..."}
重要：只返回JSON，不要包含任何思考过程、分析说明或Markdown标记。不要使用代码块包裹，直接输出纯JSON。"""

EXERCISE_GENERATION_PROMPT = """你是一个语言教学专家，根据给定的句子结构生成选择题练习。
任务：设计选择题练习题，帮助学习者巩固掌握。
要求：
1. 每道题必须围绕不同的主题场景（如：教育、旅行、科技、生活、工作、文化、健康、环境等），严禁全部围绕同一个主题。
2. 所有题目都是选择题，每题4个选项，只有1个正确答案。
3. 根据难度级别控制题目复杂度——"一般"使用简单词汇和基础语法，"偏难"使用稍复杂词汇和复合句，"极难"使用高级词汇和复杂句式。
4. **每次生成必须创造全新的题目**，不要重复之前生成过的任何练习题。
返回JSON格式：{"exercises": [{"type": "choice", "question": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."}, "answer": "A", "explanation": "..."}]}
重要：只返回JSON，不要包含任何思考过程、分析说明或Markdown标记。不要使用代码块包裹，直接输出纯JSON。"""

# ============ 句型库 ============

COMMON_PATTERNS = {
    "en": [
        # ========== 初中 (beginner) - 15 个 ==========
        {"id": "en_001", "name": "主谓宾结构", "pattern": "[Subject] + [Verb] + [Object]", "example": "I love English.", "level": "beginner"},
        {"id": "en_002", "name": "There be 句型", "pattern": "There is/are + [Noun] + [地点]", "example": "There is a book on the desk.", "level": "beginner"},
        {"id": "en_003", "name": "Be动词句型", "pattern": "[Subject] + am/is/are + [表语]", "example": "She is a student.", "level": "beginner"},
        {"id": "en_004", "name": "情态动词 can", "pattern": "[Subject] + can/cannot + [Verb原形]", "example": "I can swim very well.", "level": "beginner"},
        {"id": "en_005", "name": "现在进行时", "pattern": "[Subject] + am/is/are + [Verb-ing]", "example": "She is reading a book.", "level": "beginner"},
        {"id": "en_006", "name": "一般过去时", "pattern": "[Subject] + [Verb-ed/过去式] + [Object]", "example": "I visited Beijing last year.", "level": "beginner"},
        {"id": "en_007", "name": "一般将来时 (will)", "pattern": "[Subject] + will + [Verb原形]", "example": "I will go to the park tomorrow.", "level": "beginner"},
        {"id": "en_008", "name": "一般将来时 (going to)", "pattern": "[Subject] + am/is/are going to + [Verb原形]", "example": "She is going to buy a new phone.", "level": "beginner"},
        {"id": "en_009", "name": "一般现在时三单", "pattern": "[He/She/It] + [Verb-s/es] + [Object]", "example": "He reads English every morning.", "level": "beginner"},
        {"id": "en_010", "name": "like/love/enjoy doing", "pattern": "[Subject] + like/love/enjoy + [Verb-ing]", "example": "I like playing basketball.", "level": "beginner"},
        {"id": "en_011", "name": "want/need to do", "pattern": "[Subject] + want/need + to + [Verb原形]", "example": "I want to be a teacher.", "level": "beginner"},
        {"id": "en_012", "name": "情态动词 must/have to", "pattern": "[Subject] + must/have to + [Verb原形]", "example": "You must finish your homework.", "level": "beginner"},
        {"id": "en_013", "name": "祈使句", "pattern": "(Don't) + [Verb原形] + [Object]", "example": "Open the door, please.", "level": "beginner"},
        {"id": "en_014", "name": "There be 句型的时态变化", "pattern": "There was/were/will be + [Noun] + [地点]", "example": "There was a tree in the garden.", "level": "beginner"},
        {"id": "en_015", "name": "形容词比较级", "pattern": "[A] + am/is/are + [adj-er/more adj] + than + [B]", "example": "Tom is taller than Jerry.", "level": "beginner"},
        {"id": "en_016", "name": "形容词最高级", "pattern": "[Subject] + am/is/are + the + [adj-est/most adj]", "example": "She is the best student in our class.", "level": "beginner"},
        {"id": "en_017", "name": "频率副词", "pattern": "[Subject] + always/usually/often/sometimes + [Verb]", "example": "I always get up at six.", "level": "beginner"},
        {"id": "en_018", "name": "How many/much 疑问句", "pattern": "How many/much + [Noun] + do/does + [Subject] + [Verb]?", "example": "How many books do you have?", "level": "beginner"},
        # ========== 高中 (intermediate) - 20 个 ==========
        {"id": "en_019", "name": "现在完成时", "pattern": "[Subject] + have/has + [Past Participle]", "example": "I have already finished my homework.", "level": "intermediate"},
        {"id": "en_020", "name": "过去完成时", "pattern": "[Subject] + had + [Past Participle] + [before/by the time + 从句]", "example": "I had finished my work before he came.", "level": "intermediate"},
        {"id": "en_021", "name": "被动语态", "pattern": "[Subject] + am/is/are/was/were + [Past Participle]", "example": "English is spoken all over the world.", "level": "intermediate"},
        {"id": "en_022", "name": "定语从句 - 关系代词", "pattern": "[先行词] + who/whom/which/that + [从句]", "example": "The girl who is singing is my sister.", "level": "intermediate"},
        {"id": "en_023", "name": "定语从句 - 关系副词", "pattern": "[先行词] + where/when/why + [从句]", "example": "This is the school where I studied.", "level": "intermediate"},
        {"id": "en_024", "name": "非限制性定语从句", "pattern": "[主句], + which/who + [从句]", "example": "He passed the exam, which made us happy.", "level": "intermediate"},
        {"id": "en_025", "name": "宾语从句", "pattern": "[Subject] + [Verb] + that/if/whether + [从句]", "example": "I think that he is right.", "level": "intermediate"},
        {"id": "en_026", "name": "主语从句 (It作形式主语)", "pattern": "It is + [adj/noun] + that + [从句]", "example": "It is important that you study hard.", "level": "intermediate"},
        {"id": "en_027", "name": "表语从句", "pattern": "[Subject] + am/is/are + that/whether + [从句]", "example": "The problem is that we don't have enough time.", "level": "intermediate"},
        {"id": "en_028", "name": "so...that 结果状语从句", "pattern": "so + [adj/adv] + that + [从句]", "example": "The box is so heavy that I can't lift it.", "level": "intermediate"},
        {"id": "en_029", "name": "such...that 结果状语从句", "pattern": "such + (a/an) + [adj] + [Noun] + that + [从句]", "example": "She is such a kind girl that everyone likes her.", "level": "intermediate"},
        {"id": "en_030", "name": "not only...but also", "pattern": "not only + [A] + but also + [B]", "example": "She can not only sing but also dance.", "level": "intermediate"},
        {"id": "en_031", "name": "either...or / neither...nor", "pattern": "either/neither + [A] + or/nor + [B]", "example": "Either you or he is wrong.", "level": "intermediate"},
        {"id": "en_032", "name": "过去进行时", "pattern": "[Subject] + was/were + [Verb-ing] + [when/while + 从句]", "example": "I was watching TV when he called.", "level": "intermediate"},
        {"id": "en_033", "name": "现在完成进行时", "pattern": "[Subject] + have/has been + [Verb-ing]", "example": "I have been waiting for an hour.", "level": "intermediate"},
        {"id": "en_034", "name": "不定式作目的状语", "pattern": "[Subject] + [Verb] + to + [Verb原形]", "example": "I came here to learn English.", "level": "intermediate"},
        {"id": "en_035", "name": "分词作状语", "pattern": "[V-ing/V-ed] + [主句]", "example": "Walking in the park, I met an old friend.", "level": "intermediate"},
        {"id": "en_036", "name": "强调句 It is/was...that", "pattern": "It is/was + [被强调部分] + that + [句子其余部分]", "example": "It was yesterday that I met him.", "level": "intermediate"},
        {"id": "en_037", "name": "the more...the more", "pattern": "The + [比较级] + [从句], the + [比较级] + [主句]", "example": "The more you read, the more you learn.", "level": "intermediate"},
        {"id": "en_038", "name": "as...as 同级比较", "pattern": "[Subject] + am/is/are + as + [adj] + as + [B]", "example": "She is as tall as her mother.", "level": "intermediate"},
        # ========== 大学 (advanced) - 20 个 ==========
        {"id": "en_039", "name": "虚拟语气 - 与现在相反", "pattern": "If + [Subject] + [过去式], [Subject] + would/could + [Verb原形]", "example": "If I were you, I would accept the offer.", "level": "advanced"},
        {"id": "en_040", "name": "虚拟语气 - 与过去相反", "pattern": "If + [Subject] + had + [Past Participle], [Subject] + would have + [Past Participle]", "example": "If I had studied harder, I would have passed.", "level": "advanced"},
        {"id": "en_041", "name": "虚拟语气 - 与将来相反", "pattern": "If + [Subject] + were to/should + [Verb原形], [Subject] + would + [Verb原形]", "example": "If it should rain, we would stay home.", "level": "advanced"},
        {"id": "en_042", "name": "wish 虚拟语气", "pattern": "[Subject] + wish + [Subject] + [过去式/过去完成式]", "example": "I wish I could fly like a bird.", "level": "advanced"},
        {"id": "en_043", "name": "倒装句 - 否定词开头", "pattern": "[否定词] + [助动词] + [Subject] + [Verb原形]", "example": "Never have I seen such a beautiful view.", "level": "advanced"},
        {"id": "en_044", "name": "倒装句 - Only+状语", "pattern": "Only + [状语] + [助动词] + [Subject] + [Verb]", "example": "Only by working hard can you succeed.", "level": "advanced"},
        {"id": "en_045", "name": "So+adj 倒装", "pattern": "So + [adj/adv] + [助动词] + [Subject] + [Verb] + that...", "example": "So tired was he that he fell asleep at once.", "level": "advanced"},
        {"id": "en_046", "name": "as 引导让步状语从句", "pattern": "[adj/adv/n] + as + [Subject] + [Verb], [主句]", "example": "Young as he is, he knows a lot.", "level": "advanced"},
        {"id": "en_047", "name": "同位语从句", "pattern": "[抽象名词] + that + [从句]", "example": "The fact that he won surprised everyone.", "level": "advanced"},
        {"id": "en_048", "name": "what 引导名词性从句", "pattern": "What + [从句] + am/is/are + [表语]", "example": "What matters most is your attitude.", "level": "advanced"},
        {"id": "en_049", "name": "whatever/whoever 引导从句", "pattern": "Whatever/Whoever/Whichever + [从句], [主句]", "example": "Whatever you do, do it with passion.", "level": "advanced"},
        {"id": "en_050", "name": "独立主格结构", "pattern": "[Noun/Pronoun] + [V-ing/V-ed/adj], [主句]", "example": "The exam finished, we went home.", "level": "advanced"},
        {"id": "en_051", "name": "With 独立主格", "pattern": "With + [Noun] + [V-ing/V-ed/adj], [主句]", "example": "With the teacher standing there, we kept silent.", "level": "advanced"},
        {"id": "en_052", "name": "定语从句 - 介词+which/whom", "pattern": "[Noun] + [介词] + which/whom + [从句]", "example": "This is the book about which I told you.", "level": "advanced"},
        {"id": "en_053", "name": "Suggest/Insist/Order 虚拟语气", "pattern": "[Subject] + suggest/insist/order + that + [Subject] + (should) + [Verb原形]", "example": "I suggest that he (should) see a doctor.", "level": "advanced"},
        {"id": "en_054", "name": "动名词复合结构", "pattern": "[Possessive] + [V-ing] + [Verb]", "example": "His coming late made the teacher angry.", "level": "advanced"},
        {"id": "en_055", "name": "形式主语 It + is + adj + (for/of sb) + to do", "pattern": "It is + [adj] + for/of + [sb] + to + [Verb原形]", "example": "It is important for you to learn English.", "level": "advanced"},
        {"id": "en_056", "name": "定语从句 - as 引导非限定", "pattern": "As is known/As we know, [主句]", "example": "As is known to all, the earth goes around the sun.", "level": "advanced"},
        {"id": "en_057", "name": "There be 复杂变化 (there remain/exist/lie)", "pattern": "There remain/exist/lie/stand + [Noun] + [地点]", "example": "There exist many problems to solve.", "level": "advanced"},
        {"id": "en_058", "name": "倍数表达法", "pattern": "[A] + am/is/are + [数] times + as/more + [adj] + as/than + [B]", "example": "This room is three times as large as that one.", "level": "advanced"},
    ],
    "zh": [
        {"id": "zh_001", "name": "主谓宾句", "pattern": "[主语] + [谓语] + [宾语]", "example": "我喜欢学习。", "level": "beginner"},
        {"id": "zh_002", "name": "主系表句", "pattern": "[主语] + 是/为/乃 + [表语]", "example": "她是老师。", "level": "beginner"},
        {"id": "zh_003", "name": "存现句", "pattern": "[处所] + 有 + [名词]", "example": "桌子上有一本书。", "level": "beginner"},
        {"id": "zh_004", "name": "把字句", "pattern": "[主语] + 把 + [宾语] + [动词]", "example": "我把作业写完了。", "level": "intermediate"},
        {"id": "zh_005", "name": "被字句", "pattern": "[宾语] + 被 + [主语] + [动词]", "example": "作业被我写完了。", "level": "intermediate"},
        {"id": "zh_006", "name": "比较句", "pattern": "[A] + 比 + [B] + [形容词]", "example": "他比我高。", "level": "intermediate"},
        {"id": "zh_007", "name": "是...的强调", "pattern": "[主语] + 是 + [时间/地点] + [动词] + 的", "example": "我是昨天到北京的。", "level": "advanced"},
        {"id": "zh_008", "name": "因果复句", "pattern": "[原因]，所以/因此 + [结果]", "example": "因为下雨，所以我没出门。", "level": "advanced"},
    ]
}

# ============ 核心函数 ============

def _extract_json(text: str) -> dict:
    """从 AI 回复中提取 JSON（支持预处理去除 <think> 块等）"""
    # 预处理：剥离 <think> 思考块
    cleaned = re.sub(r'<think>[\s\S]*?</think>', '', text).strip()
    if cleaned:
        text = cleaned

    try:
        return json.loads(text.strip())
    except Exception:
        pass
    match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass
    match = re.search(r'\{[\s\S]+\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return {"error": f"无法解析响应: {text[:200]}"}


async def _call_bailian(prompt: str, system_prompt: str, api_key: str, model: str = None, temperature: float = 0.7) -> dict:
    """调用 AI API，支持多模型互备切换（依次尝试，失败自动切换到下一个）
    temperature 控制随机性：0.7 平衡模式，0.85 鼓励多样性"""
    models = [model] if model else DASHSCOPE_MODELS
    key = api_key or DASHSCOPE_API_KEY

    if not key:
        return {"error": "API_KEY 未配置，请在 Cloudflare Workers Dashboard 中设置环境变量 API_KEY"}

    errors = []
    for i, m in enumerate(models):
        url = f"{DASHSCOPE_BASE_URL}/chat/completions"
        payload = json.dumps({
            "model": m,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature
        })

        try:
            # Pyodide JS bridge: list of pairs → JS Array<[string, string]> → fetch accepts it
            resp = await fetch(
                url,
                method="POST",
                headers=[["Authorization", "Bearer " + key], ["Content-Type", "application/json"]],
                body=payload
            )

            if resp.status == 200:
                data = (await resp.json()).to_py()
                content = data["choices"][0]["message"]["content"]
                return _extract_json(content)
            else:
                error_text = await resp.text()
                err_msg = f"[{m}] HTTP {resp.status}: {error_text[:200]}"
                errors.append(err_msg)
        except Exception as e:
            err_msg = f"[{m}] 请求异常: {str(e)[:200]}"
            errors.append(err_msg)

        if i < len(models) - 1:
            # 尝试下一个模型
            continue

    return {"error": f"所有模型均失败 ({len(models)}个尝试): {' | '.join(errors)}"}


def get_pattern_by_id(pattern_id: str) -> dict:
    """根据 ID 获取句型"""
    for lang_patterns in COMMON_PATTERNS.values():
        for pattern in lang_patterns:
            if pattern["id"] == pattern_id:
                return pattern
    return None


def get_common_patterns(language: str = None, level: str = None) -> list:
    """获取句型库"""
    patterns = []
    if language is None or language == "en":
        patterns.extend(COMMON_PATTERNS.get("en", []))
    if language is None or language == "zh":
        patterns.extend(COMMON_PATTERNS.get("zh", []))
    if level:
        patterns = [p for p in patterns if p.get("level") == level]
    return patterns


async def analyze_sentence_handler(sentence: str, language: str, api_key: str) -> dict:
    """分析句子结构"""
    if language is None:
        language = "zh" if any('\u4e00' <= c <= '\u9fff' for c in sentence) else "en"
    seed = int(Date.now()) % 100000
    prompt = f"语言: {language}\n句子: {sentence}\n随机种子: {seed}"
    return await _call_bailian(prompt, STRUCTURE_ANALYSIS_PROMPT, api_key, temperature=0.8)


async def generate_examples_handler(pattern: str, language: str, count: int, difficulty: str, api_key: str) -> dict:
    """生成例句（每次随机种子确保内容不同）"""
    seed = int(Date.now()) % 100000
    rand = int(Math.random() * 100000)
    topic_pool = ["教育", "旅行", "科技", "日常生活", "工作职场", "文化", "健康", "环境", "娱乐", "社交"]
    topic = topic_pool[rand % len(topic_pool)]
    prompt = f"语言: {language}\n句型模板: {pattern}\n生成例句数量: {count}\n随机种子: {seed}-{rand}\n建议主题范围: {topic}"
    if difficulty:
        prompt += f"\n难度级别: {difficulty}"
    return await _call_bailian(prompt, EXAMPLE_GENERATION_PROMPT, api_key, temperature=0.9)


async def generate_exercises_handler(pattern: str, language: str, count: int, difficulty: str, api_key: str) -> dict:
    """生成练习题（每次随机种子确保内容不同）"""
    seed = int(Date.now()) % 100000
    rand = int(Math.random() * 100000)
    topic_pool = ["教育", "旅行", "科技", "日常生活", "工作职场", "文化", "健康", "环境", "娱乐", "社交"]
    topic = topic_pool[rand % len(topic_pool)]
    prompt = f"语言: {language}\n句型模板: {pattern}\n生成练习题数量: {count}\n随机种子: {seed}-{rand}\n建议主题范围: {topic}"
    if difficulty:
        prompt += f"\n难度要求: {difficulty}"
    return await _call_bailian(prompt, EXERCISE_GENERATION_PROMPT, api_key, temperature=0.9)


# ============ Cloudflare Worker 入口 ============

def make_response(data, status=200, cors_headers=None):
    """构造响应"""
    if cors_headers is None:
        cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    body = json.dumps(data, ensure_ascii=False)
    response_headers = Headers.new()
    response_headers.set("Content-Type", "application/json")
    for key, value in cors_headers.items():
        response_headers.set(key, value)
    return Response.new(body, status=status, headers=response_headers)


# ── 知识库 KV 工具函数 ──────────────────────────────────────────
KNOWLEDGE_PREFIX = "kb:"
KNOWLEDGE_INDEX_KEY = "kb:index"  # JSON 数组，记录所有条目 key 和元信息


async def _kb_get_all(env):
    """获取知识库所有条目"""
    if not hasattr(env, "KNOWLEDGE_BASE") or not env.KNOWLEDGE_BASE:
        return []
    index_json = await env.KNOWLEDGE_BASE.get(KNOWLEDGE_INDEX_KEY)
    if not index_json:
        return []
    try:
        return json.loads(index_json)
    except Exception:
        return []


async def _kb_save(env, entry: dict) -> bool:
    """保存条目到知识库，返回是否成功"""
    if not hasattr(env, "KNOWLEDGE_BASE") or not env.KNOWLEDGE_BASE:
        return False

    # 生成唯一 ID
    entry_id = str(Date.now()) + "-" + str(int(Date.now()) % 10000)
    entry["id"] = entry_id
    entry["saved_at"] = Date.now()

    # 写入条目
    key = KNOWLEDGE_PREFIX + entry_id
    await env.KNOWLEDGE_BASE.put(key, json.dumps(entry, ensure_ascii=False))

    # 更新索引
    index = await _kb_get_all(env)
    index.append({
        "id": entry_id,
        "type": entry.get("type", "unknown"),
        "title": entry.get("title", ""),
        "structure_pattern": entry.get("structure_pattern", ""),
        "saved_at": entry["saved_at"],
    })
    await env.KNOWLEDGE_BASE.put(KNOWLEDGE_INDEX_KEY, json.dumps(index, ensure_ascii=False))
    return True


async def _kb_delete(env, entry_id: str) -> bool:
    """从知识库删除一个条目"""
    if not hasattr(env, "KNOWLEDGE_BASE") or not env.KNOWLEDGE_BASE:
        return False

    # 删除条目数据
    key = KNOWLEDGE_PREFIX + entry_id
    await env.KNOWLEDGE_BASE.delete(key)

    # 更新索引
    index = await _kb_get_all(env)
    index = [item for item in index if item.get("id") != entry_id]
    await env.KNOWLEDGE_BASE.put(KNOWLEDGE_INDEX_KEY, json.dumps(index, ensure_ascii=False))
    return True


async def _kb_get_detail(env, entry_id: str):
    """获取知识库某个条目的详情"""
    if not hasattr(env, "KNOWLEDGE_BASE") or not env.KNOWLEDGE_BASE:
        return None
    key = KNOWLEDGE_PREFIX + entry_id
    data = await env.KNOWLEDGE_BASE.get(key)
    if not data:
        return None
    try:
        return json.loads(data)
    except Exception:
        return None


async def on_fetch(request, env):
    """Cloudflare Worker 主入口"""
    global API_KEY
    API_KEY = env.API_KEY if hasattr(env, 'API_KEY') else DASHSCOPE_API_KEY

    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

    # 处理 CORS preflight
    if request.method == "OPTIONS":
        options_headers = Headers.new()
        for key, value in cors_headers.items():
            options_headers.set(key, value)
        return Response.new(None, status=204, headers=options_headers)

    try:
        url = URL.new(request.url)
        path_parts = url.pathname.split("/")[1:]

        method = request.method
        content_type = request.headers.get("content-type", "")

        body = None
        if method == "POST" and "application/json" in content_type:
            try:
                body = json.loads(await request.text())
            except Exception:
                pass

        # API 路由
        if len(path_parts) >= 1 and path_parts[0] == "api":
            if len(path_parts) == 2:
                endpoint = path_parts[1]

                if endpoint == "analyze" and method == "POST":
                    sentence = body.get("sentence", "") if body else ""
                    language = body.get("language") if body else None
                    if not sentence:
                        return make_response({"error": "sentence 参数必填"}, 400, cors_headers)
                    result = await analyze_sentence_handler(sentence, language, API_KEY)
                    return make_response(result, 200, cors_headers)

                elif endpoint == "examples" and method == "POST":
                    pattern = body.get("pattern", "") if body else ""
                    language = body.get("language", "en") if body else "en"
                    count = body.get("count", 5) if body else 5
                    difficulty = body.get("difficulty") if body else None
                    if not pattern:
                        return make_response({"error": "pattern 参数必填"}, 400, cors_headers)
                    pattern_info = get_pattern_by_id(pattern)
                    if pattern_info:
                        pattern = pattern_info["pattern"]
                        language = pattern_info["id"][:2]
                    result = await generate_examples_handler(pattern, language, count, difficulty, API_KEY)
                    return make_response(result, 200, cors_headers)

                elif endpoint == "exercises" and method == "POST":
                    pattern = body.get("pattern", "") if body else ""
                    language = body.get("language", "en") if body else "en"
                    count = body.get("count", 5) if body else 5
                    difficulty = body.get("difficulty") if body else None
                    if not pattern:
                        return make_response({"error": "pattern 参数必填"}, 400, cors_headers)
                    pattern_info = get_pattern_by_id(pattern)
                    if pattern_info:
                        pattern = pattern_info["pattern"]
                        language = pattern_info["id"][:2]
                    result = await generate_exercises_handler(pattern, language, count, difficulty, API_KEY)
                    return make_response(result, 200, cors_headers)

                elif endpoint == "patterns" and method == "GET":
                    language = url.searchParams.get("language") if url.searchParams else None
                    level = url.searchParams.get("level") if url.searchParams else None
                    patterns = get_common_patterns(language, level)
                    return make_response({"patterns": patterns}, 200, cors_headers)

                # ── 知识库 API ──
                elif endpoint == "knowledge" and method == "GET":
                    entries = await _kb_get_all(env)
                    return make_response({"entries": entries}, 200, cors_headers)

                elif endpoint == "knowledge" and method == "POST":
                    entry = body if body else {}
                    if not entry.get("type") or not entry.get("content"):
                        return make_response({"error": "type 和 content 必填"}, 400, cors_headers)
                    ok = await _kb_save(env, entry)
                    if ok:
                        return make_response({"success": True, "entry": entry}, 200, cors_headers)
                    return make_response({"error": "知识库未配置（KNOWLEDGE_BASE 绑定）"}, 500, cors_headers)

                elif endpoint == "knowledge" and method == "DELETE":
                    entry_id = body.get("id") if body else None
                    if not entry_id:
                        return make_response({"error": "id 必填"}, 400, cors_headers)
                    ok = await _kb_delete(env, entry_id)
                    if ok:
                        return make_response({"success": True}, 200, cors_headers)
                    return make_response({"error": "未找到或删除失败"}, 404, cors_headers)

                elif endpoint == "knowledge" and method == "PATCH":
                    entry_id = url.searchParams.get("id") if url.searchParams else None
                    if not entry_id:
                        return make_response({"error": "id 参数必填"}, 400, cors_headers)
                    detail = await _kb_get_detail(env, entry_id)
                    if detail is None:
                        return make_response({"error": "未找到"}, 404, cors_headers)
                    return make_response(detail, 200, cors_headers)

                else:
                    return make_response({"error": f"未知端点: {endpoint}"}, 404, cors_headers)

            elif len(path_parts) == 1 and path_parts[0] == "api":
                return make_response({
                    "name": "AI Learning API",
                    "version": "1.0.0",
                    "endpoints": ["/api/analyze", "/api/examples", "/api/exercises", "/api/patterns", "/api/knowledge"]
                }, 200, cors_headers)

            else:
                return make_response({"error": "API 路由未找到"}, 404, cors_headers)

        # 返回 HTML 页面
        html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Learning - 智能句子结构学习</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; }
        .container { max-width: 900px; margin: 0 auto; padding: 20px; }
        header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
        header h1 { font-size: 2em; margin-bottom: 10px; }
        header p { opacity: 0.9; }
        .card { background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .tab { padding: 10px 20px; border: none; background: #e0e0e0; border-radius: 5px; cursor: pointer; font-size: 14px; transition: all 0.3s; }
        .tab.active { background: #667eea; color: white; }
        .tab:hover:not(.active) { background: #d0d0d0; }
        .input-group { margin-bottom: 15px; }
        .input-group label { display: block; margin-bottom: 5px; font-weight: 600; color: #555; }
        .input-group input, .input-group select, .input-group textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }
        .input-group textarea { min-height: 80px; resize: vertical; }
        .btn { padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.3s; }
        .btn-primary { background: #667eea; color: white; }
        .btn-primary:hover { background: #5568d3; }
        .btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .result { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px; border-left: 4px solid #667eea; line-height: 1.6; max-height: 500px; overflow-y: auto; }
        .result.error { border-left-color: #dc3545; background: #fff5f5; }
        .result.raw-json { white-space: pre-wrap; font-family: monospace; }
        .loading { text-align: center; padding: 20px; color: #666; }
        .error-line { color: #dc3545; padding: 10px; }
        .pattern-header { background: linear-gradient(135deg, #667eea15, #764ba215); padding: 12px 15px; border-radius: 8px; margin-bottom: 15px; font-size: 15px; color: #555; }
        .pattern-header code { background: #667eea20; padding: 3px 8px; border-radius: 4px; color: #667eea; font-weight: 600; }
        .examples-list { display: flex; flex-direction: column; gap: 12px; }
        .example-card { background: white; border: 1px solid #e8e8e8; border-radius: 8px; padding: 15px; position: relative; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
        .example-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .example-num { position: absolute; top: -8px; left: -8px; background: #667eea; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; }
        .example-card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; position: relative; }
        .btn-save-single { background: none; border: 1px solid #d6e4ff; border-radius: 4px; padding: 2px 6px; font-size: 13px; cursor: pointer; opacity: 0.5; transition: all 0.15s ease; line-height: 1.4; }
        .btn-save-single:hover { opacity: 1; background: #e3f2fd; border-color: #667eea; transform: translateY(-1px); }
        .example-sentence { font-size: 16px; font-weight: 600; color: #333; margin-bottom: 4px; }
        .example-translation { font-size: 14px; color: #888; margin-bottom: 8px; }
        .example-components { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }
        .component-tag { display: inline-block; background: #f0f4ff; border: 1px solid #d6e4ff; border-radius: 4px; padding: 3px 8px; font-size: 12px; color: #555; transition: all 0.15s ease; }
        .component-tag:hover { transform: translateY(-1px); box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
        .comp-role { color: #667eea; font-weight: 600; }
        /* 成分标签按角色着色（与句子着色色系一致） */
        .comp-tag-subject { background: #e3f2fd; border-color: #90caf9; } .comp-tag-subject .comp-role { color: #1565c0; }
        .comp-tag-predicate { background: #e8f5e9; border-color: #a5d6a7; } .comp-tag-predicate .comp-role { color: #2e7d32; }
        .comp-tag-predicative { background: #e8f5e9; border-color: #a5d6a7; } .comp-tag-predicative .comp-role { color: #2e7d32; }
        .comp-tag-object { background: #fff3e0; border-color: #ffcc80; } .comp-tag-object .comp-role { color: #e65100; }
        .comp-tag-attributive { background: #f3e5f5; border-color: #ce93d8; } .comp-tag-attributive .comp-role { color: #6a1b9a; }
        .comp-tag-adverbial { background: #e0f2f1; border-color: #80cbc4; } .comp-tag-adverbial .comp-role { color: #00695c; }
        .comp-tag-complement { background: #fce4ec; border-color: #ef9a9a; } .comp-tag-complement .comp-role { color: #c62828; }
        .comp-tag-verb { background: #e8f5e9; border-color: #81c784; } .comp-tag-verb .comp-role { color: #1b5e20; }
        .comp-tag-noun { background: #e3f2fd; border-color: #64b5f6; } .comp-tag-noun .comp-role { color: #0d47a1; }
        .comp-tag-default { background: #f5f5f5; border-color: #ccc; } .comp-tag-default .comp-role { color: #666; }
        .difficulty-badge { display: inline-block; margin-top: 8px; padding: 2px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
        .difficulty-badge.beginner { background: #e8f5e9; color: #2e7d32; }
        .difficulty-badge.intermediate { background: #fff3e0; color: #e65100; }
        .difficulty-badge.advanced { background: #fce4ec; color: #c62828; }
        .learning-tips { margin-top: 15px; padding: 12px 15px; background: #fff8e1; border-radius: 8px; font-size: 13px; color: #795548; border-left: 3px solid #ffc107; }
        .analysis-header { font-size: 16px; font-weight: 600; color: #333; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid #e8e8e8; }
        .analysis-row { font-size: 14px; color: #555; margin-bottom: 5px; }
        .analysis-section { font-size: 14px; font-weight: 600; color: #555; margin-bottom: 5px; }
        .exercises-list { display: flex; flex-direction: column; gap: 15px; }
        .exercise-card { background: white; border: 1px solid #e8e8e8; border-radius: 8px; padding: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
        .exercise-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .exercise-num { font-size: 13px; color: #667eea; font-weight: 600; margin-bottom: 8px; }
        .exercise-question { font-size: 15px; font-weight: 500; color: #333; margin-bottom: 10px; padding: 10px; background: #f8f9ff; border-radius: 5px; }
        .exercise-options { display: flex; flex-direction: column; gap: 5px; margin-bottom: 10px; }
        .option-row { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border: 1px solid #e8e8e8; border-radius: 5px; font-size: 14px; }
        .option-row.option-correct { background: #e8f5e9; border-color: #a5d6a7; }
        .option-letter { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; background: #667eea; color: white; border-radius: 50%; font-size: 12px; font-weight: 700; flex-shrink: 0; }
        .option-text { flex: 1; color: #444; }
        .option-check { margin-left: auto; }
        .exercise-explanation { font-size: 13px; color: #666; padding: 8px 12px; background: #f5f5ff; border-radius: 5px; margin-bottom: 6px; }
        .exercise-answer { font-size: 13px; color: #2e7d32; }
        /* 句子着色标注 */
        .hl-sentence { font-size: 16px; font-weight: 600; color: #333; line-height: 2; padding: 8px 0; }
        .hl-comp { border-radius: 4px; padding: 2px 5px; cursor: help; border-bottom: 2px solid transparent; position: relative; }
        .hl-comp:hover::after { content: attr(data-role); position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%); background: #333; color: #fff; font-size: 11px; padding: 2px 6px; border-radius: 3px; white-space: nowrap; pointer-events: none; z-index: 10; }
        .hl-subject { background: #e3f2fd; color: #1565c0; border-bottom-color: #1565c0; }      /* 主语 - 蓝 */
        .hl-predicate { background: #e8f5e9; color: #2e7d32; border-bottom-color: #2e7d32; }    /* 谓语 - 绿 */
        .hl-predicative { background: #e8f5e9; color: #2e7d32; border-bottom-color: #2e7d32; }  /* 表语 - 绿 */
        .hl-object { background: #fff3e0; color: #e65100; border-bottom-color: #e65100; }       /* 宾语 - 橙 */
        .hl-attributive { background: #f3e5f5; color: #6a1b9a; border-bottom-color: #6a1b9a; }  /* 定语 - 紫 */
        .hl-adverbial { background: #e0f2f1; color: #00695c; border-bottom-color: #00695c; }    /* 状语 - 青 */
        .hl-complement { background: #fce4ec; color: #c62828; border-bottom-color: #c62828; }   /* 补语 - 红 */
        .hl-verb { background: #e8f5e9; color: #1b5e20; border-bottom-color: #1b5e20; }         /* 动词 - 深绿 */
        .hl-noun { background: #e3f2fd; color: #0d47a1; border-bottom-color: #0d47a1; }         /* 名词 - 深蓝 */
        .hl-default { background: #f5f5f5; color: #666; border-bottom-color: #999; }            /* 其他 - 灰 */
        /* 着色例句中保留角色标签行 */
        .role-label-row { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px; }
        .role-dot { display: inline-flex; align-items: center; gap: 3px; font-size: 11px; padding: 1px 6px; border-radius: 3px; }

        .pattern-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px; margin-top: 15px; }
        .pattern-item { padding: 10px; background: #f0f0f0; border-radius: 5px; font-size: 13px; }
        .pattern-item .name { font-weight: 600; color: #333; }
        .pattern-item .meta { font-size: 11px; color: #666; margin-top: 3px; }
        .level-tag { display: inline-block; padding: 1px 8px; border-radius: 8px; font-size: 10px; font-weight: 600; }
        .level-beginner { background: #e8f5e9; color: #2e7d32; }
        .level-intermediate { background: #e3f2fd; color: #1565c0; }
        .level-advanced { background: #f3e5f5; color: #7b1fa2; }
        footer { text-align: center; padding: 20px; color: #888; font-size: 12px; }
        .difficulty-options { display: flex; gap: 10px; flex-wrap: wrap; }
        .diff-option { display: inline-flex; align-items: center; gap: 4px; padding: 4px 12px; background: #f0f0f0; border-radius: 16px; cursor: pointer; font-size: 13px; transition: all 0.2s; user-select: none; }
        .diff-option:has(input:checked) { background: #667eea; color: white; }
        .diff-option input { display: none; }
        @media (max-width: 600px) { .container { padding: 10px; } header h1 { font-size: 1.5em; } .tabs { gap: 5px; } .tab { padding: 8px 12px; font-size: 12px; } }
        /* 知识库详情弹窗 */
        .modal-overlay { display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:1000; align-items:center; justify-content:center; padding:20px; }
        .modal-box { background:white; border-radius:12px; max-width:700px; width:100%; max-height:80vh; overflow-y:auto; box-shadow:0 20px 60px rgba(0,0,0,0.3); }
        .modal-header { position:sticky; top:0; background:white; padding:18px 20px; border-bottom:1px solid #eee; border-radius:12px 12px 0 0; display:flex; align-items:center; justify-content:space-between; }
        .modal-header h3 { font-size:16px; }
        .modal-close { background:none; border:none; font-size:20px; cursor:pointer; color:#888; padding:0 5px; }
        .modal-body { padding:20px; }
    </style>
<body>
    <div class="container">
        <header>
            <h1>🤖 AI Learning</h1>
            <p>智能句子结构分析与学习系统 · 支持英语、汉语</p>
        </header>

        <div class="tabs">
            <button class="tab active" data-tab="analyze">📖 句子分析</button>
            <button class="tab" data-tab="examples">✨ 例句生成</button>
            <button class="tab" data-tab="exercises">🎯 练习题</button>
            <button class="tab" data-tab="patterns">📚 句型库</button>
            <button class="tab" data-tab="knowledge">📦 知识库</button>
        </div>

        <div id="tab-analyze" class="tab-content">
            <div class="card">
                <div class="input-group">
                    <label>输入句子</label>
                    <textarea id="analyze-input" placeholder="请输入要分析的英语或汉语句子...">I love learning new languages.</textarea>
                </div>
                <button class="btn btn-primary" id="analyze-btn">🔍 分析句子</button>
                <div id="analyze-result" class="result" style="display:none;"></div>
            </div>
        </div>

        <div id="tab-examples" class="tab-content" style="display:none;">
            <div class="card">
                <div class="input-group">
                    <label>选择句型</label>
                    <select id="example-pattern"><option value="">-- 选择句型 --</option></select>
                </div>
                <div class="input-group">
                    <label>目标语言</label>
                    <select id="example-lang"><option value="en">English</option><option value="zh">中文</option></select>
                </div>
                <div class="input-group">
                    <label>生成数量</label>
                    <input type="number" id="example-count" value="5" min="3" max="10">
                </div>
                <div class="input-group">
                    <label>难度级别</label>
                    <div class="difficulty-options">
                        <label class="diff-option"><input type="radio" name="example-difficulty" value="一般" checked> 一般</label>
                        <label class="diff-option"><input type="radio" name="example-difficulty" value="偏难"> 偏难</label>
                        <label class="diff-option"><input type="radio" name="example-difficulty" value="极难"> 极难</label>
                    </div>
                </div>
                <button class="btn btn-primary" id="examples-btn">✨ 生成例句</button>
                <div id="examples-result" class="result" style="display:none;"></div>
            </div>
        </div>

        <div id="tab-exercises" class="tab-content" style="display:none;">
            <div class="card">
                <div class="input-group">
                    <label>选择句型</label>
                    <select id="exercise-pattern"><option value="">-- 选择句型 --</option></select>
                </div>
                <div class="input-group">
                    <label>目标语言</label>
                    <select id="exercise-lang"><option value="en">English</option><option value="zh">中文</option></select>
                </div>
                <div class="input-group">
                    <label>生成数量</label>
                    <input type="number" id="exercise-count" value="5" min="3" max="10">
                </div>
                <div class="input-group">
                    <label>难度级别</label>
                    <div class="difficulty-options">
                        <label class="diff-option"><input type="radio" name="exercise-difficulty" value="一般" checked> 一般</label>
                        <label class="diff-option"><input type="radio" name="exercise-difficulty" value="偏难"> 偏难</label>
                        <label class="diff-option"><input type="radio" name="exercise-difficulty" value="极难"> 极难</label>
                    </div>
                </div>
                <button class="btn btn-primary" id="exercises-btn">🎯 生成练习题</button>
                <div id="exercises-result" class="result" style="display:none;"></div>
            </div>
        </div>

        <div id="tab-patterns" class="tab-content" style="display:none;">
            <div class="card">
                <div style="display:flex;gap:10px;flex-wrap:wrap;">
                    <div class="input-group" style="flex:1;min-width:140px;">
                        <label>语言</label>
                        <select id="pattern-lang"><option value="">全部</option><option value="en">English</option><option value="zh">中文</option></select>
                    </div>
                    <div class="input-group" style="flex:1;min-width:140px;">
                        <label>难度</label>
                        <select id="pattern-level"><option value="">全部</option><option value="beginner">初中</option><option value="intermediate">高中</option><option value="advanced">大学</option></select>
                    </div>
                </div>
                <button class="btn btn-primary" id="patterns-btn">📚 加载句型库</button>
                <div id="patterns-result" class="pattern-grid"></div>
            </div>
        </div>

        <div id="tab-knowledge" class="tab-content" style="display:none;">
            <div class="card">
                <div class="input-group">
                    <label>知识库</label>
                    <p style="color:#888;font-size:13px;">保存的例句和练习题会出现在这里，方便回顾复习。</p>
                </div>
                <button class="btn btn-primary" id="knowledge-btn">📦 刷新知识库</button>
                <div id="knowledge-result" style="margin-top:15px;"></div>
            </div>
        </div>

        <div id="knowledge-detail-modal" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:1000;display:none;align-items:center;justify-content:center;">
            <div style="background:white;border-radius:12px;padding:25px;max-width:600px;width:90%;max-height:80vh;overflow-y:auto;box-shadow:0 5px 30px rgba(0,0,0,0.3);">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
                    <h3 id="detail-title" style="margin:0;">详情</h3>
                    <button id="detail-close-btn" style="background:none;border:none;font-size:20px;cursor:pointer;color:#888;">✕</button>
                </div>
                <div id="detail-body" style="font-size:14px;line-height:1.6;color:#333;"></div>
            </div>
        </div>

        <footer>
            Powered by 百炼大模型 (Qwen) · 部署于 Cloudflare Workers
        </footer>
    </div>

    <script>
        const API_BASE = '/api';

        const ROLE_COLORS = {
            '主语':'subject','Subject':'subject','subject':'subject','S':'subject',
            '谓语':'predicate','Predicate':'predicate','predicate':'predicate','谓语动词':'predicate','V':'predicate',
            '表语':'predicative','Predicative':'predicative','predicative':'predicative',
            '宾语':'object','Object':'object','object':'object','O':'object',
            '定语':'attributive','Attributive':'attributive','attributive':'attributive',
            '状语':'adverbial','Adverbial':'adverbial','adverbial':'adverbial','Adv':'adverbial',
            '补语':'complement','Complement':'complement','complement':'complement',
            '动词':'verb','Verb':'verb','verb':'verb',
            '名词':'noun','Noun':'noun','noun':'noun',
            情态动词:'verb','情态':'verb',
            'determiner':'attributive','adjective':'attributive',
            'auxiliary verb':'verb','auxiliary':'verb',
            'preposition':'adverbial',
            'time adverbial':'adverbial','地点状语':'adverbial','时间状语':'adverbial',
            'adverbial of duration':'adverbial',
            'object of preposition':'object','时长宾语':'object','direct object':'object','indirect object':'object',
            '介词短语作状语':'adverbial','时量宾语':'object',
        };

        function esc(str) {
            return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        }

        function highlightSentence(sentence, components) {
            if (!components || !components.length) return esc(sentence);
            const sorted = components.map(c => {
                let text = (c.text || '').trim();
                // 先精确匹配，再尝试忽略大小写
                let idx = sentence.indexOf(text);
                if (idx === -1 && text.length > 0) {
                    idx = sentence.toLowerCase().indexOf(text.toLowerCase());
                }
                return { role: c.role || '', text: text, idx: idx };
            }).filter(c => c.idx !== -1 && c.text.length > 0)
              .sort((a, b) => a.idx - b.idx || b.text.length - a.text.length);
            if (!sorted.length) return esc(sentence);
            let result = '', pos = 0;
            for (const comp of sorted) {
                if (comp.idx < pos) continue;
                if (comp.idx > pos) result += esc(sentence.substring(pos, comp.idx));
                const cls = ROLE_COLORS[comp.role] || 'default';
                // 从原句中截取文本，保留原始大小写
                const actualText = sentence.substring(comp.idx, comp.idx + comp.text.length);
                result += '<span class="hl-comp hl-' + cls + '" data-role="' + esc(comp.role) + '">' + esc(actualText) + '</span>';
                pos = comp.idx + comp.text.length;
            }
            if (pos < sentence.length) result += esc(sentence.substring(pos));
            return result;
        }

                async function analyzeSentence() {
            const input = document.getElementById('analyze-input');
            const btn = document.getElementById('analyze-btn');
            const result = document.getElementById('analyze-result');
            const sentence = input.value.trim();
            if (!sentence) { alert('请输入句子'); return; }
            result.style.display = 'block';
            result.className = 'result loading';
            result.textContent = '🔍 分析中...';
            btn.disabled = true;
            try {
                const resp = await fetch(API_BASE + '/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({sentence, language: null})
                });
                const data = await resp.json();
                result.className = 'result';
                if (data.error) {
                    result.innerHTML = '<div class="error-line">❌ ' + data.error + '</div>';
                    return;
                }
                const langLabel = data.language === 'en' ? '英语' : data.language === 'zh' ? '汉语' : data.language;
                let html = '';
                html += '<div class="analysis-header"><strong>📝 原句:</strong></div>';
                html += '<div class="hl-sentence">' + highlightSentence(data.original, data.components) + '</div>';
                if (data.translation) html += '<div class="analysis-row"><strong>🌐 翻译:</strong> ' + data.translation + '</div>';
                html += '<div class="analysis-row"><strong>🗂️ 类型:</strong> ' + (data.sentence_type || 'N/A') + ' · <strong>🔤 语言:</strong> ' + langLabel + '</div>';
                if (data.structure_type) html += '<div class="analysis-row"><strong>🏗️ 结构:</strong> ' + data.structure_type + '</div>';
                if (data.structure_pattern) html += '<div class="analysis-row"><strong>📐 模式:</strong> <code>' + data.structure_pattern + '</code></div>';
                if (data.tense_aspect) html += '<div class="analysis-row"><strong>⏰ 时态:</strong> ' + data.tense_aspect + '</div>';
                if (data.components && data.components.length) {
                    html += '<div class="analysis-section"><strong>🧩 成分分析:</strong></div>';
                    html += '<div class="example-components">';
                    data.components.forEach(c => {
                        const role = typeof c === 'object' ? (c.role || '') : '';
                        const text = typeof c === 'object' ? (c.text || c) : c;
                        const roleCls = ROLE_COLORS[role] || 'default';
                        html += '<span class="component-tag comp-tag-' + roleCls + '"><span class="comp-role">' + role + '</span> ' + text + '</span>';
                    });
                    html += '</div>';
                }
                if (data.key_phrases && data.key_phrases.length) {
                    html += '<div class="analysis-section" style="margin-top:10px"><strong>🔑 关键词组:</strong></div>';
                    html += '<div style="display:flex;flex-wrap:wrap;gap:5px;margin-top:5px">';
                    data.key_phrases.forEach(kp => {
                        html += '<span class="component-tag">' + kp + '</span>';
                    });
                    html += '</div>';
                }
                if (data.difficulty) {
                    const badges = {'beginner': '初级', 'intermediate': '中级', 'advanced': '高级'};
                    html += '<div class="analysis-row" style="margin-top:10px"><strong>📊 难度:</strong> <span class="difficulty-badge ' + data.difficulty + '">' + (badges[data.difficulty] || data.difficulty) + '</span></div>';
                }
                result.innerHTML = html;
            } catch (e) {
                result.className = 'result error';
                result.innerHTML = '❌ 请求失败: ' + e.message;
            } finally {
                btn.disabled = false;
            }
        }

        async function loadPatternOptions() {
            try {
                const resp = await fetch(API_BASE + '/patterns');
                const data = await resp.json();
                const patterns = data.patterns || [];
                const options = patterns.map(p => `<option value="${p.id}">${p.id} - ${p.name}</option>`).join('');
                document.getElementById('example-pattern').innerHTML = '<option value="">-- 选择句型 --</option>' + options;
                document.getElementById('exercise-pattern').innerHTML = '<option value="">-- 选择句型 --</option>' + options;
            } catch (e) { console.error('加载句型库失败:', e); }
        }

        async function generateExamples() {
            const pattern = document.getElementById('example-pattern').value;
            const language = document.getElementById('example-lang').value;
            const count = parseInt(document.getElementById('example-count').value);
            const difficulty = document.querySelector('input[name="example-difficulty"]:checked')?.value || '一般';
            const result = document.getElementById('examples-result');
            if (!pattern) { alert('请选择句型'); return; }
            result.style.display = 'block';
            result.className = 'result loading';
            result.textContent = '✨ 生成中...';
            try {
                const resp = await fetch(API_BASE + '/examples', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({pattern, language, count, difficulty})
                });
                const data = await resp.json();
                result.className = 'result';
                if (data.error) {
                    result.innerHTML = '<div class="error-line">❌ ' + data.error + '</div>';
                    return;
                }
                let html = '<div class="pattern-header">📐 结构模式: <code>' + (data.structure_pattern || '') + '</code></div>';
                if (data.examples && data.examples.length) {
                    html += '<div class="examples-list">';
                    data.examples.forEach((ex, i) => {
                        html += '<div class="example-card">';
                        html += '<div class="example-card-header">';
                        html += '<div class="example-num">#' + (i+1) + '</div>';
                        html += '<button class="btn-save-single" data-action="save-example-single" data-index="' + i + '" title="保存此例句到知识库">📌</button>';
                        html += '</div>';
                        html += '<div class="example-sentence">' + highlightSentence(ex.sentence, ex.components) + '</div>';
                        html += '<div class="example-translation">' + ex.translation + '</div>';
                        if (ex.components && ex.components.length) {
                            html += '<div class="example-components">';
                            ex.components.forEach(c => {
                                const roleCls = ROLE_COLORS[c.role] || 'default';
                                html += '<span class="component-tag comp-tag-' + roleCls + '"><span class="comp-role">' + c.role + '</span> ' + c.text + '</span>';
                            });
                            html += '</div>';
                        }
                        if (ex.difficulty) {
                            const badges = {'beginner': '初级', 'intermediate': '中级', 'advanced': '高级'};
                            html += '<span class="difficulty-badge ' + ex.difficulty + '">' + (badges[ex.difficulty] || ex.difficulty) + '</span>';
                        }
                        html += '</div>';
                    });
                    html += '</div>';
                }
                if (data.learning_tips) {
                    html += '<div class="learning-tips">💡 学习提示: ' + data.learning_tips + '</div>';
                }
                html += '<div style="margin-top:12px;text-align:right;"><button class="btn btn-primary" data-action="save-examples">📦 保存到知识库</button></div>';
                result.innerHTML = html;
                // 保存当前数据供「保存」按钮使用
                window._lastExamplesData = data;
            } catch (e) {
                result.className = 'result error';
                result.innerHTML = '❌ 错误: ' + e.message;
            }
        }

        async function generateExercises() {
            const pattern = document.getElementById('exercise-pattern').value;
            const language = document.getElementById('exercise-lang').value;
            const count = parseInt(document.getElementById('exercise-count').value);
            const difficulty = document.querySelector('input[name="exercise-difficulty"]:checked')?.value || '一般';
            const result = document.getElementById('exercises-result');
            if (!pattern) { alert('请选择句型'); return; }
            result.style.display = 'block';
            result.className = 'result loading';
            result.textContent = '🎯 生成中...';
            try {
                const resp = await fetch(API_BASE + '/exercises', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({pattern, language, count, difficulty})
                });
                const data = await resp.json();
                result.className = 'result';
                if (data.error) {
                    result.innerHTML = '<div class="error-line">❌ ' + data.error + '</div>';
                    return;
                }
                if (!data.exercises || !data.exercises.length) {
                    result.innerHTML = '<div class="error-line">⚠️ 未生成练习题</div>';
                    return;
                }
                let html = '<div class="exercises-list">';
                data.exercises.forEach((ex, i) => {
                    html += '<div class="exercise-card">';
                    html += '<div class="example-card-header">';
                    html += '<div class="exercise-num">第 ' + (i+1) + ' 题</div>';
                    html += '<button class="btn-save-single" data-action="save-exercise-single" data-index="' + i + '" title="保存此题到知识库">📌</button>';
                    html += '</div>';
                    html += '<div class="exercise-question">' + ex.question + '</div>';
                    if (ex.options) {
                        html += '<div class="exercise-options">';
                        const letters = ['A', 'B', 'C', 'D'];
                        letters.forEach(letter => {
                            if (ex.options[letter]) {
                                const isCorrect = ex.answer === letter;
                                html += '<div class="option-row' + (isCorrect ? ' option-correct' : '') + '">';
                                html += '<span class="option-letter">' + letter + '</span>';
                                html += '<span class="option-text">' + ex.options[letter] + '</span>';
                                if (isCorrect) html += '<span class="option-check">✅</span>';
                                html += '</div>';
                            }
                        });
                        html += '</div>';
                    }
                    html += '<div class="exercise-explanation">💡 ' + ex.explanation + '</div>';
                    if (ex.answer) {
                        html += '<div class="exercise-answer">✅ 正确答案: <strong>' + ex.answer + '</strong></div>';
                    }
                    html += '</div>';
                });
                html += '</div>';
                html += '<div style="margin-top:12px;text-align:right;"><button class="btn btn-primary" data-action="save-exercises">📦 保存到知识库</button></div>';
                result.innerHTML = html;
                window._lastExercisesData = data;
            } catch (e) {
                result.className = 'result error';
                result.innerHTML = '❌ 错误: ' + e.message;
            }
        }

        async function loadPatterns() {
            const language = document.getElementById('pattern-lang').value;
            const level = document.getElementById('pattern-level').value;
            const result = document.getElementById('patterns-result');
            result.innerHTML = '<div class="loading">📚 加载中...</div>';
            try {
                let url = API_BASE + '/patterns';
                const params = new URLSearchParams();
                if (language) params.set('language', language);
                if (level) params.set('level', level);
                const query = params.toString();
                if (query) url += '?' + query;
                const resp = await fetch(url);
                const data = await resp.json();
                const patterns = data.patterns || [];
                const levelMap = {beginner: '初中', intermediate: '高中', advanced: '大学'};
                result.innerHTML = patterns.map(p => `
                    <div class="pattern-item">
                        <div class="name">${p.id} - ${p.name}</div>
                        <div class="meta"><span class="level-tag level-${p.level}">${levelMap[p.level] || p.level}</span> · ${p.pattern}</div>
                        <div class="meta">例句: ${p.example}</div>
                    </div>
                `).join('');
            } catch (e) {
                result.innerHTML = '<div class="result error">❌ 加载失败: ' + e.message + '</div>';
            }
        }

        // ── 知识库功能 ──
        async function saveExamplesToKnowledge() {
            const data = window._lastExamplesData;
            if (!data || !data.examples || !data.examples.length) {
                alert('没有可保存的例句数据');
                return;
            }
            try {
                const resp = await fetch(API_BASE + '/knowledge', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        type: 'examples',
                        title: '例句 - ' + (data.structure_pattern || ''),
                        content: data,
                        structure_pattern: data.structure_pattern || '',
                        examples_count: data.examples.length,
                        learning_tips: data.learning_tips || ''
                    })
                });
                const result = await resp.json();
                if (result.success) {
                    alert('✅ 已保存到知识库！');
                } else {
                    alert('❌ 保存失败: ' + (result.error || '未知错误'));
                }
            } catch (e) {
                alert('❌ 保存失败: ' + e.message);
            }
        }

        async function saveExercisesToKnowledge() {
            const data = window._lastExercisesData;
            if (!data || !data.exercises || !data.exercises.length) {
                alert('没有可保存的练习题数据');
                return;
            }
            try {
                const resp = await fetch(API_BASE + '/knowledge', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        type: 'exercises',
                        title: '练习题 - ' + (data.structure_pattern || ''),
                        content: data,
                        structure_pattern: data.structure_pattern || '',
                        exercises_count: data.exercises.length
                    })
                });
                const result = await resp.json();
                if (result.success) {
                    alert('✅ 已保存到知识库！');
                } else {
                    alert('❌ 保存失败: ' + (result.error || '未知错误'));
                }
            } catch (e) {
                alert('❌ 保存失败: ' + e.message);
            }
        }

        // ── 单条保存到知识库 ──
        async function saveExampleToKnowledge(index) {
            const data = window._lastExamplesData;
            if (!data || !data.examples || !data.examples[index]) {
                alert('没有可保存的例句数据');
                return;
            }
            const example = data.examples[index];
            try {
                const resp = await fetch(API_BASE + '/knowledge', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        type: 'example',
                        title: '例句 - ' + (data.structure_pattern || '') + ' (' + example.sentence.substring(0, 30) + ')',
                        content: { structure_pattern: data.structure_pattern, examples: [example], learning_tips: data.learning_tips || '' },
                        structure_pattern: data.structure_pattern || '',
                        examples_count: 1
                    })
                });
                const result = await resp.json();
                if (result.success) {
                    alert('✅ 已保存到知识库！');
                } else {
                    alert('❌ 保存失败: ' + (result.error || '未知错误'));
                }
            } catch (e) {
                alert('❌ 保存失败: ' + e.message);
            }
        }

        async function saveExerciseToKnowledge(index) {
            const data = window._lastExercisesData;
            if (!data || !data.exercises || !data.exercises[index]) {
                alert('没有可保存的练习题数据');
                return;
            }
            const exercise = data.exercises[index];
            try {
                const resp = await fetch(API_BASE + '/knowledge', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        type: 'exercise',
                        title: '练习题 - ' + (data.structure_pattern || '') + ' (' + exercise.question.substring(0, 30) + ')',
                        content: { structure_pattern: data.structure_pattern, exercises: [exercise] },
                        structure_pattern: data.structure_pattern || '',
                        exercises_count: 1
                    })
                });
                const result = await resp.json();
                if (result.success) {
                    alert('✅ 已保存到知识库！');
                } else {
                    alert('❌ 保存失败: ' + (result.error || '未知错误'));
                }
            } catch (e) {
                alert('❌ 保存失败: ' + e.message);
            }
        }

        async function loadKnowledgeBase() {
            const result = document.getElementById('knowledge-result');
            result.innerHTML = '<div class="loading">📦 加载中...</div>';
            try {
                const resp = await fetch(API_BASE + '/knowledge');
                const data = await resp.json();
                const entries = data.entries || [];
                if (!entries.length) {
                    result.innerHTML = '<div style="text-align:center;padding:30px;color:#888;">📭 知识库为空，先生成例句或练习题后保存到这里吧</div>';
                    return;
                }
                let html = '<div style="display:flex;flex-direction:column;gap:10px;">';
                // 按保存时间倒序
                entries.reverse();
                entries.forEach(e => {
                    const typeLabel = e.type === 'examples' ? '✨ 例句' : '🎯 练习题';
                    const time = new Date(e.saved_at).toLocaleString('zh-CN');
                    html += '<div style="display:flex;align-items:center;justify-content:space-between;padding:12px 15px;background:#f8f9fa;border-radius:8px;border-left:4px solid #667eea;">';
                    html += '<div style="flex:1;cursor:pointer;" data-action="open-detail" data-id="' + e.id + '">';
                    html += '<div><strong>' + typeLabel + '</strong> ' + esc(e.title) + '</div>';
                    if (e.structure_pattern) {
                        html += '<div style="display:flex;gap:6px;margin-top:4px;flex-wrap:wrap;">';
                        html += '<span style="display:inline-block;background:#667eea20;color:#667eea;font-size:11px;padding:1px 8px;border-radius:4px;border:1px solid #667eea40;">📐 ' + esc(e.structure_pattern) + '</span>';
                        html += '</div>';
                    }
                    html += '<div style="font-size:12px;color:#888;margin-top:3px;">🕐 ' + time + '</div>';
                    html += '</div>';
                    html += '<button data-action="delete-entry" data-id="' + e.id + '" style="background:none;border:1px solid #ddd;border-radius:5px;padding:5px 10px;cursor:pointer;color:#dc3545;font-size:12px;margin-left:10px;">🗑️ 删除</button>';
                    html += '</div>';
                });
                html += '</div>';
                result.innerHTML = html;
            } catch (e) {
                result.innerHTML = '<div class="result error">❌ 加载失败: ' + e.message + '</div>';
            }
        }

        async function openKnowledgeDetail(entryId) {
            try {
                const resp = await fetch(API_BASE + '/knowledge?id=' + entryId, {method: 'PATCH'});
                const data = await resp.json();
                if (data.error) {
                    alert('获取详情失败: ' + data.error);
                    return;
                }
                const modal = document.getElementById('knowledge-detail-modal');
                document.getElementById('detail-title').textContent = data.type === 'examples' ? '✨ 例句详情' : '🎯 练习题详情';
                let bodyHtml = '<div style="margin-bottom:10px;"><strong>标题:</strong> ' + esc(data.title || '') + '</div>';
                bodyHtml += '<div style="margin-bottom:10px;"><strong>保存时间:</strong> ' + new Date(data.saved_at).toLocaleString('zh-CN') + '</div>';
                if (data.type === 'examples' && data.content && data.content.examples) {
                    bodyHtml += '<div style="margin-bottom:8px;"><strong>例句 (' + data.content.examples.length + ' 条):</strong></div>';
                    data.content.examples.forEach((ex, i) => {
                        bodyHtml += '<div style="padding:8px 10px;background:#f5f5ff;border-radius:5px;margin-bottom:6px;">';
                        bodyHtml += '<div style="font-weight:600;">#' + (i+1) + ' ' + esc(ex.sentence) + '</div>';
                        bodyHtml += '<div style="color:#888;font-size:13px;">' + esc(ex.translation) + '</div>';
                        bodyHtml += '</div>';
                    });
                    if (data.content.learning_tips) {
                        bodyHtml += '<div style="padding:8px 10px;background:#fff8e1;border-radius:5px;margin-top:8px;">💡 ' + esc(data.content.learning_tips) + '</div>';
                    }
                } else if (data.type === 'exercises' && data.content && data.content.exercises) {
                    bodyHtml += '<div style="margin-bottom:8px;"><strong>练习题 (' + data.content.exercises.length + ' 题):</strong></div>';
                    data.content.exercises.forEach((ex, i) => {
                        bodyHtml += '<div style="padding:8px 10px;background:#f5f5ff;border-radius:5px;margin-bottom:8px;">';
                        bodyHtml += '<div style="font-weight:600;margin-bottom:4px;">第 ' + (i+1) + ' 题: ' + esc(ex.question) + '</div>';
                        if (ex.options) {
                            const letters = ['A', 'B', 'C', 'D'];
                            letters.forEach(letter => {
                                if (ex.options[letter]) {
                                    const mark = ex.answer === letter ? ' ✅' : '';
                                    bodyHtml += '<div style="padding:2px 0;font-size:13px;">' + letter + '. ' + esc(ex.options[letter]) + mark + '</div>';
                                }
                            });
                        }
                        bodyHtml += '<div style="color:#2e7d32;font-size:13px;margin-top:3px;">✅ 答案: ' + ex.answer + ' — ' + esc(ex.explanation) + '</div>';
                        bodyHtml += '</div>';
                    });
                }
                bodyHtml += '<div style="margin-top:12px;text-align:right;"><button class="btn btn-primary" data-action="close-detail" style="padding:8px 16px;">关闭</button></div>';
                document.getElementById('detail-body').innerHTML = bodyHtml;
                modal.style.display = 'flex';
            } catch (e) {
                alert('获取详情失败: ' + e.message);
            }
        }

        function closeKnowledgeDetail() {
            document.getElementById('knowledge-detail-modal').style.display = 'none';
        }

        async function deleteKnowledge(entryId) {
            if (!confirm('确定要删除这条记录吗？')) return;
            try {
                const resp = await fetch(API_BASE + '/knowledge', {
                    method: 'DELETE',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id: entryId})
                });
                const result = await resp.json();
                if (result.success) {
                    alert('🗑️ 已删除');
                    loadKnowledgeBase();
                } else {
                    alert('❌ 删除失败: ' + (result.error || '未知错误'));
                }
            } catch (e) {
                alert('❌ 删除失败: ' + e.message);
            }
        }

        // ── 初始化：DOMContentLoaded 后绑定所有事件 ──
        document.addEventListener('DOMContentLoaded', function() {
            // Tab 切换
            document.querySelectorAll('.tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
                    tab.classList.add('active');
                    document.getElementById('tab-' + tab.dataset.tab).style.display = 'block';
                    if (tab.dataset.tab === 'knowledge') {
                        loadKnowledgeBase();
                    }
                });
            });

            // 句子分析按钮
            document.getElementById('analyze-btn').addEventListener('click', analyzeSentence);

            // 例句生成按钮
            document.getElementById('examples-btn').addEventListener('click', generateExamples);

            // 练习题按钮
            document.getElementById('exercises-btn').addEventListener('click', generateExercises);

            // 句型库按钮 & 筛选自动刷新
            document.getElementById('patterns-btn').addEventListener('click', loadPatterns);
            document.getElementById('pattern-lang').addEventListener('change', loadPatterns);
            document.getElementById('pattern-level').addEventListener('change', loadPatterns);

            // 知识库按钮
            document.getElementById('knowledge-btn').addEventListener('click', loadKnowledgeBase);

            // 详情弹窗 — 点击遮罩关闭
            document.getElementById('knowledge-detail-modal').addEventListener('click', function(e) {
                if (e.target === this) closeKnowledgeDetail();
            });
            document.getElementById('detail-close-btn').addEventListener('click', closeKnowledgeDetail);

            // ── 事件委托：动态生成内容的点击处理 ──
            // 例句区域：保存到知识库（全部或单条）
            document.getElementById('examples-result').addEventListener('click', function(e) {
                const btn = e.target.closest('[data-action="save-examples"]');
                if (btn) saveExamplesToKnowledge();
                const single = e.target.closest('[data-action="save-example-single"]');
                if (single) saveExampleToKnowledge(parseInt(single.getAttribute('data-index')));
            });
            // 练习题区域：保存到知识库（全部或单条）
            document.getElementById('exercises-result').addEventListener('click', function(e) {
                const btn = e.target.closest('[data-action="save-exercises"]');
                if (btn) saveExercisesToKnowledge();
                const single = e.target.closest('[data-action="save-exercise-single"]');
                if (single) saveExerciseToKnowledge(parseInt(single.getAttribute('data-index')));
            });
            // 知识库区域：查看详情 / 删除
            document.getElementById('knowledge-result').addEventListener('click', function(e) {
                const detail = e.target.closest('[data-action="open-detail"]');
                if (detail) openKnowledgeDetail(detail.getAttribute('data-id'));
                const del = e.target.closest('[data-action="delete-entry"]');
                if (del) deleteKnowledge(del.getAttribute('data-id'));
            });
            // 详情内容区域：关闭按钮
            document.getElementById('detail-body').addEventListener('click', function(e) {
                const btn = e.target.closest('[data-action="close-detail"]');
                if (btn) closeKnowledgeDetail();
            });

            // 首次加载：填充句型下拉框
            loadPatternOptions();
        });
    </script>
</body>
</html>"""

        html_headers = Headers.new()
        html_headers.set("Content-Type", "text/html; charset=utf-8")
        for key, value in cors_headers.items():
            html_headers.set(key, value)
        return Response.new(html_content, status=200, headers=html_headers)

    except Exception as e:
        return make_response({"error": str(e)}, 500, cors_headers)

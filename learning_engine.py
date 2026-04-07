# -*- coding: utf-8 -*-
"""
AI Learning - 句子结构分析与学习系统
核心引擎：调用百炼 API 进行句子结构分析、例句生成、练习题生成和批改
"""

import json
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import API_KEY, auto_detect_task_type, select_model, TokenManager, TOKENS
import dashscope
from dashscope import Generation
dashscope.api_key = API_KEY

# ============ 系统提示词 ============

# 句子结构分析提示词
STRUCTURE_ANALYSIS_PROMPT = """你是一个专业的语言学分析助手，精通英语和汉语的句子结构分析。

任务：分析用户输入的句子，提取其语法结构，并以JSON格式返回。

支持语言：英语 (en) 和 汉语 (zh)

分析维度：
1. 句子类型（陈述句、疑问句、祈使句、感叹句等）
2. 句子成分（主语、谓语、宾语、定语、状语、补语等）
3. 语法结构（简单句、复合句、复杂句等）
4. 时态/语态（英语）或 体貌/语气（汉语）
5. 关键词汇和短语
6. 结构模式（可复用的句型模板）
7. 翻译（英文句子必须提供中文翻译，中文句子必须提供英文翻译）

返回JSON格式：
{
  "language": "en" | "zh",
  "original": "原句",
  "translation": "翻译（英文句子翻译成中文，中文句子翻译成英文）",
  "sentence_type": "句子类型",
  "structure_type": "结构类型（简单句/复合句/复杂句）",
  "components": [
    {"role": "主语", "text": "...", "explanation": "..."},
    {"role": "谓语", "text": "...", "explanation": "..."},
    {"role": "宾语", "text": "...", "explanation": "..."}
  ],
  "tense_aspect": "时态/体貌说明",
  "voice_mood": "语态/语气说明",
  "key_phrases": ["关键词1", "关键词2"],
  "structure_pattern": "句型模板（用[]表示可替换部分）",
  "difficulty": "难度等级：beginner/intermediate/advanced",
  "notes": "补充说明"
}

重要：translation字段必须填写，英文句子翻译成中文，中文句子翻译成英文。
只返回JSON，不要其他文字。"""

# 例句生成提示词
EXAMPLE_GENERATION_PROMPT = """你是一个语言学习助手，根据给定的句子结构生成同类例句。

任务：基于提供的句子结构，生成多个同类结构的例句，帮助学习者理解和掌握该句型。

要求：
1. 例句必须与给定结构属于同一语法类型
2. 例句难度应与原句相当或略低（便于学习）
3. 例句内容应实用、贴近生活
4. 每个例句需附带中文翻译（如果是英语）或英文翻译（如果是汉语）
5. 标注每个例句的关键结构成分

返回JSON格式：
{
  "structure_pattern": "句型模板",
  "examples": [
    {
      "sentence": "例句",
      "translation": "翻译",
      "components": [{"role": "成分", "text": "..."}],
      "difficulty": "beginner/intermediate/advanced",
      "context": "使用场景说明"
    }
  ],
  "learning_tips": "学习建议"
}

生成5-8个例句，只返回JSON。"""

# 练习题生成提示词
EXERCISE_GENERATION_PROMPT = """你是一个语言教学专家，根据给定的句子结构生成练习题。

任务：基于提供的句子结构，设计多种类型的练习题，帮助学习者巩固掌握。

练习题类型：
1. 填空题 - 挖空关键成分，让学习者补全
2. 改错题 - 提供有语法错误的句子，让学习者改正
3. 翻译题 - 提供中文/英文，让学习者翻译成目标语言
4. 造句题 - 给定关键词或结构，让学习者造句
5. 选择题 - 提供多个选项，选择正确的句子结构

返回JSON格式：
{
  "structure_pattern": "句型模板",
  "exercises": [
    {
      "type": "fill_blank|error_correction|translation|sentence_making|choice",
      "question": "题目",
      "hint": "提示",
      "answer": "正确答案",
      "explanation": "解析说明",
      "difficulty": "beginner/intermediate/advanced"
    }
  ],
  "total_count": 题目数量,
  "estimated_time": "预计完成时间（分钟）"
}

生成6-10道练习题，涵盖至少3种题型，只返回JSON。"""

# 批改提示词
CORRECTION_PROMPT = """你是一个严格的语言学习批改助手，对用户提交的答案进行批改和指导。

任务：根据题目要求，对用户答案进行批改，给出详细反馈。

批改维度：
1. 正确性 - 答案是否正确
2. 完整性 - 是否完整回答了问题
3. 准确性 - 用词、语法是否准确
4. 改进建议 - 如何改进

返回JSON格式：
{
  "is_correct": true|false,
  "score": "分数（百分制）",
  "correct_answer": "正确答案",
  "user_answer": "用户答案",
  "errors": [
    {
      "type": "错误类型（grammar/vocabulary/structure/missing）",
      "description": "错误描述",
      "suggestion": "改进建议"
    }
  ],
  "strengths": ["优点1", "优点2"],
  "improvements": ["改进点1", "改进点2"],
  "detailed_feedback": "详细评语",
  "learning_resources": ["相关学习资源或知识点"]
}

只返回JSON，评语要鼓励性但指出具体问题。"""

# 常见句型库 - 覆盖初高中全部语法点
COMMON_PATTERNS = {
    "en": [
        # ===== 七年级上册 =====
        {"id": "en_001", "name": "主谓宾结构（简单句）", "pattern": "[Subject] + [Verb] + [Object]", "example": "I love English.", "level": "beginner", "grade": "七年级上"},
        {"id": "en_002", "name": "There be 句型", "pattern": "There is/are + [Noun] + [Place]", "example": "There is a book on the desk.", "level": "beginner", "grade": "七年级上"},
        {"id": "en_003", "name": "Be动词句型", "pattern": "[Subject] + am/is/are + [Predicative]", "example": "She is a student.", "level": "beginner", "grade": "七年级上"},
        {"id": "en_004", "name": "情态动词 can", "pattern": "[Subject] + can + [Verb原形]", "example": "I can swim.", "level": "beginner", "grade": "七年级上"},
        {"id": "en_005", "name": "Be动词一般疑问句", "pattern": "Am/Is/Are + [Subject] + [Predicative]?", "example": "Are you a teacher?", "level": "beginner", "grade": "七年级上"},
        {"id": "en_006", "name": "否定句（be/情态动词）", "pattern": "[Subject] + am/is/are/can + not + ...", "example": "I am not hungry.", "level": "beginner", "grade": "七年级上"},
        
        # ===== 七年级下册 =====
        {"id": "en_007", "name": "现在进行时", "pattern": "[Subject] + am/is/are + [Verb-ing]", "example": "She is reading now.", "level": "beginner", "grade": "七年级下"},
        {"id": "en_008", "name": "现在进行时疑问句", "pattern": "Am/Is/Are + [Subject] + [Verb-ing]?", "example": "Are you listening to me?", "level": "beginner", "grade": "七年级下"},
        {"id": "en_009", "name": "方位介词短语", "pattern": "[Noun] + in/on/under/behind + [Place]", "example": "The cat is under the table.", "level": "beginner", "grade": "七年级下"},
        {"id": "en_010", "name": "一般过去时（be动词）", "pattern": "[Subject] + was/were + [Predicative]", "example": "I was happy yesterday.", "level": "beginner", "grade": "七年级下"},
        {"id": "en_011", "name": "一般过去时（实义动词）", "pattern": "[Subject] + [Verb-ed] + [Object]", "example": "I visited Beijing last week.", "level": "beginner", "grade": "七年级下"},
        {"id": "en_012", "name": "一般过去时疑问句", "pattern": "Did + [Subject] + [Verb原形] + ...?", "example": "Did you go to school yesterday?", "level": "beginner", "grade": "七年级下"},
        
        # ===== 八年级上册 =====
        {"id": "en_013", "name": "现在完成时（have/has done）", "pattern": "[Subject] + have/has + [Past Participle]", "example": "I have finished my homework.", "level": "intermediate", "grade": "八年级上"},
        {"id": "en_014", "name": "现在完成时疑问句", "pattern": "Have/Has + [Subject] + [Past Participle]?", "example": "Have you seen the movie?", "level": "intermediate", "grade": "八年级上"},
        {"id": "en_015", "name": "过去进行时", "pattern": "[Subject] + was/were + [Verb-ing]", "example": "I was reading at 8 o'clock.", "level": "intermediate", "grade": "八年级上"},
        {"id": "en_016", "name": "形容词比较级", "pattern": "[A] + is/am/are + [Adjective-er] + than + [B]", "example": "He is taller than me.", "level": "intermediate", "grade": "八年级上"},
        {"id": "en_017", "name": "形容词最高级", "pattern": "[A] + is + the + [Adjective-est] + in/of ...", "example": "She is the tallest in the class.", "level": "intermediate", "grade": "八年级上"},
        {"id": "en_018", "name": "副词比较级/最高级", "pattern": "[A] + [Adverb] + (er/est) + than/in ...", "example": "He runs faster than me.", "level": "intermediate", "grade": "八年级上"},
        
        # ===== 八年级下册 =====
        {"id": "en_019", "name": "被动语态（一般现在时）", "pattern": "[Subject] + am/is/are + [Past Participle]", "example": "English is spoken worldwide.", "level": "intermediate", "grade": "八年级下"},
        {"id": "en_020", "name": "被动语态（一般过去时）", "pattern": "[Subject] + was/were + [Past Participle]", "example": "The letter was sent yesterday.", "level": "intermediate", "grade": "八年级下"},
        {"id": "en_021", "name": "if条件句（第一类）", "pattern": "If + [Present Simple], [Future will/may ...]", "example": "If it rains, I will stay home.", "level": "intermediate", "grade": "八年级下"},
        {"id": "en_022", "name": "if条件句（第二类-虚拟）", "pattern": "If + [Past Simple], [would/could + Verb]", "example": "If I had time, I would help you.", "level": "intermediate", "grade": "八年级下"},
        {"id": "en_023", "name": "情态动词 must/should", "pattern": "[Subject] + must/should + [Verb原形]", "example": "You should study harder.", "level": "intermediate", "grade": "八年级下"},
        {"id": "en_024", "name": "used to 句型", "pattern": "[Subject] + used to + [Verb原形]", "example": "I used to play football.", "level": "intermediate", "grade": "八年级下"},
        
        # ===== 九年级 =====
        {"id": "en_025", "name": "定语从句（who/that）", "pattern": "[Noun] + who/that + [Verb ...]", "example": "The man who is standing there is my teacher.", "level": "advanced", "grade": "九年级"},
        {"id": "en_026", "name": "定语从句（which/that）", "pattern": "[Noun] + which/that + [Verb ...]", "example": "The book which I bought is interesting.", "level": "advanced", "grade": "九年级"},
        {"id": "en_027", "name": "定语从句（whose）", "pattern": "[Noun] + whose + [Noun] + [Verb ...]", "example": "The student whose name is Tom is here.", "level": "advanced", "grade": "九年级"},
        {"id": "en_028", "name": "宾语从句（that引导）", "pattern": "[Subject] + [Verb] + that + [Clause]", "example": "I think that he is right.", "level": "advanced", "grade": "九年级"},
        {"id": "en_029", "name": "宾语从句（whether/if）", "pattern": "[Subject] + [Verb] + whether/if + [Clause]", "example": "I wonder if he will come.", "level": "advanced", "grade": "九年级"},
        {"id": "en_030", "name": "宾语从句（疑问词）", "pattern": "[Subject] + [Verb] + what/where/when + [Clause]", "example": "I don't know where he lives.", "level": "advanced", "grade": "九年级"},
        {"id": "en_031", "name": "状语从句（时间when/while）", "pattern": "[主句], when/while + [从句]", "example": "I was reading when he came in.", "level": "advanced", "grade": "九年级"},
        {"id": "en_032", "name": "状语从句（原因because）", "pattern": "[主句], because + [原因从句]", "example": "I stayed home because it rained.", "level": "advanced", "grade": "九年级"},
        {"id": "en_033", "name": "状语从句（结果so）", "pattern": "[原因], so + [结果]", "example": "It rained heavily, so we cancelled the trip.", "level": "advanced", "grade": "九年级"},
        {"id": "en_034", "name": "状语从句（目的so that）", "pattern": "[主句], so that + [目的从句]", "example": "I studied hard so that I could pass the exam.", "level": "advanced", "grade": "九年级"},
        {"id": "en_035", "name": "状语从句（让步although）", "pattern": "Although/Though + [从句], [主句]", "example": "Although it was cold, he went out.", "level": "advanced", "grade": "九年级"},
        {"id": "en_036", "name": "主语从句", "pattern": "That/[疑问词] + [从句] + [谓语]", "example": "That he won surprised everyone.", "level": "advanced", "grade": "九年级"},
        {"id": "en_037", "name": "表语从句", "pattern": "[主语] + is + that/[疑问词] + [从句]", "example": "The problem is that we have no money.", "level": "advanced", "grade": "九年级"},
        {"id": "en_038", "name": "虚拟语气（与现在相反）", "pattern": "If + [Past Simple], [would/could + Verb原形]", "example": "If I were you, I would take this job.", "level": "advanced", "grade": "九年级"},
        {"id": "en_039", "name": "虚拟语气（与过去相反）", "pattern": "If + [Past Perfect], [would/could have + Past Participle]", "example": "If I had studied harder, I would have passed.", "level": "advanced", "grade": "九年级"},
        {"id": "en_040", "name": "虚拟语气（wish）", "pattern": "I wish + [过去式/过去完成时]", "example": "I wish I had more time.", "level": "advanced", "grade": "九年级"},
        {"id": "en_041", "name": "倒装句（否定词开头）", "pattern": "Never/Rarely/Seldom + [助动词] + [主语] + [动词]", "example": "Never have I seen such a beautiful sight.", "level": "advanced", "grade": "九年级"},
        {"id": "en_042", "name": "倒装句（Only开头）", "pattern": "Only + [状语] + [助动词] + [主语] + [动词]", "example": "Only then did I realize the truth.", "level": "advanced", "grade": "九年级"},
        {"id": "en_043", "name": "强调句型", "pattern": "It is/was + [强调部分] + that/who + [句子]", "example": "It was in Beijing that I met her.", "level": "advanced", "grade": "九年级"},
        {"id": "en_044", "name": "省略句", "pattern": "[If possible/When ready/etc.]", "example": "If possible, please call me tonight.", "level": "advanced", "grade": "九年级"},
        {"id": "en_045", "name": "情态动词 could/might", "pattern": "[Subject] + could/might + [Verb原形]", "example": "Could you help me, please?", "level": "intermediate", "grade": "八年级下"},
        {"id": "en_046", "name": "现在完成时（延续性动词）", "pattern": "[Subject] + have/has + [Verb-ed] + for/since", "example": "I have lived here for 10 years.", "level": "intermediate", "grade": "八年级上"},
        {"id": "en_047", "name": "现在完成时（already/yjust）", "pattern": "[Subject] + have/has + [already/just/yet] + [Verb-ed]", "example": "I have already finished my work.", "level": "intermediate", "grade": "八年级上"},
        {"id": "en_048", "name": "情态动词 have to", "pattern": "[Subject] + have/has to + [Verb原形]", "example": "I have to finish this today.", "level": "beginner", "grade": "七年级下"},
        {"id": "en_049", "name": "祈使句", "pattern": "[Verb原形] + [宾语] / Don't + [Verb原形]", "example": "Please sit down. / Don't be late.", "level": "beginner", "grade": "七年级上"},
        {"id": "en_050", "name": "感叹句", "pattern": "What + [a/an] + [Adj] + [N] + (it is)!", "example": "What a beautiful girl she is!", "level": "intermediate", "grade": "八年级上"},
    ],
    "zh": [
        # ===== 初中常用句型 =====
        {"id": "zh_001", "name": "主谓宾句", "pattern": "[主语] + [谓语] + [宾语]", "example": "我喜欢学习。", "level": "beginner", "grade": "七年级"},
        {"id": "zh_002", "name": "主系表句", "pattern": "[主语] + 是/为/乃 + [表语]", "example": "她是老师。", "level": "beginner", "grade": "七年级"},
        {"id": "zh_003", "name": "存现句（有字句）", "pattern": "[处所] + 有 + [名词]", "example": "桌子上有一本书。", "level": "beginner", "grade": "七年级"},
        {"id": "zh_004", "name": "存现句（无字句）", "pattern": "[处所] + 无 + [名词]", "example": "今天无事。", "level": "beginner", "grade": "七年级"},
        {"id": "zh_005", "name": "在字句", "pattern": "[主语] + 在 + [处所] + [动词短语]", "example": "我在学校学习。", "level": "beginner", "grade": "七年级"},
        {"id": "zh_006", "name": "是字句", "pattern": "[主语] + 是 + [名词]", "example": "北京是中国的首都。", "level": "beginner", "grade": "七年级"},
        {"id": "zh_007", "name": "把字句", "pattern": "[主语] + 把 + [宾语] + [动词] + [补语]", "example": "我把作业写完了。", "level": "intermediate", "grade": "八年级"},
        {"id": "zh_008", "name": "被字句", "pattern": "[宾语] + 被 + [主语/施事] + [动词]", "example": "作业被我写完了。", "level": "intermediate", "grade": "八年级"},
        {"id": "zh_009", "name": "被动句（一般）", "pattern": "[主语] + 被 + [动词]", "example": "他被开除了。", "level": "intermediate", "grade": "八年级"},
        {"id": "zh_010", "name": "连动句", "pattern": "[主语] + [动词1] + [宾语1] + [动词2] + [宾语2]", "example": "我去图书馆借书。", "level": "intermediate", "grade": "八年级"},
        {"id": "zh_011", "name": "兼语句（使令）", "pattern": "[主语] + 请/叫/让/使 + [兼语] + [动词]", "example": "老师让我们做作业。", "level": "intermediate", "grade": "八年级"},
        {"id": "zh_012", "name": "兼语句（喜恶）", "pattern": "[主语] + 喜欢/讨厌 + [兼语] + [动词]", "example": "我喜欢他唱歌。", "level": "intermediate", "grade": "八年级"},
        {"id": "zh_013", "name": "双宾语句", "pattern": "[主语] + [动词] + [间接宾语] + [直接宾语]", "example": "老师教我们英语。", "level": "intermediate", "grade": "八年级"},
        {"id": "zh_014", "name": "比较句", "pattern": "[A] + 比 + [B] + [形容词/动词短语]", "example": "他比我高。", "level": "intermediate", "grade": "八年级"},
        {"id": "zh_015", "name": "比较句（更）", "pattern": "[A] + 比 + [B] + 更/还 + [形容词]", "example": "今天比昨天更冷。", "level": "intermediate", "grade": "八年级"},
        {"id": "zh_016", "name": "感叹句", "pattern": "多/多么/真 + [形容词] + [名词/主谓短语]", "example": "多么美丽的风景啊！", "level": "beginner", "grade": "七年级"},
        {"id": "zh_017", "name": "疑问句（吗）", "pattern": "[主语] + [谓语] + [宾语] + 吗？", "example": "你是学生吗？", "level": "beginner", "grade": "七年级"},
        {"id": "zh_018", "name": "疑问句（呢）", "pattern": "[主语] + 在/是 + [处所/名词] + 呢？", "example": "你呢？", "level": "beginner", "grade": "七年级"},
        {"id": "zh_019", "name": "疑问句（谁）", "pattern": "谁 + [谓语] + [宾语/补语]？", "example": "谁是你的老师？", "level": "beginner", "grade": "七年级"},
        {"id": "zh_020", "name": "疑问句（什么）", "pattern": "[主语] + 做/是 + 什么？", "example": "你在做什么？", "level": "beginner", "grade": "七年级"},
        {"id": "zh_021", "name": "疑问句（哪里）", "pattern": "[主语] + 在 + 哪里？", "example": "你住在哪里？", "level": "beginner", "grade": "七年级"},
        {"id": "zh_022", "name": "疑问句（怎么）", "pattern": "怎么/怎么样 + [主谓短语]？", "example": "这本书怎么样？", "level": "beginner", "grade": "七年级"},
        {"id": "zh_023", "name": "疑问句（多少）", "pattern": "多少 + [名词] + [谓语]？", "example": "你们有多少人？", "level": "beginner", "grade": "七年级"},
        {"id": "zh_024", "name": "反问句", "pattern": "难道 + [主谓短语] + 不/没 + [谓语] + 吗？", "example": "难道你不知道吗？", "level": "intermediate", "grade": "八年级"},
        
        # ===== 高中常用句型 =====
        {"id": "zh_025", "name": "是...的强调句", "pattern": "[主语] + 是 + [时间/地点/方式] + [动词] + 的", "example": "我是昨天到北京的。", "level": "advanced", "grade": "高中"},
        {"id": "zh_026", "name": "双重否定句", "pattern": "没有/不/非 + [主语] + 没有/不/非 + [谓语]", "example": "没有人不知道这件事。", "level": "advanced", "grade": "高中"},
        {"id": "zh_027", "name": "省略句", "pattern": "[上文已出现] + 的 + [省略部分]", "example": "他的成绩比我的（成绩）好。", "level": "advanced", "grade": "高中"},
        {"id": "zh_028", "name": "被动句（被...所）", "pattern": "[主语] + 被 + [名词] + 所 + [动词]", "example": "他被大家所信任。", "level": "advanced", "grade": "高中"},
        {"id": "zh_029", "name": "被动句（为...所）", "pattern": "[主语] + 为 + [名词] + 所 + [动词]", "example": "这种思想为很多人所接受。", "level": "advanced", "grade": "高中"},
        {"id": "zh_030", "name": "递进复句", "pattern": "[主句]，而且/甚至 + [递进句]", "example": "他会英语，而且会法语。", "level": "advanced", "grade": "高中"},
        {"id": "zh_031", "name": "因果复句", "pattern": "[原因]，所以/因此/因而 + [结果]", "example": "因为下雨，所以我没出门。", "level": "advanced", "grade": "高中"},
        {"id": "zh_032", "name": "转折复句", "pattern": "[主句]，但是/然而/不过 + [转折句]", "example": "我喜欢他，但是不了解他。", "level": "advanced", "grade": "高中"},
        {"id": "zh_033", "name": "条件复句", "pattern": "只要/只有/除非 + [条件句] + [结果句]", "example": "只要你努力，就会成功。", "level": "advanced", "grade": "高中"},
        {"id": "zh_034", "name": "目的复句", "pattern": "[主句]，以便/为了 + [目的句]", "example": "我努力学习，以便考个好成绩。", "level": "advanced", "grade": "高中"},
        {"id": "zh_035", "name": "假设复句", "pattern": "如果/假如/要是 + [假设句] + [结果句]", "example": "如果你不努力，就会失败。", "level": "advanced", "grade": "高中"},
        {"id": "zh_036", "name": "让步复句", "pattern": "即使/虽然/尽管 + [让步句] + [主句]", "example": "虽然很累，但是我还是坚持。", "level": "advanced", "grade": "高中"},
        {"id": "zh_037", "name": "排比句", "pattern": "[短句1]，又/还 + [短句2]，更 + [短句3]", "example": "我们要学习，要实践，更要创新。", "level": "advanced", "grade": "高中"},
        {"id": "zh_038", "name": "对偶句", "pattern": "[对偶A]， [对偶B]", "example": "风声雨声读书声，声声入耳。", "level": "advanced", "grade": "高中"},
        {"id": "zh_039", "name": "把字句（复杂）", "pattern": "[主语] + 把 + [宾语] + 给 + [兼语] + [动词]", "example": "我把书借给他看。", "level": "advanced", "grade": "高中"},
        {"id": "zh_040", "name": "兼语句（委婉）", "pattern": "[主语] + 麻烦/劳驾 + [兼语] + [动词]", "example": "麻烦你帮我拿一下。", "level": "intermediate", "grade": "八年级"},
        {"id": "zh_041", "name": "存现句（着）", "pattern": "[处所] + 动词 + 着 + [名词]", "example": "墙上挂着一幅画。", "level": "intermediate", "grade": "八年级"},
        {"id": "zh_042", "name": "存现句（了）", "pattern": "[处所] + 动词 + 了 + [名词]", "example": "门口来了一个人。", "level": "intermediate", "grade": "八年级"},
        {"id": "zh_043", "name": "陈述句（肯定）", "pattern": "[主语] + [谓语] + [宾语/补语]", "example": "今天天气很好。", "level": "beginner", "grade": "七年级"},
        {"id": "zh_044", "name": "陈述句（否定）", "pattern": "[主语] + 不/没/无 + [谓语]", "example": "我不认识他。", "level": "beginner", "grade": "七年级"},
        {"id": "zh_045", "name": "祈使句", "pattern": "请/让/帮 + [动词短语]", "example": "请大家安静！", "level": "beginner", "grade": "七年级"},
        {"id": "zh_046", "name": "修辞句（比喻）", "pattern": "[本体] + 像/如/似 + [喻体]", "example": "弯弯的月亮像小船。", "level": "intermediate", "grade": "八年级"},
        {"id": "zh_047", "name": "修辞句（拟人）", "pattern": "[事物] + [人的动作/情感]", "example": "春风轻轻地唱歌。", "level": "intermediate", "grade": "八年级"},
        {"id": "zh_048", "name": "修辞句（夸张）", "pattern": "太/极/甚 + [形容词] + 了", "example": "高兴极了！", "level": "beginner", "grade": "七年级"},
        {"id": "zh_049", "name": "修辞句（排比）", "pattern": "[短语1]，又/也/还 + [短语2]，而且 + [短语3]", "example": "要认真，要努力，要有恒心。", "level": "advanced", "grade": "高中"},
        {"id": "zh_050", "name": "固定句式（不管...都）", "pattern": "不管/无论 + [条件] + 都/也 + [结果]", "example": "不管刮风下雨，他都坚持锻炼。", "level": "advanced", "grade": "高中"},
    ]
}

# ============ 核心功能 ============

def _extract_json(text: str) -> dict:
    """从 AI 回复中提取 JSON"""
    # 尝试直接解析
    try:
        return json.loads(text.strip())
    except Exception:
        pass

    # 提取 ```json ... ``` 块
    match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # 提取第一个 { ... }
    match = re.search(r'\{[\s\S]+\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    raise ValueError(f"无法从回复中提取JSON: {text[:200]}")


def _call_api(prompt: str, system_prompt: str, model_id: str = "qwen-plus-latest") -> dict:
    """调用百炼 API"""
    resp = Generation.call(
        model=model_id,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        result_format="message",
        stream=False,
    )

    if resp.status_code != 200:
        raise Exception(f"API错误: {resp.message}")

    return _extract_json(resp.output.choices[0].message.content)


def analyze_sentence(sentence: str, language: str = None) -> dict:
    """
    分析句子结构
    
    Args:
        sentence: 要分析的句子
        language: 语言代码 'en' 或 'zh'，None 则自动检测
    
    Returns:
        句子结构分析结果
    """
    # 自动检测语言
    if language is None:
        # 简单检测：包含中文字符则为中文
        if any('\u4e00' <= char <= '\u9fff' for char in sentence):
            language = "zh"
        else:
            language = "en"
    
    prompt = f"语言: {language}\n句子: {sentence}"
    
    result = _call_api(prompt, STRUCTURE_ANALYSIS_PROMPT)
    result["language"] = language
    return result


def generate_examples(structure_pattern: str, language: str, count: int = 5) -> dict:
    """
    基于句子结构生成例句
    
    Args:
        structure_pattern: 句型模板
        language: 目标语言 'en' 或 'zh'
        count: 生成例句数量
    
    Returns:
        例句列表
    """
    prompt = f"语言: {language}\n句型模板: {structure_pattern}\n生成例句数量: {count}"
    
    return _call_api(prompt, EXAMPLE_GENERATION_PROMPT)


def generate_exercises(structure_pattern: str, language: str, difficulty: str = None) -> dict:
    """
    基于句子结构生成练习题
    
    Args:
        structure_pattern: 句型模板
        language: 目标语言 'en' 或 'zh'
        difficulty: 难度等级 beginner/intermediate/advanced
    
    Returns:
        练习题列表
    """
    prompt = f"语言: {language}\n句型模板: {structure_pattern}"
    if difficulty:
        prompt += f"\n难度要求: {difficulty}"
    
    return _call_api(prompt, EXERCISE_GENERATION_PROMPT)


def check_answer(question: str, correct_answer: str, user_answer: str, question_type: str = None) -> dict:
    """
    批改用户答案
    
    Args:
        question: 题目
        correct_answer: 正确答案
        user_answer: 用户答案
        question_type: 题目类型
    
    Returns:
        批改结果
    """
    prompt = f"""题目: {question}
题目类型: {question_type or '未指定'}
正确答案: {correct_answer}
用户答案: {user_answer}"""
    
    return _call_api(prompt, CORRECTION_PROMPT)


def get_common_patterns(language: str = None, level: str = None) -> list:
    """
    获取常见句型库
    
    Args:
        language: 语言 'en' 或 'zh'，None 则返回全部
        level: 难度等级 beginner/intermediate/advanced
    
    Returns:
        句型列表
    """
    patterns = []
    
    if language is None or language == "en":
        patterns.extend(COMMON_PATTERNS["en"])
    if language is None or language == "zh":
        patterns.extend(COMMON_PATTERNS["zh"])
    
    if level:
        patterns = [p for p in patterns if p["level"] == level]
    
    return patterns


def get_pattern_by_id(pattern_id: str) -> dict:
    """根据ID获取句型"""
    for lang_patterns in COMMON_PATTERNS.values():
        for pattern in lang_patterns:
            if pattern["id"] == pattern_id:
                return pattern
    return None


# ============ 学习路径生成 ============

LEARNING_PATH_PROMPT = """你是一个语言学习规划专家，根据学习者的水平和目标制定个性化的句子结构学习路径。

任务：为学习者设计一个系统的句子结构学习计划。

返回JSON格式：
{
  "level": "当前水平评估",
  "goals": ["学习目标1", "学习目标2"],
  "phases": [
    {
      "phase": "阶段名称",
      "duration": "预计时长",
      "patterns": ["句型1", "句型2"],
      "focus": "学习重点",
      "milestones": ["里程碑1", "里程碑2"]
    }
  ],
  "recommendations": ["学习建议1", "学习建议2"],
  "resources": ["推荐资源1", "推荐资源2"]
}

只返回JSON。"""


def generate_learning_path(current_level: str, target_level: str, language: str) -> dict:
    """
    生成个性化学习路径
    
    Args:
        current_level: 当前水平 beginner/intermediate/advanced
        target_level: 目标水平
        language: 目标语言
    
    Returns:
        学习路径规划
    """
    prompt = f"""目标语言: {language}
当前水平: {current_level}
目标水平: {target_level}
请制定学习路径。"""
    
    return _call_api(prompt, LEARNING_PATH_PROMPT)

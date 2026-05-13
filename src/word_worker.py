# -*- coding: utf-8 -*-
"""
Word Learning - Cloudflare Worker
趣味单词拆解和学习系统
提供单词拆解、词源分析、记忆技巧、趣味练习等功能
"""

import json
import re
from js import URL, Response, fetch

# ============ 提示词定义 ============

WORD_BREAKDOWN_PROMPT = """你是一个专业的英语词汇教学专家，擅长用趣味、生动的方式拆解单词。

任务：分析用户输入的英语单词，进行趣味拆解，帮助学习者轻松记忆。

分析维度：
1. 词根词缀拆解（prefix-词根-suffix）
2. 词源故事（有趣的起源）
3. 联想记忆技巧（谐音、图像、故事等）
4. 常见搭配和例句
5. 同义词/反义词家族
6. 易混淆词辨析

返回JSON格式：
{
  "word": "单词",
  "phonetic": "音标",
  "part_of_speech": "词性",
  "meaning": "核心含义",
  "breakdown": {
    "prefix": {"text": "前缀", "meaning": "含义", "examples": ["例词1", "例词2"]},
    "root": {"text": "词根", "meaning": "含义", "examples": ["例词1", "例词2"]},
    "suffix": {"text": "后缀", "meaning": "含义", "examples": ["例词1", "例词2"]}
  },
  "etymology": {
    "origin": "词源语言（如Latin, Greek等）",
    "story": "有趣的词源故事（100字以内）",
    "evolution": "演变过程简述"
  },
  "memory_tips": [
    {"type": "association", "tip": "联想记忆技巧", "detail": "详细说明"},
    {"type": "pun", "tip": "谐音记忆", "detail": "详细说明"},
    {"type": "story", "tip": "故事记忆", "detail": "详细说明"}
  ],
  "collocations": ["常见搭配1", "常见搭配2", "常见搭配3"],
  "examples": [
    {"sentence": "例句", "translation": "翻译", "highlight": "例句中该词的用法亮点"}
  ],
  "word_family": {
    "synonyms": ["同义词1", "同义词2"],
    "antonyms": ["反义词1", "反义词2"],
    "derivatives": ["派生词1", "派生词2"]
  },
  "confusable": [
    {"word": "易混淆词", "difference": "区别说明"}
  ],
  "fun_fact": "一个有趣的知识点或冷知识",
  "difficulty": "beginner/intermediate/advanced"
}

重要：只返回JSON，不要包含任何思考过程或Markdown标记。"""

WORD_QUIZ_PROMPT = """你是一个趣味英语教学专家，根据给定的单词生成趣味练习题。

任务：设计有趣的练习题，帮助学习者巩固单词记忆。

题目类型要求：
1. 词根词缀猜词题（给出词根词缀，猜单词含义）
2. 联想记忆选择题（给出记忆技巧，选择对应单词）
3. 易混淆词辨析题
4. 语境填空题
5. 词源知识趣味题

返回JSON格式：
{
  "quizzes": [
    {
      "type": "root_guess|association|confusable|fill_blank|etymology",
      "question": "题目内容",
      "options": {"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"},
      "answer": "正确选项字母",
      "explanation": "答案解析",
      "fun_fact": "相关趣味知识点"
    }
  ],
  "tips": "学习建议"
}

生成5-8道题目，确保趣味性和教育性并重。只返回JSON。"""

WORD_STORY_PROMPT = """你是一个创意故事作家，擅长用有趣的记忆宫殿法帮助记忆单词。

任务：根据给定的单词列表，创作一个有趣的故事，将所有单词自然融入其中。

要求：
1. 故事情节有趣、连贯、易记
2. 每个单词在故事中高亮标注
3. 提供故事场景的可视化描述（便于脑中成像）
4. 故事长度适中（200-300词）

返回JSON格式：
{
  "title": "故事标题",
  "scene": "场景描述（便于脑中成像）",
  "story": "故事正文（用**单词**标记目标单词）",
  "translation": "故事中文翻译",
  "words_in_story": ["单词1", "单词2"],
  "memory_palace": {
    "location": "记忆宫殿位置",
    "path": "记忆路径描述",
    "hooks": [{"word": "单词", "hook": "记忆挂钩"}]
  }
}

只返回JSON。"""

# ============ 常用词根词缀库 ============

COMMON_ROOTS = {
    "prefixes": [
        {"text": "un-", "meaning": "不，相反", "examples": ["unhappy", "undo", "unreal"]},
        {"text": "re-", "meaning": "再，重新", "examples": ["rewrite", "return", "rebuild"]},
        {"text": "pre-", "meaning": "在...之前", "examples": ["preview", "predict", "prepare"]},
        {"text": "dis-", "meaning": "分离，不", "examples": ["disagree", "disappear", "disconnect"]},
        {"text": "mis-", "meaning": "错误地", "examples": ["misunderstand", "mislead", "mistake"]},
        {"text": "over-", "meaning": "过度，超过", "examples": ["overwork", "overeat", "overcome"]},
        {"text": "under-", "meaning": "不足，在...下", "examples": ["understand", "underestimate", "underwater"]},
        {"text": "anti-", "meaning": "反对，抵抗", "examples": ["antisocial", "antibody", "antiwar"]},
        {"text": "auto-", "meaning": "自动，自己", "examples": ["automatic", "autograph", "automobile"]},
        {"text": "bi-", "meaning": "两个，双", "examples": ["bicycle", "bilingual", "bimonthly"]},
    ],
    "roots": [
        {"text": "spect", "meaning": "看", "examples": ["inspect", "respect", "aspect"]},
        {"text": "struct", "meaning": "建造", "examples": ["structure", "construct", "instruct"]},
        {"text": "ject", "meaning": "投掷", "examples": ["inject", "reject", "project"]},
        {"text": "port", "meaning": "携带", "examples": ["import", "export", "transport"]},
        {"text": "form", "meaning": "形状", "examples": ["reform", "inform", "transform"]},
        {"text": "dict", "meaning": "说", "examples": ["predict", "dictionary", "dictate"]},
        {"text": "cred", "meaning": "相信", "examples": ["credit", "incredible", "credibility"]},
        {"text": "grad", "meaning": "步，级", "examples": ["grade", "gradual", "degrade"]},
        {"text": "chron", "meaning": "时间", "examples": ["chronic", "chronology", "synchronize"]},
        {"text": "therm", "meaning": "热", "examples": ["thermal", "thermometer", "thermostat"]},
    ],
    "suffixes": [
        {"text": "-tion", "meaning": "行为，状态", "examples": ["action", "creation", "information"]},
        {"text": "-able", "meaning": "可...的", "examples": ["readable", "enjoyable", "comfortable"]},
        {"text": "-ful", "meaning": "充满...的", "examples": ["beautiful", "helpful", "powerful"]},
        {"text": "-less", "meaning": "无...的", "examples": ["hopeless", "careless", "endless"]},
        {"text": "-ment", "meaning": "行为结果", "examples": ["development", "movement", "agreement"]},
        {"text": "-ness", "meaning": "性质，状态", "examples": ["happiness", "darkness", "kindness"]},
        {"text": "-er/-or", "meaning": "做...的人", "examples": ["teacher", "actor", "writer"]},
        {"text": "-ist", "meaning": "...主义者", "examples": ["artist", "scientist", "tourist"]},
        {"text": "-ive", "meaning": "有...性质的", "examples": ["active", "creative", "effective"]},
        {"text": "-ous", "meaning": "具有...的", "examples": ["famous", "dangerous", "curious"]},
    ]
}

# ============ 核心函数 ============

def _extract_json(text: str) -> dict:
    """从 AI 回复中提取 JSON"""
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


async def _call_api(prompt: str, system_prompt: str, api_key: str, model: str = "qwen-plus") -> dict:
    """调用百炼 API"""
    if not api_key:
        return {"error": "API_KEY 未配置，请在 Cloudflare Workers Dashboard 中设置环境变量 API_KEY"}

    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8
    })

    try:
        resp = await fetch(url, {
            "method": "POST",
            "headers": {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            "body": payload
        })

        if resp.status == 200:
            data = await resp.json()
            content = data["choices"][0]["message"]["content"]
            return _extract_json(content)
        else:
            error_text = await resp.text()
            return {"error": f"API错误: {resp.status} - {error_text}"}
    except Exception as e:
        return {"error": f"请求失败: {str(e)}"}


async def breakdown_word(word: str, api_key: str) -> dict:
    """单词趣味拆解"""
    prompt = f"请分析单词: {word}"
    return await _call_api(prompt, WORD_BREAKDOWN_PROMPT, api_key)


async def generate_quiz(word: str, difficulty: str, api_key: str) -> dict:
    """生成趣味练习题"""
    prompt = f"单词: {word}\n难度: {difficulty if difficulty else 'intermediate'}"
    return await _call_api(prompt, WORD_QUIZ_PROMPT, api_key)


async def generate_story(words: list, api_key: str) -> dict:
    """生成记忆故事"""
    prompt = f"请用以下单词创作一个有趣的记忆故事: {', '.join(words)}"
    return await _call_api(prompt, WORD_STORY_PROMPT, api_key)


def get_roots_library(category: str = None) -> list:
    """获取词根词缀库"""
    if category and category in COMMON_ROOTS:
        return COMMON_ROOTS[category]
    return COMMON_ROOTS


# ============ HTML 页面 ============

def get_html_page():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>趣味单词拆解 - Word Learning</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; color: #333; }
        .container { max-width: 1000px; margin: 0 auto; padding: 20px; }
        header { background: rgba(255,255,255,0.95); color: #333; padding: 30px 20px; border-radius: 15px; margin-bottom: 20px; text-align: center; box-shadow: 0 10px 40px rgba(0,0,0,0.2); }
        header h1 { font-size: 2.2em; margin-bottom: 10px; background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        header p { color: #666; }
        .nav-back { display: inline-block; margin-top: 15px; padding: 8px 20px; background: #f0f0f0; border-radius: 20px; color: #666; text-decoration: none; font-size: 14px; }
        .nav-back:hover { background: #e0e0e0; }
        .card { background: rgba(255,255,255,0.95); border-radius: 15px; padding: 25px; margin-bottom: 20px; box-shadow: 0 5px 20px rgba(0,0,0,0.1); }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .tab { padding: 12px 24px; border: none; background: #e8e8e8; border-radius: 25px; cursor: pointer; font-size: 14px; transition: all 0.3s; font-weight: 500; }
        .tab.active { background: linear-gradient(135deg, #667eea, #764ba2); color: white; }
        .tab:hover:not(.active) { background: #d8d8d8; transform: translateY(-2px); }
        .input-group { margin-bottom: 20px; }
        .input-group label { display: block; margin-bottom: 8px; font-weight: 600; color: #555; }
        .input-group input, .input-group select, .input-group textarea { width: 100%; padding: 12px 15px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 15px; transition: border-color 0.3s; }
        .input-group input:focus, .input-group textarea:focus { border-color: #667eea; outline: none; }
        .input-group textarea { min-height: 100px; resize: vertical; }
        .btn { padding: 14px 28px; border: none; border-radius: 25px; cursor: pointer; font-size: 15px; font-weight: 600; transition: all 0.3s; }
        .btn-primary { background: linear-gradient(135deg, #667eea, #764ba2); color: white; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(102,126,234,0.4); }
        .btn:disabled { opacity: 0.6; cursor: not- allowed; }
        .result { margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 10px; border-left: 4px solid #667eea; }
        .result.error { border-left-color: #dc3545; background: #fff5f5; }
        .loading { text-align: center; padding: 30px; color: #666; }
        .loading::after { content: ''; display: inline-block; width: 20px; height: 20px; border: 3px solid #667eea; border-radius: 50%; border-top-color: transparent; animation: spin 1s linear infinite; margin-left: 10px; vertical-align: middle; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .word-card { background: linear-gradient(135deg, #f8f9fa, #fff); border-radius: 15px; padding: 25px; margin-top: 20px; }
        .word-title { font-size: 2.5em; font-weight: bold; color: #667eea; margin-bottom: 5px; }
        .phonetic { color: #888; font-size: 1.1em; margin-bottom: 15px; }
        .breakdown-box { display: flex; gap: 10px; flex-wrap: wrap; margin: 20px 0; }
        .breakdown-part { padding: 15px 20px; border-radius: 10px; text-align: center; min-width: 120px; }
        .breakdown-prefix { background: #fff3cd; border: 2px solid #ffc107; }
        .breakdown-root { background: #d4edda; border: 2px solid #28a745; }
        .breakdown-suffix { background: #cce5ff; border: 2px solid #007bff; }
        .breakdown-part .text { font-size: 1.5em; font-weight: bold; display: block; }
        .breakdown-part .meaning { font-size: 0.9em; color: #666; }
        .memory-tip { background: #fff8e1; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0; border-radius: 0 10px 10px 0; }
        .memory-tip h4 { color: #f57c00; margin-bottom: 8px; }
        .example-box { background: #e3f2fd; padding: 15px; border-radius: 10px; margin: 10px 0; }
        .example-box .sentence { font-style: italic; color: #1565c0; }
        .example-box .translation { color: #666; margin-top: 5px; }
        .roots-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; margin-top: 20px; }
        .root-item { background: #f8f9fa; border-radius: 10px; padding: 15px; border-left: 4px solid #667eea; }
        .root-item .text { font-weight: bold; color: #667eea; font-size: 1.2em; }
        .root-item .meaning { color: #666; margin: 5px 0; }
        .root-item .examples { color: #888; font-size: 0.9em; }
        footer { text-align: center; padding: 20px; color: rgba(255,255,255,0.8); font-size: 13px; }
        @media (max-width: 600px) { .container { padding: 10px; } header h1 { font-size: 1.6em; } .tabs { gap: 5px; } .tab { padding: 10px 16px; font-size: 13px; } }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔤 趣味单词拆解</h1>
            <p>词根词缀 · 词源故事 · 联想记忆 · 趣味练习</p>
            <a href="/" class="nav-back">← 返回主入口</a>
        </header>

        <div class="tabs">
            <button class="tab active" data-tab="breakdown">🔍 单词拆解</button>
            <button class="tab" data-tab="quiz">🎯 趣味练习</button>
            <button class="tab" data-tab="story">📖 记忆故事</button>
            <button class="tab" data-tab="roots">📚 词根词缀库</button>
        </div>

        <div id="tab-breakdown" class="tab-content">
            <div class="card">
                <div class="input-group">
                    <label>输入英语单词</label>
                    <input type="text" id="word-input" placeholder="例如: incredible, misunderstanding, autobiography..." value="incredible">
                </div>
                <button class="btn btn-primary" id="breakdown-btn" onclick="breakdownWord()">🔍 趣味拆解</button>
                <div id="breakdown-result"></div>
            </div>
        </div>

        <div id="tab-quiz" class="tab-content" style="display:none;">
            <div class="card">
                <div class="input-group">
                    <label>输入单词（可选，留空则随机出题）</label>
                    <input type="text" id="quiz-word" placeholder="输入要练习的单词">
                </div>
                <div class="input-group">
                    <label>难度</label>
                    <select id="quiz-difficulty">
                        <option value="">自动</option>
                        <option value="beginner">初级</option>
                        <option value="intermediate">中级</option>
                        <option value="advanced">高级</option>
                    </select>
                </div>
                <button class="btn btn-primary" onclick="generateQuiz()">🎯 生成练习题</button>
                <div id="quiz-result"></div>
            </div>
        </div>

        <div id="tab-story" class="tab-content" style="display:none;">
            <div class="card">
                <div class="input-group">
                    <label>输入多个单词（用逗号或空格分隔）</label>
                    <textarea id="story-words" placeholder="例如: incredible, adventure, discover, mystery">incredible, adventure, discover, mystery</textarea>
                </div>
                <button class="btn btn-primary" onclick="generateStory()">📖 生成记忆故事</button>
                <div id="story-result"></div>
            </div>
        </div>

        <div id="tab-roots" class="tab-content" style="display:none;">
            <div class="card">
                <div class="input-group">
                    <label>分类筛选</label>
                    <select id="roots-category" onchange="loadRoots()">
                        <option value="">全部</option>
                        <option value="prefixes">前缀 (Prefixes)</option>
                        <option value="roots">词根 (Roots)</option>
                        <option value="suffixes">后缀 (Suffixes)</option>
                    </select>
                </div>
                <button class="btn btn-primary" onclick="loadRoots()">📚 加载词根词缀库</button>
                <div id="roots-result" class="roots-grid"></div>
            </div>
        </div>

        <footer>
            Powered by 百炼大模型 (Qwen) · 趣味单词学习系统
        </footer>
    </div>

    <script>
        const API_BASE = '/word/api';

        // Tab 切换
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
                tab.classList.add('active');
                document.getElementById('tab-' + tab.dataset.tab).style.display = 'block';
            });
        });

        // 单词拆解
        async function breakdownWord() {
            const word = document.getElementById('word-input').value.trim();
            if (!word) { alert('请输入单词'); return; }
            
            const btn = document.getElementById('breakdown-btn');
            const result = document.getElementById('breakdown-result');
            
            btn.disabled = true;
            result.innerHTML = '<div class="loading">正在拆解单词...</div>';
            
            try {
                const resp = await fetch(API_BASE + '/breakdown', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({word})
                });
                const data = await resp.json();
                
                if (data.error) {
                    result.innerHTML = `<div class="result error">❌ ${data.error}</div>`;
                } else {
                    renderBreakdown(data, result);
                }
            } catch (e) {
                result.innerHTML = `<div class="result error">❌ 请求失败: ${e.message}</div>`;
            } finally {
                btn.disabled = false;
            }
        }

        // 渲染单词拆解结果
        function renderBreakdown(data, container) {
            let html = `<div class="word-card">
                <div class="word-title">${data.word || ''}</div>
                <div class="phonetic">${data.phonetic || ''} ${data.part_of_speech || ''}</div>
                <p><strong>含义:</strong> ${data.meaning || ''}</p>`;
            
            // 词根词缀拆解
            if (data.breakdown) {
                html += '<div class="breakdown-box">';
                if (data.breakdown.prefix) {
                    html += `<div class="breakdown-part breakdown-prefix">
                        <span class="text">${data.breakdown.prefix.text}</span>
                        <span class="meaning">${data.breakdown.prefix.meaning}</span>
                    </div>`;
                }
                if (data.breakdown.root) {
                    html += `<div class="breakdown-part breakdown-root">
                        <span class="text">${data.breakdown.root.text}</span>
                        <span class="meaning">${data.breakdown.root.meaning}</span>
                    </div>`;
                }
                if (data.breakdown.suffix) {
                    html += `<div class="breakdown-part breakdown-suffix">
                        <span class="text">${data.breakdown.suffix.text}</span>
                        <span class="meaning">${data.breakdown.suffix.meaning}</span>
                    </div>`;
                }
                html += '</div>';
            }
            
            // 词源故事
            if (data.etymology) {
                html += `<div class="memory-tip">
                    <h4>📜 词源故事 (${data.etymology.origin || ''})</h4>
                    <p>${data.etymology.story || ''}</p>
                </div>`;
            }
            
            // 记忆技巧
            if (data.memory_tips && data.memory_tips.length) {
                html += '<div class="memory-tip"><h4>💡 记忆技巧</h4>';
                data.memory_tips.forEach(tip => {
                    html += `<p><strong>${tip.tip}</strong>: ${tip.detail}</p>`;
                });
                html += '</div>';
            }
            
            // 例句
            if (data.examples && data.examples.length) {
                html += '<h4 style="margin: 15px 0 10px;">📝 例句</h4>';
                data.examples.forEach(ex => {
                    html += `<div class="example-box">
                        <div class="sentence">${ex.sentence}</div>
                        <div class="translation">${ex.translation}</div>
                    </div>`;
                });
            }
            
            // 趣味知识
            if (data.fun_fact) {
                html += `<div class="memory-tip" style="background: #e8f5e9; border-left-color: #4caf50;">
                    <h4>🎉 趣味知识</h4>
                    <p>${data.fun_fact}</p>
                </div>`;
            }
            
            html += '</div>';
            container.innerHTML = html;
        }

        // 生成练习题
        async function generateQuiz() {
            const word = document.getElementById('quiz-word').value.trim();
            const difficulty = document.getElementById('quiz-difficulty').value;
            const result = document.getElementById('quiz-result');
            
            result.innerHTML = '<div class="loading">正在生成练习题...</div>';
            
            try {
                const resp = await fetch(API_BASE + '/quiz', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({word, difficulty})
                });
                const data = await resp.json();
                
                if (data.error) {
                    result.innerHTML = `<div class="result error">❌ ${data.error}</div>`;
                } else {
                    renderQuiz(data, result);
                }
            } catch (e) {
                result.innerHTML = `<div class="result error">❌ 请求失败: ${e.message}</div>`;
            }
        }

        // 渲染练习题
        function renderQuiz(data, container) {
            let html = '<div class="result"><h3>🎯 趣味练习</h3>';
            
            if (data.quizzes) {
                data.quizzes.forEach((q, i) => {
                    html += `<div style="margin: 20px 0; padding: 15px; background: white; border-radius: 10px;">
                        <p><strong>第${i+1}题</strong> (${q.type})</p>
                        <p style="margin: 10px 0;">${q.question}</p>`;
                    
                    if (q.options) {
                        Object.entries(q.options).forEach(([key, val]) => {
                            const mark = key === q.answer ? ' ✓' : '';
                            html += `<p style="margin: 5px 0;"><strong>${key}.</strong> ${val}${mark}</p>`;
                        });
                    }
                    
                    if (q.explanation) {
                        html += `<p style="margin-top: 10px; color: #666;">📖 ${q.explanation}</p>`;
                    }
                    html += '</div>';
                });
            }
            
            html += '</div>';
            container.innerHTML = html;
        }

        // 生成记忆故事
        async function generateStory() {
            const wordsText = document.getElementById('story-words').value.trim();
            const words = wordsText.split(/[, \\s]+/).filter(w => w);
            
            if (words.length < 2) { alert('请输入至少2个单词'); return; }
            
            const result = document.getElementById('story-result');
            result.innerHTML = '<div class="loading">正在创作记忆故事...</div>';
            
            try {
                const resp = await fetch(API_BASE + '/story', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({words})
                });
                const data = await resp.json();
                
                if (data.error) {
                    result.innerHTML = `<div class="result error">❌ ${data.error}</div>`;
                } else {
                    renderStory(data, result);
                }
            } catch (e) {
                result.innerHTML = `<div class="result error">❌ 请求失败: ${e.message}</div>`;
            }
        }

        // 渲染故事
        function renderStory(data, container) {
            let html = `<div class="word-card">
                <h3 style="color: #667eea; margin-bottom: 15px;">📖 ${data.title || '记忆故事'}</h3>`;
            
            if (data.scene) {
                html += `<p style="color: #888; margin-bottom: 15px;">🎬 场景: ${data.scene}</p>`;
            }
            
            if (data.story) {
                html += `<div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 15px 0; line-height: 1.8;">
                    ${data.story.replace(/\\*\\*(\\w+)\\*\\*/g, '<strong style="color: #667eea;">$1</strong>')}
                </div>`;
            }
            
            if (data.translation) {
                html += `<p style="color: #666; margin: 15px 0;">${data.translation}</p>`;
            }
            
            if (data.memory_palace) {
                html += `<div class="memory-tip">
                    <h4>🏛️ 记忆宫殿</h4>
                    <p><strong>位置:</strong> ${data.memory_palace.location || ''}</p>
                    <p><strong>路径:</strong> ${data.memory_palace.path || ''}</p>
                </div>`;
            }
            
            html += '</div>';
            container.innerHTML = html;
        }

        // 加载词根词缀库
        async function loadRoots() {
            const category = document.getElementById('roots-category').value;
            const result = document.getElementById('roots-result');
            
            result.innerHTML = '<div class="loading">加载中...</div>';
            
            try {
                const url = API_BASE + '/roots' + (category ? '?category=' + category : '');
                const resp = await fetch(url);
                const data = await resp.json();
                
                if (data.error) {
                    result.innerHTML = `<div class="result error">❌ ${data.error}</div>`;
                    return;
                }
                
                let html = '';
                const items = data.roots || [];
                items.forEach(item => {
                    html += `<div class="root-item">
                        <div class="text">${item.text}</div>
                        <div class="meaning">${item.meaning}</div>
                        <div class="examples">例词: ${(item.examples || []).join(', ')}</div>
                    </div>`;
                });
                
                result.innerHTML = html || '<p>暂无数据</p>';
            } catch (e) {
                result.innerHTML = `<div class="result error">❌ 加载失败: ${e.message}</div>`;
            }
        }

        // 页面加载时预加载词根库
        loadRoots();
    </script>
</body>
</html>"""


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
    return Response.new(body, {
        "status": status,
        "headers": {"Content-Type": "application/json", **cors_headers}
    })


async def on_fetch(request, env):
    """Cloudflare Worker 主入口"""
    api_key = env.API_KEY if hasattr(env, 'API_KEY') else None

    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

    # 处理 CORS preflight
    if request.method == "OPTIONS":
        return Response.new(None, {"status": 204, "headers": cors_headers})

    try:
        url = URL.new(request.url)
        pathname = url.pathname
        path_parts = [p for p in pathname.split("/") if p]

        method = request.method
        content_type = request.headers.get("content-type", "")

        body = None
        if method == "POST" and "application/json" in content_type:
            try:
                body = json.loads(await request.text())
            except Exception:
                pass

        # API 路由: /word/api/*
        if len(path_parts) >= 2 and path_parts[0] == "word" and path_parts[1] == "api":
            if len(path_parts) == 3:
                endpoint = path_parts[2]

                if endpoint == "breakdown" and method == "POST":
                    word = body.get("word", "") if body else ""
                    if not word:
                        return make_response({"error": "word 参数必填"}, 400, cors_headers)
                    result = await breakdown_word(word, api_key)
                    return make_response(result, 200, cors_headers)

                elif endpoint == "quiz" and method == "POST":
                    word = body.get("word", "") if body else ""
                    difficulty = body.get("difficulty") if body else None
                    result = await generate_quiz(word, difficulty, api_key)
                    return make_response(result, 200, cors_headers)

                elif endpoint == "story" and method == "POST":
                    words = body.get("words", []) if body else []
                    if not words:
                        return make_response({"error": "words 参数必填"}, 400, cors_headers)
                    result = await generate_story(words, api_key)
                    return make_response(result, 200, cors_headers)

                elif endpoint == "roots" and method == "GET":
                    # 解析查询参数
                    search = url.search.replace("?", "") if url.search else ""
                    params = {}
                    if search:
                        for pair in search.split("&"):
                            if "=" in pair:
                                k, v = pair.split("=", 1)
                                params[k] = v
                    category = params.get("category")
                    roots = get_roots_library(category)
                    return make_response({"roots": roots if isinstance(roots, list) else [roots]}, 200, cors_headers)

                else:
                    return make_response({"error": f"未知端点: {endpoint}"}, 404, cors_headers)

            elif len(path_parts) == 2:
                return make_response({
                    "name": "Word Learning API",
                    "version": "1.0.0",
                    "endpoints": ["/word/api/breakdown", "/word/api/quiz", "/word/api/story", "/word/api/roots"]
                }, 200, cors_headers)

        # 返回 HTML 页面
        html_content = get_html_page()
        html_headers = {
            "Content-Type": "text/html; charset=utf-8",
            **cors_headers
        }
        return Response.new(html_content, status=200, headers=html_headers)

    except Exception as e:
        return make_response({"error": str(e)}, 500, cors_headers)

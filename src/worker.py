# -*- coding: utf-8 -*-
"""
AI Learning - Cloudflare Worker
提供 REST API 接口，支持句子分析、例句生成、练习题生成
"""

import json
import re
from js import URL, Response, fetch

# Cloudflare Workers 环境下从环境变量获取 API Key
API_KEY = None

# ============ 提示词定义 ============

STRUCTURE_ANALYSIS_PROMPT = """你是一个专业的语言学分析助手，精通英语和汉语的句子结构分析。
任务：分析用户输入的句子，提取其语法结构，并以JSON格式返回。
支持语言：英语 (en) 和 汉语 (zh)
分析维度：句子类型、句子成分、语法结构、时态/语态、关键词汇、结构模式、翻译
返回JSON格式必须包含：language, original, translation, sentence_type, structure_type, components, tense_aspect, key_phrases, structure_pattern, difficulty"""

EXAMPLE_GENERATION_PROMPT = """你是一个语言学习助手，根据给定的句子结构生成同类例句。
任务：基于提供的句子结构，生成多个同类结构的例句。
要求：例句难度应与原句相当，内容实用、贴近生活
返回JSON格式：{"structure_pattern": "...", "examples": [{"sentence": "...", "translation": "...", "components": [{"role": "主语", "text": "..."}], "difficulty": "beginner"}], "learning_tips": "..."}"""

EXERCISE_GENERATION_PROMPT = """你是一个语言教学专家，根据给定的句子结构生成选择题练习。
任务：设计选择题练习题，帮助学习者巩固掌握。
要求：所有题目都是选择题，每题4个选项，只有1个正确答案
返回JSON格式：{"exercises": [{"type": "choice", "question": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."}, "answer": "A", "explanation": "..."}]}"""

# ============ 句型库 ============

COMMON_PATTERNS = {
    "en": [
        {"id": "en_001", "name": "主谓宾结构", "pattern": "[Subject] + [Verb] + [Object]", "example": "I love English.", "level": "beginner"},
        {"id": "en_002", "name": "There be 句型", "pattern": "There is/are + [Noun] + [Place]", "example": "There is a book.", "level": "beginner"},
        {"id": "en_003", "name": "Be动词句型", "pattern": "[Subject] + am/is/are + [Predicative]", "example": "She is a student.", "level": "beginner"},
        {"id": "en_004", "name": "情态动词 can", "pattern": "[Subject] + can + [Verb原形]", "example": "I can swim.", "level": "beginner"},
        {"id": "en_005", "name": "现在进行时", "pattern": "[Subject] + am/is/are + [Verb-ing]", "example": "She is reading.", "level": "beginner"},
        {"id": "en_006", "name": "一般过去时", "pattern": "[Subject] + [Verb-ed] + [Object]", "example": "I visited Beijing.", "level": "beginner"},
        {"id": "en_007", "name": "现在完成时", "pattern": "[Subject] + have/has + [Past Participle]", "example": "I have finished.", "level": "intermediate"},
        {"id": "en_008", "name": "被动语态", "pattern": "[Subject] + am/is/are + [Past Participle]", "example": "English is spoken.", "level": "intermediate"},
        {"id": "en_009", "name": "定语从句", "pattern": "[Noun] + who/that + [Verb]", "example": "The man who is there.", "level": "advanced"},
        {"id": "en_010", "name": "宾语从句", "pattern": "[Subject] + [Verb] + that + [Clause]", "example": "I think that he is right.", "level": "advanced"},
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


async def _call_bailian(prompt: str, system_prompt: str, api_key: str, model: str = "qwen-plus-latest") -> dict:
    """调用百炼 API（使用 Cloudflare Workers fetch API）"""
    # 检查 API Key
    if not api_key:
        return {"error": "API_KEY 未配置，请在 Cloudflare Workers Dashboard 中设置环境变量 API_KEY"}

    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    })

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
    prompt = f"语言: {language}\n句子: {sentence}"
    return await _call_bailian(prompt, STRUCTURE_ANALYSIS_PROMPT, api_key)


async def generate_examples_handler(pattern: str, language: str, count: int, api_key: str) -> dict:
    """生成例句"""
    prompt = f"语言: {language}\n句型模板: {pattern}\n生成例句数量: {count}"
    return await _call_bailian(prompt, EXAMPLE_GENERATION_PROMPT, api_key)


async def generate_exercises_handler(pattern: str, language: str, difficulty: str, api_key: str) -> dict:
    """生成练习题"""
    prompt = f"语言: {language}\n句型模板: {pattern}"
    if difficulty:
        prompt += f"\n难度要求: {difficulty}"
    return await _call_bailian(prompt, EXERCISE_GENERATION_PROMPT, api_key)


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
    global API_KEY
    API_KEY = env.API_KEY if hasattr(env, 'API_KEY') else None

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
                    if not pattern:
                        return make_response({"error": "pattern 参数必填"}, 400, cors_headers)
                    pattern_info = get_pattern_by_id(pattern)
                    if pattern_info:
                        pattern = pattern_info["pattern"]
                        language = pattern_info["id"][:2]
                    result = await generate_examples_handler(pattern, language, count, API_KEY)
                    return make_response(result, 200, cors_headers)

                elif endpoint == "exercises" and method == "POST":
                    pattern = body.get("pattern", "") if body else ""
                    language = body.get("language", "en") if body else "en"
                    difficulty = body.get("difficulty") if body else None
                    if not pattern:
                        return make_response({"error": "pattern 参数必填"}, 400, cors_headers)
                    pattern_info = get_pattern_by_id(pattern)
                    if pattern_info:
                        pattern = pattern_info["pattern"]
                        language = pattern_info["id"][:2]
                    result = await generate_exercises_handler(pattern, language, difficulty, API_KEY)
                    return make_response(result, 200, cors_headers)

                elif endpoint == "patterns" and method == "GET":
                    language = url.searchParams.get("language") if url.searchParams else None
                    level = url.searchParams.get("level") if url.searchParams else None
                    patterns = get_common_patterns(language, level)
                    return make_response({"patterns": patterns}, 200, cors_headers)

                else:
                    return make_response({"error": f"未知端点: {endpoint}"}, 404, cors_headers)

            elif len(path_parts) == 1 and path_parts[0] == "api":
                return make_response({
                    "name": "AI Learning API",
                    "version": "1.0.0",
                    "endpoints": ["/api/analyze", "/api/examples", "/api/exercises", "/api/patterns"]
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
        .result { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px; border-left: 4px solid #667eea; white-space: pre-wrap; font-family: monospace; line-height: 1.6; max-height: 400px; overflow-y: auto; }
        .result.error { border-left-color: #dc3545; background: #fff5f5; }
        .loading { text-align: center; padding: 20px; color: #666; }
        .pattern-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px; margin-top: 15px; }
        .pattern-item { padding: 10px; background: #f0f0f0; border-radius: 5px; font-size: 13px; }
        .pattern-item .name { font-weight: 600; color: #333; }
        .pattern-item .meta { font-size: 11px; color: #666; margin-top: 3px; }
        footer { text-align: center; padding: 20px; color: #888; font-size: 12px; }
        @media (max-width: 600px) { .container { padding: 10px; } header h1 { font-size: 1.5em; } .tabs { gap: 5px; } .tab { padding: 8px 12px; font-size: 12px; } }
    </style>
</head>
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
        </div>

        <div id="tab-analyze" class="tab-content">
            <div class="card">
                <div class="input-group">
                    <label>输入句子</label>
                    <textarea id="analyze-input" placeholder="请输入要分析的英语或汉语句子...">I love learning new languages.</textarea>
                </div>
                <button class="btn btn-primary" id="analyze-btn" onclick="analyzeSentence()">🔍 分析句子</button>
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
                <button class="btn btn-primary" onclick="generateExamples()">✨ 生成例句</button>
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
                <button class="btn btn-primary" onclick="generateExercises()">🎯 生成练习题</button>
                <div id="exercises-result" class="result" style="display:none;"></div>
            </div>
        </div>

        <div id="tab-patterns" class="tab-content" style="display:none;">
            <div class="card">
                <div class="input-group">
                    <label>筛选语言</label>
                    <select id="pattern-lang" onchange="loadPatterns()"><option value="">全部</option><option value="en">English</option><option value="zh">中文</option></select>
                </div>
                <button class="btn btn-primary" onclick="loadPatterns()">📚 加载句型库</button>
                <div id="patterns-result" class="pattern-grid"></div>
            </div>
        </div>

        <footer>
            Powered by 百炼大模型 (Qwen) · 部署于 Cloudflare Workers
        </footer>
    </div>

    <script>
        const API_BASE = '/api';

        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
                tab.classList.add('active');
                document.getElementById('tab-' + tab.dataset.tab).style.display = 'block';
            });
        });

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
                result.textContent = JSON.stringify(data, null, 2);
            } catch (e) {
                result.className = 'result error';
                result.textContent = '❌ 请求失败: ' + e.message;
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
            const result = document.getElementById('examples-result');
            if (!pattern) { alert('请选择句型'); return; }
            result.style.display = 'block';
            result.className = 'result loading';
            result.textContent = '✨ 生成中...';
            try {
                const resp = await fetch(API_BASE + '/examples', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({pattern, language, count})
                });
                const data = await resp.json();
                result.className = 'result';
                result.textContent = JSON.stringify(data, null, 2);
            } catch (e) {
                result.className = 'result error';
                result.textContent = '❌ 错误: ' + e.message;
            }
        }

        async function generateExercises() {
            const pattern = document.getElementById('exercise-pattern').value;
            const language = document.getElementById('exercise-lang').value;
            const result = document.getElementById('exercises-result');
            if (!pattern) { alert('请选择句型'); return; }
            result.style.display = 'block';
            result.className = 'result loading';
            result.textContent = '🎯 生成中...';
            try {
                const resp = await fetch(API_BASE + '/exercises', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({pattern, language})
                });
                const data = await resp.json();
                result.className = 'result';
                result.textContent = JSON.stringify(data, null, 2);
            } catch (e) {
                result.className = 'result error';
                result.textContent = '❌ 错误: ' + e.message;
            }
        }

        async function loadPatterns() {
            const language = document.getElementById('pattern-lang').value;
            const result = document.getElementById('patterns-result');
            result.innerHTML = '<div class="loading">📚 加载中...</div>';
            try {
                const url = API_BASE + '/patterns' + (language ? '?language=' + language : '');
                const resp = await fetch(url);
                const data = await resp.json();
                const patterns = data.patterns || [];
                result.innerHTML = patterns.map(p => `
                    <div class="pattern-item">
                        <div class="name">${p.id} - ${p.name}</div>
                        <div class="meta">${p.level} · ${p.pattern}</div>
                        <div class="meta">例句: ${p.example}</div>
                    </div>
                `).join('');
            } catch (e) {
                result.innerHTML = '<div class="result error">❌ 加载失败: ' + e.message + '</div>';
            }
        }

        loadPatternOptions();
    </script>
</body>
</html>"""

        return Response.new(html_content, {
            "status": 200,
            "headers": {"Content-Type": "text/html; charset=utf-8", **cors_headers}
        })

    except Exception as e:
        return make_response({"error": str(e)}, 500, cors_headers)

# -*- coding: utf-8 -*-
"""
AI Learning - Cloudflare Worker
提供 REST API 接口，支持句子分析、例句生成、练习题生成
"""

import json
import re
from js import URL, Response, fetch, Headers

# Cloudflare Workers 环境下从环境变量获取 API Key
API_KEY = None

# ============ DashScope 配置 ============
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_API_KEY = "sk-9e6be88fab044f719313ce6bba59b759"
# 多模型互备列表（按优先级排序，依次尝试）
DASHSCOPE_MODELS = [
    "qwen3-next-80b-a3b-instruct",
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
要求：例句难度应与原句相当，内容实用、贴近生活
返回JSON格式：{"structure_pattern": "...", "examples": [{"sentence": "...", "translation": "...", "components": [{"role": "主语", "text": "..."}], "difficulty": "beginner"}], "learning_tips": "..."}
重要：只返回JSON，不要包含任何思考过程、分析说明或Markdown标记。不要使用代码块包裹，直接输出纯JSON。"""

EXERCISE_GENERATION_PROMPT = """你是一个语言教学专家，根据给定的句子结构生成选择题练习。
任务：设计选择题练习题，帮助学习者巩固掌握。
要求：所有题目都是选择题，每题4个选项，只有1个正确答案
返回JSON格式：{"exercises": [{"type": "choice", "question": "...", "options": {"A": "...", "B": "...", "C": "...", "D": "..."}, "answer": "A", "explanation": "..."}]}
重要：只返回JSON，不要包含任何思考过程、分析说明或Markdown标记。不要使用代码块包裹，直接输出纯JSON。"""

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


async def _call_bailian(prompt: str, system_prompt: str, api_key: str, model: str = None) -> dict:
    """调用 AI API，支持多模型互备切换（依次尝试，失败自动切换到下一个）"""
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
            "temperature": 0.7
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
    response_headers = Headers.new()
    response_headers.set("Content-Type", "application/json")
    for key, value in cors_headers.items():
        response_headers.set(key, value)
    return Response.new(body, status=status, headers=response_headers)


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

        const ROLE_COLORS = {
            '主语':'subject','Subject':'subject','S':'subject',
            '谓语':'predicate','Predicate':'predicate','谓语动词':'predicate','V':'predicate',
            '表语':'predicative','Predicative':'predicative',
            '宾语':'object','Object':'object','O':'object',
            '定语':'attributive','Attributive':'attributive',
            '状语':'adverbial','Adverbial':'adverbial','Adv':'adverbial',
            '补语':'complement','Complement':'complement',
            '动词':'verb','Verb':'verb',
            '名词':'noun','Noun':'noun',
            情态动词:'verb','情态':'verb',
        };

        function esc(str) {
            return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        }

        function highlightSentence(sentence, components) {
            if (!components || !components.length) return esc(sentence);
            const sorted = components.map(c => ({
                role: c.role || '',
                text: c.text || '',
                idx: sentence.indexOf(c.text || '')
            })).filter(c => c.idx !== -1 && c.text.length > 0)
              .sort((a, b) => a.idx - b.idx || b.text.length - a.text.length);
            if (!sorted.length) return esc(sentence);
            let result = '', pos = 0;
            for (const comp of sorted) {
                if (comp.idx < pos) continue;
                if (comp.idx > pos) result += esc(sentence.substring(pos, comp.idx));
                const cls = ROLE_COLORS[comp.role] || 'default';
                result += '<span class="hl-comp hl-' + cls + '" data-role="' + esc(comp.role) + '">' + esc(comp.text) + '</span>';
                pos = comp.idx + comp.text.length;
            }
            if (pos < sentence.length) result += esc(sentence.substring(pos));
            return result;
        }

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
                if (data.error) {
                    result.innerHTML = '<div class="error-line">❌ ' + data.error + '</div>';
                    return;
                }
                let html = '<div class="pattern-header">📐 结构模式: <code>' + (data.structure_pattern || '') + '</code></div>';
                if (data.examples && data.examples.length) {
                    html += '<div class="examples-list">';
                    data.examples.forEach((ex, i) => {
                        html += '<div class="example-card">';
                        html += '<div class="example-num">#' + (i+1) + '</div>';
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
                result.innerHTML = html;
            } catch (e) {
                result.className = 'result error';
                result.innerHTML = '❌ 错误: ' + e.message;
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
                    html += '<div class="exercise-num">第 ' + (i+1) + ' 题</div>';
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
                result.innerHTML = html;
            } catch (e) {
                result.className = 'result error';
                result.innerHTML = '❌ 错误: ' + e.message;
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

        html_headers = Headers.new()
        html_headers.set("Content-Type", "text/html; charset=utf-8")
        for key, value in cors_headers.items():
            html_headers.set(key, value)
        return Response.new(html_content, status=200, headers=html_headers)

    except Exception as e:
        return make_response({"error": str(e)}, 500, cors_headers)

# -*- coding: utf-8 -*-
"""
AI Learning - 本地开发 API
使用 FastAPI 提供与 Cloudflare Worker 相同的接口，方便本地调试
启动: uvicorn src.api:app --reload --port 8787
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))

from learning_engine import (
    analyze_sentence, generate_examples, generate_exercises,
    get_common_patterns, get_pattern_by_id, COMMON_PATTERNS
)

app = FastAPI(title="AI Learning API", version="1.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 请求模型 ============

class AnalyzeRequest(BaseModel):
    sentence: str
    language: Optional[str] = None

class ExamplesRequest(BaseModel):
    pattern: str
    language: str = "en"
    count: int = 5

class ExercisesRequest(BaseModel):
    pattern: str
    language: str = "en"
    difficulty: Optional[str] = None

# ============ API 端点 ============

@app.get("/api")
def api_info():
    """API 信息"""
    return {
        "name": "AI Learning API",
        "version": "1.0.0",
        "endpoints": ["/api/analyze", "/api/examples", "/api/exercises", "/api/patterns"]
    }

@app.post("/api/analyze")
def api_analyze(req: AnalyzeRequest):
    """分析句子结构"""
    if not req.sentence:
        raise HTTPException(status_code=400, detail="sentence 参数必填")
    try:
        result = analyze_sentence(req.sentence, req.language)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/examples")
def api_examples(req: ExamplesRequest):
    """生成例句"""
    if not req.pattern:
        raise HTTPException(status_code=400, detail="pattern 参数必填")

    # 检查是否是句型 ID
    pattern = req.pattern
    pattern_info = get_pattern_by_id(pattern)
    if pattern_info:
        pattern = pattern_info["pattern"]
        language = pattern_info["id"][:2]
    else:
        language = req.language

    try:
        result = generate_examples(pattern, language, req.count)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/exercises")
def api_exercises(req: ExercisesRequest):
    """生成练习题"""
    if not req.pattern:
        raise HTTPException(status_code=400, detail="pattern 参数必填")

    pattern = req.pattern
    pattern_info = get_pattern_by_id(pattern)
    if pattern_info:
        pattern = pattern_info["pattern"]
        language = pattern_info["id"][:2]
    else:
        language = req.language

    try:
        result = generate_exercises(pattern, language, req.difficulty)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/patterns")
def api_patterns(language: Optional[str] = None, level: Optional[str] = None):
    """获取句型库"""
    patterns = get_common_patterns(language, level)
    return {"patterns": patterns}

# ============ 本地开发服务器 ============

if __name__ == "__main__":
    import uvicorn
    print("🚀 AI Learning API 本地服务器")
    print("📍 http://localhost:8787")
    print("📖 API 文档: http://localhost:8787/docs")
    uvicorn.run(app, host="0.0.0.0", port=8787, reload=True)

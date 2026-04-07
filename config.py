# -*- coding: utf-8 -*-
"""
AI Learning - 百炼大模型配置中心
基于 bailian-ai 项目配置复用
"""

import json
import time
from pathlib import Path

WORKSPACE = Path(r"C:\Users\27977\.qclaw\workspace")

# ============ API 配置 ============
API_KEY = "sk-9e6be88fab044f719313ce6bba59b759"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

TOKENS = {
    "百炼主账号": {
        "api_key": API_KEY,
        "balance": 1_000_000,
        "model": "qwen-plus-latest",
        "type": "free",
    },
}

# ============ 模型配置 ============
# (类型, 路由优先级, 成本系数, 最大上下文)
MODEL_MAP = {
    "qwen-plus-latest":            ("chat",     8,  0.2,   131_072),
    "qwen-turbo-latest":          ("chat",     6,  0.05,  32_768),
    "qwen-turbo":                  ("chat",     5,  0.05,  32_768),
    "qwen-long":                   ("chat",     7,  0.5,   1_000_000),
    "qwen-max-latest":             ("chat",    10,  1.0,   32_768),
    "qwen3.5-flash":              ("chat",     7,  0.05,  131_072),
    "qwen3-8b":                   ("chat",     6,  0.1,   32_768),
    "qwq-plus-latest":            ("reasoning",11,  1.0,  131_072),
    "qwq-plus":                   ("reasoning",10,  1.0,  131_072),
    "qwen-coder-turbo":            ("code",     7,  0.15,  32_768),
    "qwen3-coder-flash":          ("code",     7,  0.1,   131_072),
    "deepseek-v3":                 ("chat",     9,  0.4,   131_072),
    "glm-4.7":                    ("chat",     9,  0.35,  131_072),
    "qwen-vl-plus-latest":         ("vl",       7,  0.3,   32_768),
    "qwen-vl-ocr-latest":         ("vl",       6,  0.2,   32_768),
    "qwen-math-turbo":             ("math",     6,  0.15,  131_072),
}

MODEL_NAMES_ZH = {
    "qwen-plus-latest":           "Qwen Plus 最新（主力）",
    "qwen-turbo-latest":         "Qwen Turbo 最新（快速）",
    "qwen-turbo":                 "Qwen Turbo（快速）",
    "qwen-long":                  "Qwen Long（超长文本）",
    "qwen-max-latest":           "Qwen Max 最新（旗舰）",
    "qwen3.5-flash":             "Qwen3.5 Flash",
    "qwen3-8b":                  "Qwen3 8B",
    "qwq-plus-latest":           "QwQ Plus 最新（推理思考）",
    "qwq-plus":                  "QwQ Plus（推理思考）",
    "qwen-coder-turbo":           "Qwen-Coder Turbo（编程）",
    "qwen3-coder-flash":         "Qwen3-Coder Flash（最新编程）",
    "deepseek-v3":               "DeepSeek V3（对话）",
    "glm-4.7":                   "GLM-4.7（智谱）",
    "qwen-vl-plus-latest":        "Qwen-VL Plus（视觉）",
    "qwen-vl-ocr-latest":        "Qwen-VL OCR（文字识别）",
    "qwen-math-turbo":            "Qwen-Math Turbo（数学）",
}

TASK_ROUTING = {
    "chat": [
        ("qwen-plus-latest", "qwen-turbo-latest", "qwen-turbo"),
        ("qwen-long",),
        ("deepseek-v3", "glm-4.7"),
    ],
    "code": [
        ("qwen-coder-turbo", "qwen3-coder-flash"),
    ],
    "reasoning": [
        ("qwq-plus-latest", "qwq-plus"),
    ],
    "math": [
        ("qwen-math-turbo",),
    ],
    "vl": [
        ("qwen-vl-plus-latest",),
    ],
    "image": [
        ("qwen-plus-latest",),
    ],
}

# ============ Token 管理 ============

class TokenManager:
    def __init__(self, tokens_config: dict):
        self.tokens = tokens_config
        self.log_path = WORKSPACE / "ai-learning" / "usage.json"
        self.usage = self._load_usage()

    def _load_usage(self) -> dict:
        if self.log_path.exists():
            try:
                with open(self.log_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_usage(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(self.usage, f, ensure_ascii=False, indent=2)

    def deduct(self, token_name: str, amount: float):
        if token_name in self.tokens:
            self.tokens[token_name]["balance"] = max(
                0, self.tokens[token_name].get("balance", 0) - amount
            )
        today = time.strftime("%Y-%m-%d")
        if token_name not in self.usage:
            self.usage[token_name] = {"total": 0, "daily": {}, "requests": 0}
        self.usage[token_name]["total"] += amount
        self.usage[token_name]["requests"] += 1
        self.usage[token_name]["daily"][today] = \
            self.usage[token_name]["daily"].get(today, 0) + amount
        self._save_usage()

    def get_best_token(self, model_id: str) -> tuple:
        candidates = []
        for name, cfg in self.tokens.items():
            if cfg.get("balance", 0) > 50:
                candidates.append((name, cfg))
        if not candidates:
            for name, cfg in self.tokens.items():
                candidates.append((name, cfg))
        if not candidates:
            return None, None
        candidates.sort(key=lambda x: (
            0 if x[1].get("type") == "free" else 1,
            -x[1].get("balance", 0)
        ))
        return candidates[0]

    def status(self) -> dict:
        return {
            name: {
                "balance": cfg.get("balance", 0),
                "type": cfg.get("type", "paid"),
                "primary_model": cfg.get("model", "unknown"),
            }
            for name, cfg in self.tokens.items()
        }


def select_model(task_type: str, manager: TokenManager) -> tuple:
    for model_candidates in TASK_ROUTING.get(task_type, TASK_ROUTING["chat"]):
        for model_id in model_candidates:
            if model_id in MODEL_MAP:
                token_name, token_cfg = manager.get_best_token(model_id)
                if token_name:
                    return model_id, token_name, token_cfg["api_key"]
    return None, None, None


def auto_detect_task_type(prompt: str) -> str:
    p = prompt.lower()
    scores = {
        "code":     sum(1 for kw in ["代码","code","编程","python","javascript","java","写函数","debug","git","sql","html","css","def ","import ","函数","脚本"] if kw in p),
        "math":     sum(1 for kw in ["数学","计算","方程","微积分","概率","math","equation","calculus"] if kw in p),
        "reasoning":sum(1 for kw in ["思考","推理","为什么","分析","reason","think","逻辑","深度"] if kw in p),
        "image":    sum(1 for kw in ["画","画图","生成图片","图像","draw","generate image"] if kw in p),
    }
    if   scores["code"]     >= 2: return "code"
    elif scores["math"]     >= 2: return "math"
    elif scores["reasoning"]>= 2: return "reasoning"
    elif scores["image"]    >= 2: return "image"
    elif scores["code"]     >= 1: return "code"
    return "chat"

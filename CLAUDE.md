# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI Learning - 句子结构分析与学习系统，支持英语和汉语句子结构分析、例句生成、练习题生成和 AI 批改。核心调用阿里百炼（Qwen）API。

## 常用命令

```bash
# Cloudflare Workers 部署
wrangler dev                    # 本地开发预览
wrangler deploy                 # 生产部署

# 本地 API 开发服务器
python -m uvicorn src.api:app --reload --port 8787

# Gradio Web 界面
python web.py                  # 端口 7860

# 命令行界面
python cli.py

# 测试版本
python test_web.py             # 端口 7862
```

## 架构

```
src/
  worker.py          - Cloudflare Worker (Python)，内嵌静态 HTML 前端
  api.py             - 本地 FastAPI 开发服务器（接口与 Worker 兼容）

public/             - 静态资源目录（备用）

learning_engine.py  - 核心引擎：AI prompts、API 调用、句型库
web.py              - Gradio Web 界面
cli.py              - 命令行交互界面
config.py           - 百炼 API 配置、Token 管理、模型路由
app.py              - Railway/Render 部署入口
wrangler.toml       - Cloudflare Workers 配置
```

## 核心模块

**learning_engine.py**:
- `analyze_sentence()` - 分析句子结构（自动检测中/英文）
- `generate_examples()` - 基于句型生成例句
- `generate_exercises()` - 生成选择题练习
- `check_answer()` - AI 批改答案
- `get_common_patterns()` - 获取句型库
- `generate_learning_path()` - 生成学习路径

**句型库** 覆盖初高中全部语法点，按年级分级。

## Cloudflare Workers API

Worker 提供 REST API（与本地 `src/api.py` 接口兼容）：

| 端点 | 方法 | 参数 | 说明 |
|------|------|------|------|
| `/api/analyze` | POST | `sentence`, `language` | 分析句子结构 |
| `/api/examples` | POST | `pattern`, `language`, `count` | 生成例句 |
| `/api/exercises` | POST | `pattern`, `language`, `difficulty` | 生成练习题 |
| `/api/patterns` | GET | `language`, `level` | 获取句型库 |

## 环境变量

- `API_KEY` - 百炼 API Key（Cloudflare Dashboard 设置）
- `PORT` - Railway/Render 部署端口（默认 7860）

## 部署

详细部署步骤见 `DEPLOY.md`：
- **Cloudflare Workers** - 免费额度 100k 请求/天，`wrangler deploy`
- **Railway/Render** - 入口 `python app.py`

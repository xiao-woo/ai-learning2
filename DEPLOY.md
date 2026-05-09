# AI Learning 部署指南

## 第一步：上传代码到 GitHub Desktop

### 1.1 打开 GitHub Desktop
- 启动 GitHub Desktop
- 登录你的 GitHub 账号（File → Options → Sign in）

### 1.2 添加仓库
- 点击 **File** → **Add Local Repository**
- 浏览到 `C:\Users\27977\.qclaw\workspace\ai-learning`
- 点击 **Add Repository**

### 1.3 发布到 GitHub
- 点击右上角 **Publish repository**
- 仓库名称：`ai-learning`
- 勾选 **Keep this code private**（可选私有）
- 点击 **Publish repository**

### 1.4 确认上传成功
- 访问 https://github.com/xiao-woo/ai-learning 确认代码已上传

---

## 第二步：部署到 Railway

### 2.1 创建 Railway 账号
1. 访问 https://railway.app
2. 点击 **Login** → 使用 **GitHub 登录**
3. 授权 GitHub 访问

### 2.2 部署项目
1. 点击 **New Project** → **Deploy from GitHub repo**
2. 选择 `xiao-woo/ai-learning` 仓库
3. Railway 会自动检测为 Python 项目

### 2.3 配置环境变量
1. 点击你的项目 → **Variables**
2. 添加环境变量：
   - **Key**: `DASHSCOPE_API_KEY`
   - **Value**: `sk-9e6be88fab044f719313ce6bba59b759`

### 2.4 配置启动命令
1. 点击 **Settings** → **Start Command**
2. 输入：`python app.py`

### 2.5 获取访问地址
- 部署完成后，Railway 会提供一个 `.railway.app` 域名
- 例如：`https://ai-learning.railway.app`

---

## 第三步：部署到 Vercel

### 3.1 安装 Vercel CLI
在终端运行：
```bash
npm install -g vercel
```

### 3.2 登录 Vercel
```bash
vercel login
```

### 3.3 部署
```bash
cd C:\Users\27977\.qclaw\workspace\ai-learning
vercel
```

按照提示操作：
- Set up and deploy? **Y**
- Which scope? 选择你的账号
- Link to existing project? **N**
- Project name? `ai-learning`
- Directory? **.** (当前目录)
- Override settings? **N**

### 3.4 获取访问地址
- 部署完成后会显示 `.vercel.app` 域名

---

## 第四步：部署到 Cloudflare Workers（连接 GitHub）

代码已托管 GitHub，可直接连接实现**推送代码 → 自动部署**。

### 4.1 创建 Cloudflare Workers 项目
1. 访问 https://dash.cloudflare.com
2. 点击 **Workers & Pages** → **Create an application**
3. 选择 **Deploy from GitHub**
4. 授权 GitHub 访问，选择 `xiao-woo/ai-learning` 仓库

### 4.2 配置构建和入口
在创建页面设置：
- **Production branch**: `main`
- **Build command**: （留空，Worker Python 无需构建）
- **Build output directory**: （留空）
- **Entry point**: `src/worker.py`

### 4.3 配置环境变量
进入项目 → **Settings** → **Variables and Secrets** → **Add variable**：
- **Variable name**: `API_KEY`
- **Value**: `sk-9e6be88fab044f719313ce6bba59b759`

### 4.4 部署
点击 **Save and Deploy**。以后每次推送到 `main` 分支，Cloudflare 会自动重新部署。

### 4.5 获取访问地址
部署完成后返回 `.workers.dev` 域名，例如：
`https://ai-learning.xiao-woo.workers.dev`

### 本地开发
```bash
# 克隆仓库后，本地预览
wrangler dev

# 本地 API 服务器（与 Worker 接口兼容）
python -m uvicorn src.api:app --reload --port 8787
```

### Cloudflare 架构
```
src/
  worker.py       # Cloudflare Worker 入口（Python），内嵌 HTML 前端
  api.py          # 本地 FastAPI 开发服务器
wrangler.toml     # Cloudflare 配置
public/          # 静态资源（备用）
```

### 注意事项
- Worker 有 10ms CPU 时间限制，复杂 AI 分析可能超时
- 百炼 API Key 必须通过 Dashboard 环境变量配置，不要硬编码
- 免费版 Workers 每日 100,000 请求限额

---

## 快速对比

| 平台 | 免费额度 | 触发方式 |
|------|---------|------|
| **Cloudflare Workers** | 100k 请求/天 | GitHub push → 自动部署 |
| **Railway** | $5/月 | GitHub push → 自动部署 |
| **Vercel** | 100GB/月 | GitHub push → 自动部署 |
| **Render** | 750小时/月 | GitHub push → 自动部署 |

---

## 常见问题

### Q: Railway 显示部署失败？
A: 检查日志，确保环境变量 `DASHSCOPE_API_KEY` 已添加

### Q: Vercel 部署后无法访问？
A: Vercel 主要面向前端/Serverless，后端持续运行项目建议用 Railway

### Q: 如何更新代码？
A: 代码推送到 GitHub 后，所有连接的平台（Cloudflare/Railway/Vercel/Render）都会自动重新部署。

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `src/worker.py` | Cloudflare Workers 入口 |
| `src/api.py` | 本地 FastAPI 开发服务器 |
| `wrangler.toml` | Cloudflare 配置 |
| `app.py` | Railway/Render 入口 |
| `web.py` | Gradio Web 主程序 |
| `learning_engine.py` | AI 学习引擎 |
| `config.py` | 百炼大模型配置 |
| `requirements.txt` | Python 依赖 |

---

部署完成后，你就可以在任何地方通过浏览器访问 AI Learning 了！🎉

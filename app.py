# -*- coding: utf-8 -*-
"""
AI Learning Web - Railway/Render 部署入口
基于 Gradio 的交互式句子结构学习平台
"""

import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入 web 模块中的 app
import web

# 获取端口（Railway/Render 会设置 PORT 环境变量）
PORT = int(os.environ.get("PORT", 7860))

# 启动应用
if __name__ == "__main__":
    web.app.launch(
        server_name="0.0.0.0",
        server_port=PORT,
        share=False,
        show_error=True
    )

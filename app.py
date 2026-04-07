# -*- coding: utf-8 -*-
"""
AI Learning Web - Render部署入口
基于 Gradio 的交互式句子结构学习平台
"""

import os
import sys

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web import create_ui
import gradio as gr

# 获取端口（Render会设置PORT环境变量）
PORT = int(os.environ.get("PORT", 7860))

# 创建应用
app = create_ui()

# 启动（Render需要0.0.0.0）
if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=PORT,
        share=False,
        show_error=True
    )

# -*- coding: utf-8 -*-
"""
AI Learning - 简化测试版
用于诊断按钮无反应的问题
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from learning_engine import analyze_sentence, generate_examples, get_common_patterns
import gradio as gr

def test_analyze(sentence):
    """测试分析功能"""
    if not sentence:
        return "请输入句子"
    try:
        result = analyze_sentence(sentence)
        return f"分析完成!\n\n类型: {result.get('sentence_type', 'N/A')}\n结构: {result.get('structure_type', 'N/A')}\n模板: {result.get('structure_pattern', 'N/A')}"
    except Exception as e:
        return f"错误: {str(e)}"

def test_examples(pattern, language):
    """测试例句生成"""
    if not pattern:
        return "请输入句型模板"
    try:
        result = generate_examples(pattern, language, 3)
        examples = result.get('examples', [])
        text = f"生成 {len(examples)} 个例句:\n\n"
        for i, ex in enumerate(examples, 1):
            text += f"{i}. {ex.get('sentence', '')}\n   -> {ex.get('translation', '')}\n\n"
        return text
    except Exception as e:
        return f"错误: {str(e)}"

def test_patterns(language):
    """测试句型库"""
    try:
        patterns = get_common_patterns(language)
        text = f"找到 {len(patterns)} 个句型:\n\n"
        for p in patterns[:5]:
            text += f"- {p['id']}: {p['name']}\n"
        return text
    except Exception as e:
        return f"错误: {str(e)}"

# 简化界面
with gr.Blocks(title="AI Learning 测试版") as demo:
    gr.Markdown("# 🤖 AI Learning 测试版")
    
    with gr.Tab("句子分析"):
        with gr.Row():
            sentence_in = gr.Textbox(label="输入句子", placeholder="输入英文或中文句子...")
            analyze_btn = gr.Button("🔍 分析", variant="primary")
        result_out = gr.Textbox(label="结果", lines=5)
        analyze_btn.click(fn=test_analyze, inputs=sentence_in, outputs=result_out)
    
    with gr.Tab("例句生成"):
        with gr.Row():
            pattern_in = gr.Textbox(label="句型模板", placeholder="如: [Subject] + [Verb] + [Object]")
            lang_in = gr.Dropdown(choices=[("English", "en"), ("中文", "zh")], value="en", label="语言")
            example_btn = gr.Button("✨ 生成例句", variant="primary")
        example_out = gr.Textbox(label="例句", lines=8)
        example_btn.click(fn=test_examples, inputs=[pattern_in, lang_in], outputs=example_out)
    
    with gr.Tab("句型库"):
        with gr.Row():
            pat_lang = gr.Dropdown(choices=[("全部", ""), ("English", "en"), ("中文", "zh")], value="", label="语言")
            pat_btn = gr.Button("📚 查看句型", variant="primary")
        pat_out = gr.Textbox(label="句型列表", lines=10)
        pat_btn.click(fn=test_patterns, inputs=pat_lang, outputs=pat_out)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7862, share=False)

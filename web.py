# -*- coding: utf-8 -*-
"""
AI Learning Web - Web界面
基于 Gradio 的交互式句子结构学习平台
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from learning_engine import (
    analyze_sentence, generate_examples, generate_exercises,
    check_answer, get_common_patterns, get_pattern_by_id,
    generate_learning_path, COMMON_PATTERNS
)

import gradio as gr

# ============ 功能函数 ============

def analyze_sentence_ui(sentence):
    """句子分析UI函数"""
    if not sentence or not sentence.strip():
        return "请输入要分析的句子", "", ""
    
    try:
        result = analyze_sentence(sentence.strip())
        
        language = "中文" if result.get('language') == 'zh' else "English"
        
        # 构建翻译显示
        translation_text = result.get('translation', '')
        translation_display = f"\n\n**翻译**: {translation_text}" if translation_text else ""
        
        # 句子成分颜色映射
        color_map = {
            '主语': '#FF6B6B',      # 红色
            '谓语': '#4ECDC4',      # 青色
            '宾语': '#45B7D1',      # 蓝色
            '定语': '#96CEB4',      # 绿色
            '状语': '#FFEAA7',      # 黄色
            '补语': '#DDA0DD',      # 紫色
            '表语': '#F8B500',      # 橙色
            '同位语': '#B0C4DE',    # 浅蓝
            '插入语': '#D3D3D3',    # 灰色
            'Subject': '#FF6B6B',
            'Predicate': '#4ECDC4',
            'Object': '#45B7D1',
            'Attribute': '#96CEB4',
            'Adverbial': '#FFEAA7',
            'Complement': '#DDA0DD',
            'Predicative': '#F8B500',
            'Appositive': '#B0C4DE',
        }
        
        # 构建原句标记（在句子上标注成分）
        original_sentence = result.get('original', sentence)
        components = result.get('components', [])
        
        # 创建带标记的句子
        marked_sentence = original_sentence
        marked_parts = []
        
        if components:
            # 按位置排序成分（从后往前替换，避免位置偏移）
            sorted_components = sorted(components, key=lambda x: len(x.get('text', '')), reverse=True)
            
            for comp in sorted_components:
                text = comp.get('text', '').strip()
                role = comp.get('role', '')
                if text and role:
                    color = color_map.get(role, '#E0E0E0')
                    # 使用下划线+背景色标记
                    marker = f"<mark style='background-color: {color}; padding: 2px 4px; border-radius: 3px; color: #000; font-weight: 500;' title='{role}'>{text}</mark>"
                    marked_sentence = marked_sentence.replace(text, marker, 1)
        
        # 句子可视化（带颜色标注）
        sentence_viz = f"""### 📝 句子成分标注

{marked_sentence}

"""
        
        # 成分图例
        if components:
            legend_text = "**图例**: "
            legend_parts = []
            seen_roles = set()
            for comp in components:
                role = comp.get('role', '')
                if role and role not in seen_roles:
                    color = color_map.get(role, '#E0E0E0')
                    legend_parts.append(f"<span style='background-color: {color}; padding: 2px 6px; border-radius: 4px; color: #000; font-weight: bold;'>{role}</span>")
                    seen_roles.add(role)
            legend_text += " ".join(legend_parts)
        else:
            legend_text = ""
        
        analysis_text = f"""## 📖 句子分析结果

**原句**: {result.get('original', sentence)}{translation_display}

**语言**: {language}

**句子类型**: {result.get('sentence_type', 'N/A')}

**结构类型**: {result.get('structure_type', 'N/A')}

**时态/体貌**: {result.get('tense_aspect', 'N/A')}

**语态/语气**: {result.get('voice_mood', 'N/A')}

**难度**: {result.get('difficulty', 'N/A')}

**句型模板**: 
```
{result.get('structure_pattern', 'N/A')}
```

**补充说明**: {result.get('notes', '无')}

{sentence_viz}{legend_text}
"""
        
        components = result.get('components', [])
        if components:
            # 定义颜色映射
            color_map = {
                '主语': '#FF6B6B',      # 红色
                '谓语': '#4ECDC4',      # 青色
                '宾语': '#45B7D1',      # 蓝色
                '定语': '#96CEB4',      # 绿色
                '状语': '#FFEAA7',      # 黄色
                '补语': '#DDA0DD',      # 紫色
                '表语': '#F8B500',      # 橙色
                '同位语': '#B0C4DE',    # 浅蓝
                '插入语': '#D3D3D3',    # 灰色
                'Subject': '#FF6B6B',
                'Predicate': '#4ECDC4',
                'Object': '#45B7D1',
                'Attribute': '#96CEB4',
                'Adverbial': '#FFEAA7',
                'Complement': '#DDA0DD',
                'Predicative': '#F8B500',
                'Appositive': '#B0C4DE',
            }
            
            comp_text = "### 句子成分\n\n| 成分 | 内容 | 说明 |\n|------|------|------|\n"
            for comp in components:
                role = comp.get('role', '')
                # 获取颜色，默认白色
                color = color_map.get(role, '#FFFFFF')
                # 使用HTML标签添加颜色背景
                colored_role = f"<span style='background-color: {color}; padding: 2px 6px; border-radius: 4px; color: #333; font-weight: bold;'>{role}</span>"
                comp_text += f"| {colored_role} | {comp.get('text', '')} | {comp.get('explanation', '')} |\n"
        else:
            comp_text = ""
        
        # 关键词汇也添加颜色标注
        key_phrases = result.get('key_phrases', [])
        if key_phrases:
            keywords_text = "### 关键词汇\n\n"
            for phrase in key_phrases:
                keywords_text += f"<span style='background-color: #E8F4FD; padding: 2px 6px; border-radius: 4px; color: #0066CC; margin-right: 8px;'>{phrase}</span>"
        else:
            keywords_text = ""
        
        return analysis_text, comp_text, keywords_text
        
    except Exception as e:
        return f"分析出错: {str(e)}", "", ""


def generate_examples_ui(pattern, language, count):
    """生成例句UI函数"""
    if not pattern or not pattern.strip():
        return "请输入句型模板"
    
    pattern_info = get_pattern_by_id(pattern.strip())
    if pattern_info:
        pattern = pattern_info['pattern']
        language = pattern_info['id'][:2]
    
    try:
        result = generate_examples(pattern.strip(), language, count)
        
        text = f"""## ✨ 例句生成

**句型模板**: `{result.get('structure_pattern', pattern)}`

**生成数量**: {len(result.get('examples', []))} 个

---

"""
        
        for i, ex in enumerate(result.get('examples', []), 1):
            text += f"**{i}.** {ex.get('sentence', '')}\n\n"
            if ex.get('translation'):
                text += f"   → {ex['translation']}\n\n"
            if ex.get('context'):
                text += f"   💡 *{ex['context']}*\n\n"
            text += "\n"
        
        if result.get('learning_tips'):
            text += f"---\n\n💡 **学习建议**: {result['learning_tips']}"
        
        return text
        
    except Exception as e:
        return f"生成出错: {str(e)}"


def generate_exercises_ui(pattern, language, difficulty):
    """生成练习题UI函数"""
    if not pattern or not pattern.strip():
        return "请输入句型模板", ""
    
    pattern_info = get_pattern_by_id(pattern.strip())
    if pattern_info:
        pattern = pattern_info['pattern']
        language = pattern_info['id'][:2]
    
    try:
        result = generate_exercises(pattern.strip(), language, difficulty if difficulty else None)
        
        exercises = result.get('exercises', [])
        
        text = f"""## 🎯 练习题

**句型模板**: `{result.get('structure_pattern', pattern)}`

**题目数量**: {len(exercises)} 道

**预计时间**: {result.get('estimated_time', 'N/A')}

---

"""
        
        type_map = {
            'fill_blank': '填空题',
            'error_correction': '改错题',
            'translation': '翻译题',
            'sentence_making': '造句题',
            'choice': '选择题'
        }
        
        for i, ex in enumerate(exercises, 1):
            ex_type = type_map.get(ex.get('type'), ex.get('type', '练习题'))
            text += f"### 第{i}题 [{ex_type}]\n\n"
            text += f"**题目**: {ex.get('question', '')}\n\n"
            if ex.get('hint'):
                text += f"💡 提示: {ex['hint']}\n\n"
            text += f"✅ 答案: ||{ex.get('answer', 'N/A')}||\n\n"
            if ex.get('explanation'):
                text += f"📖 解析: {ex['explanation']}\n\n"
            text += "---\n\n"
        
        qa_list = []
        for ex in exercises:
            qa_list.append({
                'question': ex.get('question', ''),
                'answer': ex.get('answer', ''),
                'type': ex.get('type', ''),
                'hint': ex.get('hint', '')
            })
        
        return text, json.dumps(qa_list, ensure_ascii=False)
        
    except Exception as e:
        return f"生成出错: {str(e)}", ""


def check_answer_ui(question, correct_answer, user_answer, question_type):
    """批改答案UI函数"""
    if not question or not user_answer:
        return "请输入题目和答案"
    
    try:
        result = check_answer(question, correct_answer, user_answer, question_type)
        
        status = "✅ 正确" if result.get('is_correct') else "❌ 有误"
        
        text = f"""## 📝 批改结果

**状态**: {status}

**得分**: {result.get('score', 'N/A')}/100

**你的答案**: {user_answer}

**正确答案**: {correct_answer}

---

"""
        
        if result.get('detailed_feedback'):
            text += f"**评语**: {result['detailed_feedback']}\n\n"
        
        if result.get('errors'):
            text += "### 错误分析\n\n"
            for err in result['errors']:
                text += f"• **{err.get('type', '错误')}**: {err.get('description', '')}\n"
                if err.get('suggestion'):
                    text += f"  - 建议: {err['suggestion']}\n"
            text += "\n"
        
        if result.get('strengths'):
            text += "### 👍 优点\n\n"
            for s in result['strengths']:
                text += f"• {s}\n"
            text += "\n"
        
        if result.get('improvements'):
            text += "### 💡 改进建议\n\n"
            for imp in result['improvements']:
                text += f"• {imp}\n"
            text += "\n"
        
        if result.get('learning_resources'):
            text += "### 📚 相关学习资源\n\n"
            for res in result['learning_resources']:
                text += f"• {res}\n"
        
        return text
        
    except Exception as e:
        return f"批改出错: {str(e)}"


def get_patterns_ui(language, level):
    """获取句型库UI函数"""
    patterns = get_common_patterns(language if language else None, level if level else None)
    
    if not patterns:
        return "没有找到符合条件的句型"
    
    text = f"## 📚 常见句型库 ({len(patterns)} 个)\n\n"
    
    # 按年级分组显示
    grade_groups = {}
    for p in patterns:
        grade = p.get('grade', '其他')
        if grade not in grade_groups:
            grade_groups[grade] = []
        grade_groups[grade].append(p)
    
    # 年级顺序
    grade_order = ['七年级上', '七年级下', '八年级上', '八年级下', '九年级', '高中', '其他']
    
    for grade in sorted(grade_groups.keys(), key=lambda x: (grade_order.index(x) if x in grade_order else 999, x)):
        patterns_in_grade = grade_groups[grade]
        text += f"### 📖 {grade} ({len(patterns_in_grade)}个句型)\n\n"
        
        for p in patterns_in_grade:
            lang_icon = "🇬🇧" if p['id'].startswith('en') else "🇨🇳"
            level_icon = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}.get(p['level'], "⚪")
            level_text = {"beginner": "初级", "intermediate": "中级", "advanced": "高级"}.get(p['level'], p['level'])
            
            text += f"**{lang_icon} {p['name']}** {level_icon}\n\n"
            text += f"- 模板: `{p['pattern']}`\n"
            text += f"- 例句: {p['example']}\n"
            text += f"- 难度: {level_text} ({p['level']})\n\n"
    
    return text


def generate_learning_path_ui(current_level, target_level, language):
    """生成学习路径UI函数"""
    try:
        result = generate_learning_path(current_level, target_level, language)
        
        text = f"""## 🗺️ 个性化学习路径

**当前水平**: {result.get('level', 'N/A')}

---

"""
        
        if result.get('goals'):
            text += "### 🎯 学习目标\n\n"
            for goal in result['goals']:
                text += f"• {goal}\n"
            text += "\n"
        
        if result.get('phases'):
            text += "### 📋 学习阶段\n\n"
            for phase in result['phases']:
                text += f"**{phase.get('phase', '')}**\n\n"
                text += f"- 预计时长: {phase.get('duration', 'N/A')}\n"
                text += f"- 学习重点: {phase.get('focus', 'N/A')}\n"
                if phase.get('patterns'):
                    text += f"- 句型: {', '.join(phase['patterns'][:5])}\n"
                if phase.get('milestones'):
                    text += f"- 里程碑: {', '.join(phase['milestones'])}\n"
                text += "\n"
        
        if result.get('recommendations'):
            text += "### 💡 学习建议\n\n"
            for rec in result['recommendations']:
                text += f"• {rec}\n"
            text += "\n"
        
        if result.get('resources'):
            text += "### 📚 推荐资源\n\n"
            for res in result['resources']:
                text += f"• {res}\n"
        
        return text
        
    except Exception as e:
        return f"生成出错: {str(e)}"


# ============ 构建界面 ============

with gr.Blocks(title="AI Learning - 智能句子结构学习") as app:
    
    gr.Markdown("""
    # 🤖 AI Learning - 智能句子结构学习系统
    
    **支持英语、汉语双语言** · **智能分析** · **个性化练习** · **AI批改指导**
    """)
    
    with gr.Tabs():
        
        # ========== 句子分析 ==========
        with gr.Tab("📖 句子分析"):
            with gr.Row():
                with gr.Column(scale=1):
                    sentence_input = gr.Textbox(
                        label="输入句子",
                        placeholder="请输入要分析的英语或汉语句子...",
                        lines=3
                    )
                    analyze_btn = gr.Button("🔍 分析句子", variant="primary")
                
                with gr.Column(scale=2):
                    analysis_output = gr.Markdown(label="分析结果")
                    components_output = gr.Markdown(label="句子成分")
                    keywords_output = gr.Markdown(label="关键词汇")
            
            analyze_btn.click(
                fn=analyze_sentence_ui,
                inputs=[sentence_input],
                outputs=[analysis_output, components_output, keywords_output]
            )
        
        # ========== 例句生成 ==========
        with gr.Tab("✨ 例句生成"):
            with gr.Row():
                with gr.Column(scale=1):
                    pattern_input = gr.Textbox(
                        label="句型模板或ID",
                        placeholder="如: [Subject] + [Verb] + [Object] 或 en_001",
                        lines=2
                    )
                    lang_dropdown = gr.Dropdown(
                        choices=[("English", "en"), ("中文", "zh")],
                        value="en",
                        label="目标语言"
                    )
                    count_slider = gr.Slider(
                        minimum=3, maximum=10, value=5, step=1,
                        label="生成数量"
                    )
                    examples_btn = gr.Button("✨ 生成例句", variant="primary")
                
                with gr.Column(scale=2):
                    examples_output = gr.Markdown(label="例句")
            
            examples_btn.click(
                fn=generate_examples_ui,
                inputs=[pattern_input, lang_dropdown, count_slider],
                outputs=[examples_output]
            )
        
        # ========== 练习题 ==========
        with gr.Tab("🎯 练习题"):
            with gr.Row():
                with gr.Column(scale=1):
                    ex_pattern_input = gr.Textbox(
                        label="句型模板或ID",
                        placeholder="如: [Subject] + [Verb] + [Object] 或 zh_005",
                        lines=2
                    )
                    ex_lang_dropdown = gr.Dropdown(
                        choices=[("English", "en"), ("中文", "zh")],
                        value="en",
                        label="目标语言"
                    )
                    ex_diff_dropdown = gr.Dropdown(
                        choices=[("全部", ""), ("初级", "beginner"), ("中级", "intermediate"), ("高级", "advanced")],
                        value="",
                        label="难度"
                    )
                    exercises_btn = gr.Button("🎯 生成练习题", variant="primary")
                
                with gr.Column(scale=2):
                    exercises_output = gr.Markdown(label="练习题")
                    exercises_json = gr.Textbox(visible=False)
            
            exercises_btn.click(
                fn=generate_exercises_ui,
                inputs=[ex_pattern_input, ex_lang_dropdown, ex_diff_dropdown],
                outputs=[exercises_output, exercises_json]
            )
        
        # ========== 智能批改 ==========
        with gr.Tab("📝 智能批改"):
            with gr.Row():
                with gr.Column(scale=1):
                    check_question = gr.Textbox(
                        label="题目",
                        placeholder="输入题目内容...",
                        lines=2
                    )
                    check_answer_text = gr.Textbox(
                        label="正确答案",
                        placeholder="输入正确答案...",
                        lines=2
                    )
                    check_user_answer = gr.Textbox(
                        label="你的答案",
                        placeholder="输入你的答案...",
                        lines=2
                    )
                    check_type = gr.Dropdown(
                        choices=[("填空题", "fill_blank"), ("改错题", "error_correction"), 
                                ("翻译题", "translation"), ("造句题", "sentence_making"), ("选择题", "choice")],
                        value="fill_blank",
                        label="题目类型"
                    )
                    check_btn = gr.Button("📝 提交批改", variant="primary")
                
                with gr.Column(scale=2):
                    check_output = gr.Markdown(label="批改结果")
            
            check_btn.click(
                fn=check_answer_ui,
                inputs=[check_question, check_answer_text, check_user_answer, check_type],
                outputs=[check_output]
            )
        
        # ========== 句型库 ==========
        with gr.Tab("📚 句型库"):
            with gr.Row():
                with gr.Column(scale=1):
                    pat_lang_dropdown = gr.Dropdown(
                        choices=[("全部", ""), ("English", "en"), ("中文", "zh")],
                        value="",
                        label="语言筛选"
                    )
                    pat_level_dropdown = gr.Dropdown(
                        choices=[("全部", ""), ("初级", "beginner"), ("中级", "intermediate"), ("高级", "advanced")],
                        value="",
                        label="难度筛选"
                    )
                    pat_btn = gr.Button("📚 查看句型", variant="primary")
                
                with gr.Column(scale=2):
                    pat_output = gr.Markdown(label="句型列表")
            
            pat_btn.click(
                fn=get_patterns_ui,
                inputs=[pat_lang_dropdown, pat_level_dropdown],
                outputs=[pat_output]
            )
        
        # ========== 学习路径 ==========
        with gr.Tab("🗺️ 学习路径"):
            with gr.Row():
                with gr.Column(scale=1):
                    path_current = gr.Dropdown(
                        choices=[("初级", "beginner"), ("中级", "intermediate"), ("高级", "advanced")],
                        value="beginner",
                        label="当前水平"
                    )
                    path_target = gr.Dropdown(
                        choices=[("中级", "intermediate"), ("高级", "advanced"), ("精通", "master")],
                        value="intermediate",
                        label="目标水平"
                    )
                    path_lang = gr.Dropdown(
                        choices=[("English", "en"), ("中文", "zh")],
                        value="en",
                        label="目标语言"
                    )
                    path_btn = gr.Button("🗺️ 生成学习路径", variant="primary")
                
                with gr.Column(scale=2):
                    path_output = gr.Markdown(label="学习路径")
            
            path_btn.click(
                fn=generate_learning_path_ui,
                inputs=[path_current, path_target, path_lang],
                outputs=[path_output]
            )
    
    gr.Markdown("""
    ---
    
    💡 **使用提示**:
    - 输入任意英语或汉语句子即可自动分析其结构
    - 可以使用句型ID（如 en_001, zh_005）快速选择常见句型
    - 系统会自动根据内容难度调整练习题目
    
    Powered by 百炼大模型 (Qwen)
    """)


if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)

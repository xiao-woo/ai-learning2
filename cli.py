# -*- coding: utf-8 -*-
"""
AI Learning CLI - 交互式句子结构学习工具
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from learning_engine import (
    analyze_sentence, generate_examples, generate_exercises,
    check_answer, get_common_patterns, get_pattern_by_id,
    generate_learning_path
)
from config import TokenManager, TOKENS

# 兼容 Windows
try:
    import termcolor
    TERMCOLOR_OK = True
except ImportError:
    TERMCOLOR_OK = False


def c(text, color=None):
    """彩色输出"""
    if not TERMCOLOR_OK or not sys.stdout.isatty():
        return text
    if color:
        try:
            from termcolor import colored
            return colored(text, color)
        except Exception:
            return text
    return text


def print_banner():
    banner = f"""
{c('╔═══════════════════════════════════════════════════════╗', 'cyan')}
{c('║     🤖 AI Learning - 智能句子结构学习系统              ║', 'cyan')}
{c('║     支持英语、汉语双语言 · 智能分析 · 个性化练习        ║', 'cyan')}
╚═══════════════════════════════════════════════════════╝

{c('📚 功能菜单:', 'yellow')}
  {c('1', 'green')}. 分析句子结构 - 输入任意句子，AI分析其语法结构
  {c('2', 'green')}. 浏览句型库 - 查看常见句型，选择练习
  {c('3', 'green')}. 生成例句 - 基于句型生成同类例句
  {c('4', 'green')}. 生成练习题 - 针对句型生成练习题
  {c('5', 'green')}. 开始练习 - 选择句型进行练习
  {c('6', 'green')}. 学习路径规划 - 制定个性化学习计划
  
{c('⚡ 快捷命令:', 'yellow')}
  {c('/analyze <句子>', 'cyan')} - 快速分析句子
  {c('/examples <句型ID>', 'cyan')} - 快速生成例句
  {c('/practice <句型ID>', 'cyan')} - 快速开始练习
  {c('/patterns [en/zh]', 'cyan')} - 查看句型库
  {c('/lang [en/zh]', 'cyan')} - 切换默认语言
  {c('/exit', 'red')} - 退出程序

{c('💡 提示: 直接输入句子也可以自动分析', 'dim')}
"""
    print(banner)


# ============ 功能实现 ============

def do_analyze():
    """分析句子结构"""
    print(c("\n📖 句子结构分析", "cyan"))
    print(c("-" * 40, "dim"))
    
    sentence = input(c("请输入要分析的句子: ", "yellow")).strip()
    if not sentence:
        print(c("⚠️ 句子不能为空", "red"))
        return
    
    print(c("\n🔍 正在分析...", "blue"))
    
    try:
        result = analyze_sentence(sentence)
        
        print(c(f"\n✅ 分析完成", "green"))
        print(c(f"\n原句: {result.get('original', sentence)}", "white"))
        print(c(f"语言: {'中文' if result.get('language') == 'zh' else 'English'}", "dim"))
        print(c(f"句子类型: {result.get('sentence_type', 'N/A')}", "yellow"))
        print(c(f"结构类型: {result.get('structure_type', 'N/A')}", "yellow"))
        
        if result.get('components'):
            print(c("\n句子成分:", "cyan"))
            for comp in result['components']:
                print(f"  • {c(comp.get('role', ''), 'green')}: {comp.get('text', '')}")
                if comp.get('explanation'):
                    print(f"    {c(comp['explanation'], 'dim')}")
        
        if result.get('tense_aspect'):
            print(c(f"\n时态/体貌: {result['tense_aspect']}", "magenta"))
        
        if result.get('structure_pattern'):
            print(c(f"\n句型模板: {result['structure_pattern']}", "cyan"))
        
        if result.get('difficulty'):
            difficulty_map = {
                'beginner': '初级',
                'intermediate': '中级', 
                'advanced': '高级'
            }
            diff = difficulty_map.get(result['difficulty'], result['difficulty'])
            print(c(f"难度: {diff}", "yellow"))
        
        if result.get('notes'):
            print(c(f"\n补充说明: {result['notes']}", "dim"))
        
        # 询问是否生成例句
        choice = input(c("\n是否基于此结构生成例句? (y/n): ", "yellow")).strip().lower()
        if choice in ('y', 'yes', '是'):
            do_generate_examples(result.get('structure_pattern', ''), result.get('language', 'en'))
            
    except Exception as e:
        print(c(f"\n❌ 分析失败: {e}", "red"))


def do_browse_patterns():
    """浏览句型库"""
    print(c("\n📚 常见句型库", "cyan"))
    print(c("-" * 40, "dim"))
    
    print(c("\n选择语言:", "yellow"))
    print(f"  {c('1', 'green')}. 英语 (English)")
    print(f"  {c('2', 'green')}. 汉语 (中文)")
    print(f"  {c('3', 'green')}. 全部显示")
    
    choice = input(c("\n请选择 (1-3): ", "yellow")).strip()
    
    lang_map = {'1': 'en', '2': 'zh', '3': None}
    language = lang_map.get(choice)
    
    patterns = get_common_patterns(language)
    
    if not patterns:
        print(c("\n⚠️ 没有找到句型", "red"))
        return
    
    print(c(f"\n找到 {len(patterns)} 个句型:\n", "green"))
    
    for i, p in enumerate(patterns, 1):
        lang_icon = "🇬🇧" if p['id'].startswith('en') else "🇨🇳"
        level_icon = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}.get(p['level'], "⚪")
        print(f"{i:2d}. {lang_icon} {level_icon} {c(p['name'], 'cyan')} [{p['id']}]")
        print(f"    模板: {p['pattern']}")
        print(f"    例句: {p['example']}")
        print()
    
    # 选择句型进行练习
    choice = input(c("输入句型编号进行练习 (或回车跳过): ", "yellow")).strip()
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(patterns):
            do_practice_pattern(patterns[idx])


def do_generate_examples(pattern: str = None, language: str = None):
    """生成例句"""
    if not pattern:
        print(c("\n✨ 生成例句", "cyan"))
        print(c("-" * 40, "dim"))
        
        pattern = input(c("请输入句型模板 (或输入句型ID): ", "yellow")).strip()
        
        # 检查是否是句型ID
        pattern_info = get_pattern_by_id(pattern)
        if pattern_info:
            pattern = pattern_info['pattern']
            language = pattern_info['id'][:2]
            print(c(f"找到句型: {pattern_info['name']}", "green"))
        
        if not language:
            lang = input(c("目标语言 (en/zh): ", "yellow")).strip()
            language = 'zh' if lang in ('zh', '中文', '汉语', 'chinese') else 'en'
    
    print(c(f"\n📝 正在生成例句...", "blue"))
    
    try:
        result = generate_examples(pattern, language)
        
        print(c(f"\n✅ 生成完成", "green"))
        print(c(f"\n句型模板: {result.get('structure_pattern', pattern)}", "cyan"))
        
        examples = result.get('examples', [])
        print(c(f"\n共生成 {len(examples)} 个例句:\n", "yellow"))
        
        for i, ex in enumerate(examples, 1):
            print(f"{i}. {c(ex.get('sentence', ''), 'white')}")
            if ex.get('translation'):
                print(f"   {c('→ ' + ex['translation'], 'dim')}")
            if ex.get('context'):
                print(f"   {c('💡 ' + ex['context'], 'green')}")
            print()
        
        if result.get('learning_tips'):
            print(c(f"\n💡 学习建议: {result['learning_tips']}", "green"))
            
    except Exception as e:
        print(c(f"\n❌ 生成失败: {e}", "red"))


def do_generate_exercises():
    """生成练习题"""
    print(c("\n🎯 生成练习题", "cyan"))
    print(c("-" * 40, "dim"))
    
    pattern = input(c("请输入句型模板 (或输入句型ID): ", "yellow")).strip()
    
    # 检查是否是句型ID
    pattern_info = get_pattern_by_id(pattern)
    if pattern_info:
        pattern = pattern_info['pattern']
        language = pattern_info['id'][:2]
        print(c(f"找到句型: {pattern_info['name']}", "green"))
    else:
        lang = input(c("目标语言 (en/zh): ", "yellow")).strip()
        language = 'zh' if lang in ('zh', '中文', '汉语', 'chinese') else 'en'
    
    difficulty = input(c("难度 (beginner/intermediate/advanced，回车自动): ", "yellow")).strip()
    if difficulty not in ('beginner', 'intermediate', 'advanced'):
        difficulty = None
    
    print(c(f"\n📝 正在生成练习题...", "blue"))
    
    try:
        result = generate_exercises(pattern, language, difficulty)
        
        print(c(f"\n✅ 生成完成", "green"))
        print(c(f"句型模板: {result.get('structure_pattern', pattern)}", "cyan"))
        print(c(f"题目数量: {result.get('total_count', 0)}", "yellow"))
        print(c(f"预计时间: {result.get('estimated_time', 'N/A')}", "dim"))
        
        exercises = result.get('exercises', [])
        print(c(f"\n练习题:\n", "cyan"))
        
        for i, ex in enumerate(exercises, 1):
            type_map = {
                'fill_blank': '填空题',
                'error_correction': '改错题',
                'translation': '翻译题',
                'sentence_making': '造句题',
                'choice': '选择题'
            }
            ex_type = type_map.get(ex.get('type'), ex.get('type', '练习题'))
            print(f"\n{c(f'第{i}题 [{ex_type}]', 'yellow')}")
            print(f"题目: {ex.get('question', '')}")
            if ex.get('hint'):
                print(f"{c('提示:', 'dim')} {ex['hint']}")
            print()
        
        # 询问是否开始练习
        choice = input(c("是否开始练习这些题目? (y/n): ", "yellow")).strip().lower()
        if choice in ('y', 'yes', '是'):
            do_practice_exercises(exercises)
            
    except Exception as e:
        print(c(f"\n❌ 生成失败: {e}", "red"))


def do_practice_pattern(pattern_info: dict = None):
    """针对特定句型练习"""
    if not pattern_info:
        print(c("\n🎯 开始练习", "cyan"))
        print(c("-" * 40, "dim"))
        
        pattern_id = input(c("请输入句型ID (如 en_001): ", "yellow")).strip()
        pattern_info = get_pattern_by_id(pattern_id)
        
        if not pattern_info:
            print(c(f"\n⚠️ 未找到句型: {pattern_id}", "red"))
            return
    
    print(c(f"\n📖 当前句型: {pattern_info['name']}", "cyan"))
    print(f"模板: {pattern_info['pattern']}")
    print(f"例句: {pattern_info['example']}")
    
    # 生成练习题
    print(c(f"\n📝 正在生成练习题...", "blue"))
    
    try:
        exercises_result = generate_exercises(
            pattern_info['pattern'], 
            pattern_info['id'][:2],
            pattern_info.get('level')
        )
        exercises = exercises_result.get('exercises', [])
        
        if exercises:
            do_practice_exercises(exercises)
        else:
            print(c("\n⚠️ 未能生成练习题", "red"))
            
    except Exception as e:
        print(c(f"\n❌ 练习生成失败: {e}", "red"))


def do_practice_exercises(exercises: list):
    """练习题答题"""
    print(c(f"\n📝 开始答题 (共{len(exercises)}题)", "cyan"))
    print(c("-" * 40, "dim"))
    
    correct_count = 0
    results = []
    
    for i, ex in enumerate(exercises, 1):
        print(c(f"\n{'='*40}", "dim"))
        type_map = {
            'fill_blank': '填空题',
            'error_correction': '改错题',
            'translation': '翻译题',
            'sentence_making': '造句题',
            'choice': '选择题'
        }
        ex_type = type_map.get(ex.get('type'), ex.get('type', '练习题'))
        
        print(f"{c(f'第{i}题', 'yellow')} [{ex_type}] 难度: {ex.get('difficulty', 'N/A')}")
        print(f"\n题目: {ex.get('question', '')}")
        
        if ex.get('hint'):
            print(f"{c('💡 提示:', 'green')} {ex['hint']}")
        
        # 获取用户答案
        user_answer = input(c("\n你的答案: ", "cyan")).strip()
        
        if not user_answer:
            print(c("⏭️  跳过本题", "dim"))
            continue
        
        # 批改
        print(c("\n🔍 正在批改...", "blue"))
        
        try:
            correction = check_answer(
                ex.get('question', ''),
                ex.get('answer', ''),
                user_answer,
                ex.get('type')
            )
            
            is_correct = correction.get('is_correct', False)
            if is_correct:
                correct_count += 1
                print(c("\n✅ 回答正确!", "green"))
            else:
                print(c("\n❌ 回答有误", "red"))
            
            print(f"正确答案: {c(ex.get('answer', ''), 'cyan')}")
            
            if correction.get('detailed_feedback'):
                print(f"\n{c('评语:', 'yellow')} {correction['detailed_feedback']}")
            
            if correction.get('errors'):
                print(c("\n错误分析:", "red"))
                for err in correction['errors']:
                    print(f"  • {err.get('type', '')}: {err.get('description', '')}")
                    if err.get('suggestion'):
                        print(f"    建议: {err['suggestion']}")
            
            if correction.get('improvements'):
                print(c("\n改进建议:", "yellow"))
                for imp in correction['improvements']:
                    print(f"  • {imp}")
            
            results.append({
                'question': ex.get('question'),
                'correct': is_correct,
                'score': correction.get('score', 0)
            })
            
        except Exception as e:
            print(c(f"\n⚠️ 批改出错: {e}", "red"))
            # 简单对比
            if user_answer.lower().strip() == ex.get('answer', '').lower().strip():
                print(c("✅ 回答正确! (简单匹配)", "green"))
                correct_count += 1
            else:
                print(c("❌ 回答有误", "red"))
                print(f"正确答案: {c(ex.get('answer', ''), 'cyan')}")
            
            if ex.get('explanation'):
                print(f"\n{c('解析:', 'dim')} {ex['explanation']}")
    
    # 练习总结
    print(c(f"\n{'='*40}", "dim"))
    print(c("📊 练习总结", "cyan"))
    print(f"总题数: {len(exercises)}")
    print(f"正确数: {c(correct_count, 'green')}")
    print(f"正确率: {c(f'{correct_count/len(exercises)*100:.1f}%', 'yellow')}")
    
    if correct_count == len(exercises):
        print(c("\n🎉 完美! 全部答对!", "green"))
    elif correct_count >= len(exercises) * 0.8:
        print(c("\n👍 很棒! 继续保持!", "green"))
    elif correct_count >= len(exercises) * 0.6:
        print(c("\n💪 不错! 还有进步空间", "yellow"))
    else:
        print(c("\n📚 建议多复习相关句型", "red"))


def do_learning_path():
    """学习路径规划"""
    print(c("\n🗺️  学习路径规划", "cyan"))
    print(c("-" * 40, "dim"))
    
    print(c("\n选择目标语言:", "yellow"))
    print(f"  {c('1', 'green')}. 英语 (English)")
    print(f"  {c('2', 'green')}. 汉语 (中文)")
    
    lang_choice = input(c("请选择 (1-2): ", "yellow")).strip()
    language = 'en' if lang_choice == '1' else 'zh'
    
    print(c("\n选择当前水平:", "yellow"))
    print(f"  {c('1', 'green')}. 初级 (Beginner)")
    print(f"  {c('2', 'green')}. 中级 (Intermediate)")
    print(f"  {c('3', 'green')}. 高级 (Advanced)")
    
    level_choice = input(c("请选择 (1-3): ", "yellow")).strip()
    level_map = {'1': 'beginner', '2': 'intermediate', '3': 'advanced'}
    current_level = level_map.get(level_choice, 'beginner')
    
    print(c("\n选择目标水平:", "yellow"))
    print(f"  {c('1', 'green')}. 中级 (Intermediate)")
    print(f"  {c('2', 'green')}. 高级 (Advanced)")
    print(f"  {c('3', 'green')}. 精通 (Master)")
    
    target_choice = input(c("请选择 (1-3): ", "yellow")).strip()
    target_map = {'1': 'intermediate', '2': 'advanced', '3': 'master'}
    target_level = target_map.get(target_choice, 'intermediate')
    
    print(c(f"\n📝 正在生成学习路径...", "blue"))
    
    try:
        result = generate_learning_path(current_level, target_level, language)
        
        print(c(f"\n✅ 学习路径已生成", "green"))
        print(c(f"\n当前水平评估: {result.get('level', 'N/A')}", "cyan"))
        
        if result.get('goals'):
            print(c("\n学习目标:", "yellow"))
            for goal in result['goals']:
                print(f"  • {goal}")
        
        if result.get('phases'):
            print(c("\n学习阶段:", "cyan"))
            for phase in result['phases']:
                print(c(f"\n📌 {phase.get('phase', '')}", "green"))
                print(f"   预计时长: {phase.get('duration', 'N/A')}")
                print(f"   学习重点: {phase.get('focus', 'N/A')}")
                if phase.get('patterns'):
                    print(f"   句型: {', '.join(phase['patterns'][:3])}...")
        
        if result.get('recommendations'):
            print(c("\n学习建议:", "yellow"))
            for rec in result['recommendations']:
                print(f"  • {rec}")
        
        if result.get('resources'):
            print(c("\n推荐资源:", "dim"))
            for res in result['resources']:
                print(f"  • {res}")
                
    except Exception as e:
        print(c(f"\n❌ 生成失败: {e}", "red"))


# ============ 快捷命令处理 ============

def handle_quick_command(cmd: str, args: str):
    """处理快捷命令"""
    if cmd == '/analyze':
        if args:
            print(c(f"\n🔍 分析句子: {args}", "cyan"))
            try:
                result = analyze_sentence(args)
                print(c(f"\n✅ 分析完成", "green"))
                print(f"句子类型: {result.get('sentence_type', 'N/A')}")
                print(f"结构类型: {result.get('structure_type', 'N/A')}")
                if result.get('structure_pattern'):
                    print(f"句型模板: {result['structure_pattern']}")
            except Exception as e:
                print(c(f"❌ 分析失败: {e}", "red"))
        else:
            do_analyze()
    
    elif cmd == '/examples':
        if args:
            do_generate_examples(args)
        else:
            do_generate_examples()
    
    elif cmd == '/practice':
        if args:
            pattern_info = get_pattern_by_id(args)
            if pattern_info:
                do_practice_pattern(pattern_info)
            else:
                print(c(f"⚠️ 未找到句型: {args}", "red"))
        else:
            do_practice_pattern()
    
    elif cmd == '/patterns':
        lang = args.strip() if args else None
        patterns = get_common_patterns(lang)
        print(c(f"\n📚 句型库 ({len(patterns)} 个)", "cyan"))
        for p in patterns[:10]:
            lang_icon = "🇬🇧" if p['id'].startswith('en') else "🇨🇳"
            print(f"  {lang_icon} {p['id']}: {p['name']} - {p['pattern']}")
        if len(patterns) > 10:
            print(c(f"  ... 还有 {len(patterns)-10} 个句型", "dim"))
    
    elif cmd == '/lang':
        print(c("\n🌐 语言设置功能开发中...", "yellow"))
    
    else:
        print(c(f"⚠️ 未知命令: {cmd}", "red"))


# ============ 主循环 ============

def main():
    os.system("")  # 启用 ANSI 颜色（Windows）
    
    print_banner()
    
    while True:
        try:
            user_input = input(c("\n▌ 请选择功能 (1-6) 或输入命令: ", "cyan")).strip()
            
            if not user_input:
                continue
            
            # 检查是否是快捷命令
            if user_input.startswith('/'):
                parts = user_input.split(' ', 1)
                cmd = parts[0]
                args = parts[1] if len(parts) > 1 else ''
                
                if cmd in ('/exit', '/quit', '/q'):
                    print(c("\n👋 再见! 继续加油学习!\n", "green"))
                    break
                
                handle_quick_command(cmd, args)
                continue
            
            # 数字菜单选择
            if user_input == '1':
                do_analyze()
            elif user_input == '2':
                do_browse_patterns()
            elif user_input == '3':
                do_generate_examples()
            elif user_input == '4':
                do_generate_exercises()
            elif user_input == '5':
                do_practice_pattern()
            elif user_input == '6':
                do_learning_path()
            else:
                # 默认当作句子分析
                print(c(f"\n🔍 自动分析句子: {user_input}", "cyan"))
                try:
                    result = analyze_sentence(user_input)
                    print(c(f"\n✅ 分析完成", "green"))
                    print(f"句子类型: {c(result.get('sentence_type', 'N/A'), 'yellow')}")
                    print(f"结构类型: {c(result.get('structure_type', 'N/A'), 'yellow')}")
                    if result.get('structure_pattern'):
                        print(f"句型模板: {c(result['structure_pattern'], 'cyan')}")
                    if result.get('components'):
                        print(c("\n句子成分:", "cyan"))
                        for comp in result['components'][:3]:
                            print(f"  • {comp.get('role', '')}: {comp.get('text', '')}")
                except Exception as e:
                    print(c(f"❌ 分析失败: {e}", "red"))
                    
        except KeyboardInterrupt:
            print(c("\n\n👋 再见!\n", "yellow"))
            break
        except EOFError:
            break
        except Exception as e:
            print(c(f"\n⚠️ 错误: {e}\n", "red"))


if __name__ == "__main__":
    main()

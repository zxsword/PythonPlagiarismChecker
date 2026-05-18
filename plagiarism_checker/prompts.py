# -*- coding: utf-8 -*-
"""
Prompt 集中管理模块
将所有发送给大模型的指令模板统一放在这里，避免同一段文案在 grader.py 和 dialogs.py 中
重复出现、各自演变不一致的问题。
"""

# 本地模型允许更长的输出（建议含代码示例时需要更多 token）
MAX_TOKENS_VERBOSE = 1024
MAX_TOKENS_BRIEF   = 256


def build_grading_prompt(exercise_text: str, require_suggestions: bool,
                         source_code: str, verbose: bool = False) -> str:
    """
    构建批改作业的 Prompt。

    Args:
        exercise_text:       教师填写的评分细则，为空则不附加。
        require_suggestions: True 时要求 AI 给出具体修改建议；False 时只需指出错误。
        source_code:         学生提交的源代码原文。
        verbose:             True 时使用更详细的建议模板（适合本地模型，max_tokens 需配合
                             使用 MAX_TOKENS_VERBOSE）；False 时使用简洁模板（适合云端模型）。

    Returns:
        完整的 Prompt 字符串，已内嵌带行号的源代码。
    """
    # 为源代码添加行号，方便模型精确定位错误
    numbered = "\n".join(f"{i+1} | {line}" for i, line in enumerate(source_code.split('\n')))

    prompt = "你是一个负责给Python初学者批改作业的严格老师。满分100分。\n"
    if exercise_text:
        prompt += f"【评分细则】：\n{exercise_text}\n请严格按照细则审查并扣分。\n"

    prompt += "\n为了保持报告清晰，你【必须且只能】按以下固定模板输出，不要说任何废话客套话：\n"
    prompt += "【最终评分】: [填入0-100的纯数字]分\n"
    prompt += "【扣分明细】:\n"

    if require_suggestions:
        if verbose:
            # 本地模型：要求给出详细建议和代码示例，放宽字数
            prompt += "- 第[X]行：[指出错误] -> [给出详细的修改建议和代码示例] (扣[Y]分)\n"
            prompt += "【总体评价】:\n[一段100字以内的精炼总结]\n"
        else:
            # 云端模型：简洁建议即可，控制输出长度
            prompt += "- 第[X]行：[指出错误] -> [给出修改建议] (扣[Y]分)\n"
            prompt += "【总体评价】:\n[一段50字以内的精炼总结]\n"
    else:
        prompt += "- 第[X]行：[一句话指出错误] (扣[Y]分)\n"
        prompt += "【总体评价】:\n[一句10字以内的简短总结]\n"

    prompt += f"\n带行号的代码如下：\n```python\n{numbered}\n```"
    return prompt


def build_judgement_prompt(code_a: str, code_b: str, name_a: str, name_b: str) -> str:
    """
    构建深度查重审判的 Prompt。

    Args:
        code_a / code_b: 两份待比对的源代码原文。
        name_a / name_b: 对应的文件名，用于在报告中标注来源。

    Returns:
        完整的 Prompt 字符串。
    """
    return (
        f'你是一个资深的计算机科学教授和极具洞察力的代码查重专家。\n'
        f'请对以下两份初学者的 Python 代码进行深度对比分析，判断它们是否存在互相抄袭的行为。\n'
        f'请重点分析并分条指出：\n'
        f'1. 核心逻辑、算法流程以及特殊数值是否高度一致？\n'
        f'2. 是否存在为了掩人耳目而故意修改变量名、调换无关语句顺序、增删无用代码或注释的“洗稿”行为？\n'
        f'3. 给出你的最终鉴定结论（例如：高度疑似抄袭 / 仅仅是思路相似的独立完成）。\n\n'
        f'【代码 A ({name_a})】：\n```python\n{code_a}\n```\n\n'
        f'【代码 B ({name_b})】：\n```python\n{code_b}\n```'
    )

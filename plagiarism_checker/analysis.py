# -*- coding: utf-8 -*-
"""
核心分析模块

这个文件包含了所有与代码分析相关的核心逻辑，独立于用户界面(UI)。
主要功能包括：
1. 标准化Python代码（去除注释、空格等干扰因素）。
2. 计算文件之间的相似度并找出可疑的文件对。
"""

import ast  # Abstract Syntax Tree, 用于将代码解析成语法树结构
import re  # Regular Expressions, 用于文本的模式匹配（主要用于后备的标准化方法）
import difflib  # 用于比较序列（比如文本行）的差异
from itertools import combinations  # 用于生成所有可能的文件组合

def normalize_code(file_path):
    """
    读取并“标准化”一个Python代码文件。

    标准化的目的是为了让比较更“纯粹”，不受变量名、注释、空行等影响。
    这里我们采用两种策略：
    1. 首选策略 (AST): 将代码解析成抽象语法树，然后再“反解析”回文本。这个过程会自动
       去除注释、统一代码风格（比如缩进和空格），非常可靠。
    2. 后备策略 (Regex): 如果代码本身有语法错误，无法被解析成AST，我们就用正则表达式
       来粗略地移除注释和文档字符串。这个方法虽然不如AST完美，但能兼容有错误的代码。

    Args:
        file_path (str): 要处理的Python文件的完整路径。

    Returns:
        str: 标准化后的代码字符串。
        None: 如果文件读取失败或两种标准化方法都失败，则返回None。
    """
    try:
        # 尝试以 utf-8 编码读取文件，忽略无法解码的字符
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source_code = f.read()
    except IOError:
        # 如果文件因为权限等问题无法打开，直接返回None
        return None

    # 1. 首选策略：使用AST进行标准化
    try:
        # ast.parse: 将源代码字符串解析成一个AST节点对象
        # ast.unparse: 将AST节点对象转换回格式统一的Python代码字符串
        return ast.unparse(ast.parse(source_code))
    except (SyntaxError, ValueError, TypeError):
        # 如果代码有语法错误(SyntaxError)或其它解析问题，上面的代码会抛出异常
        # 这时，我们切换到后备策略
        
        # 2. 后备策略：使用正则表达式进行清理
        try:
            # 移除单行注释 (从'#'到行尾)
            code = re.sub(r'#.*', '', source_code)
            # 移除三引号形式的文档字符串/多行注释 (非贪婪模式)
            code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
            code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
            # 将所有行合并，只保留那些剥离掉首尾空格后不为空的行
            return "\n".join(line for line in code.splitlines() if line.strip())
        except Exception:
            # 如果连后备策略都失败了，就彻底放弃
            return None

def find_suspicious_pairs(files_to_check, threshold):
    """
    分析一系列文件，并找出相似度高于指定阈值的文件对。

    Args:
        files_to_check (list): 一个包含所有待检查文件【完整路径】的列表。
        threshold (float): 相似度阈值，一个介于 0.0 到 1.0 之间的小数。
                           例如，0.85代表相似度高于85%才被认为是可疑的。

    Returns:
        一个元组，包含两个元素:
        - suspicious_pairs (list): 一个列表，每个元素都是一个可疑文件对的信息。
          格式为: [ ((文件1路径, 文件2路径), 相似度), ... ]
        - errors (dict): 一个字典，记录了哪些文件在处理过程中出错了。
          格式为: { 文件路径: "错误信息", ... }
    """
    file_contents = {}
    errors = {}

    # 第一步：为每个文件生成标准化的内容
    for path in files_to_check:
        normalized_code = normalize_code(path)
        if normalized_code is not None:
            # 如果标准化成功，存入字典，键是文件路径，值是标准化后的代码
            file_contents[path] = normalized_code
        else:
            # 如果失败，记录到错误字典中
            errors[path] = "无法读取或处理此文件。"

    # 如果成功处理的文件少于2个，无法进行比较，直接返回
    if len(file_contents) < 2:
        return [], errors

    suspicious_pairs = []
    # 第二步：生成所有可能的文件对组合
    # 例如，如果有 [f1, f2, f3]，combinations会生成 (f1,f2), (f1,f3), (f2,f3)
    for f1, f2 in combinations(file_contents.keys(), 2):
        # 第三步：计算两个标准化代码的相似度
        # difflib.SequenceMatcher是核心工具，用于比较两个序列的相似程度
        # .ratio() 方法返回一个 0 到 1 之间的浮点数，代表相似度
        similarity = difflib.SequenceMatcher(None, file_contents[f1], file_contents[f2]).ratio()
        
        # 第四步：如果相似度达到阈值，就记录下来
        if similarity >= threshold:
            suspicious_pairs.append(((f1, f2), similarity))

    # 第五步：将结果按相似度从高到低排序，方便查看
    suspicious_pairs.sort(key=lambda x: x[1], reverse=True)
    
    return suspicious_pairs, errors

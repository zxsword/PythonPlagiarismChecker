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

def normalize_code(file_path, advanced_mode=False):
    """
    读取并“标准化”一个Python代码文件。

    标准化的目的是为了让比较更“纯粹”，不受变量名、注释、空行等影响。
    这里我们采用两种策略：
    1. 首选策略 (AST): 将代码解析成抽象语法树。
       - 如果 advanced_mode 为 False：常规查重，保留变量名，仅统一代码格式并去除注释。
       - 如果 advanced_mode 为 True：深度查重，仅提取纯节点类型序列（免疫变量重命名）。
    2. 后备策略 (Regex): 如果代码本身有语法错误，无法被解析成AST，我们就用正则表达式
       来粗略地移除注释和文档字符串。这个方法虽然不如AST完美，但能兼容有错误的代码。

    Args:
        file_path (str): 要处理的Python文件的完整路径。
        advanced_mode (bool): 是否启用深度查重（无视变量重命名）。

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

    # 1. 首选策略
    try:
        # ast.parse: 将源代码字符串解析成一个AST节点对象
        tree = ast.parse(source_code)
        
        if not advanced_mode:
            # 常规模式：保留变量名，仅统一格式并去除注释
            return ast.unparse(tree)
        else:
            # 深度模式：提取纯节点类型（免疫变量重命名）
            class ASTStructureExtractor(ast.NodeVisitor):
                def __init__(self):
                    self.nodes = []
                def generic_visit(self, node):
                    self.nodes.append(type(node).__name__)
                    super().generic_visit(node)
                    
            extractor = ASTStructureExtractor()
            extractor.visit(tree)
            # 以特殊分隔符拼接节点名称，这会形成一个代码的“骨架指纹”
            return " ".join(extractor.nodes)
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

def find_suspicious_pairs(files_to_check, threshold, advanced_mode=False):
    """
    分析一系列文件，并找出相似度高于指定阈值的文件对。

    Args:
        files_to_check (list): 一个包含所有待检查文件【完整路径】的列表。
        threshold (float): 相似度阈值，一个介于 0.0 到 1.0 之间的小数。
                           例如，0.85代表相似度高于85%才被认为是可疑的。
        advanced_mode (bool): 是否进行深度模式（无视变量重命名）对比。

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
        normalized_code = normalize_code(path, advanced_mode)
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

import os

def build_similarity_graph(suspicious_pairs):
    """
    基于相似度列表构建无向图。
    
    【教学说明】什么是图 (Graph)？
    在这里，我们将每个被怀疑的“文件”当作图中的一个“节点(Node)”。
    如果文件A和文件B的相似度超过了阈值，我们就在它们之间连一条“边(Edge)”。
    最后得到的数据结构是一个字典，键是文件名，值是和它相似的所有文件集合。
    """
    graph = {}
    for (f1, f2), sim in suspicious_pairs:
        if f1 not in graph:
            graph[f1] = set()
        if f2 not in graph:
            graph[f2] = set()
        graph[f1].add(f2)
        graph[f2].add(f1)
    return graph

def find_plagiarism_groups(suspicious_pairs):
    """
    使用深度优先搜索找出图中的所有连通分量，即互相抄袭的分组。
    同时计算该分组内各个可疑文件对的平均相似度。
    只返回包含至少 2 个文件的组。
    
    【教学说明】连通分量 (Connected Components)：
    如果A抄B，B抄C，那么A、B、C就是一个互相连通的分组，我们用图论算法把它们一次性全抓出来。
    """
    graph = build_similarity_graph(suspicious_pairs)
    
    # 建立一个字典，存储各对文件的相似度，以便计算组内平均相似度
    sim_dict = {}
    for (f1, f2), sim in suspicious_pairs:
        sim_dict[(f1, f2)] = sim
        sim_dict[(f2, f1)] = sim

    visited = set()
    groups_with_sim = []

    # 【教学说明】深度优先搜索 (DFS - Depth First Search)
    # 这是一个经典的递归算法。想象你在走迷宫：
    # 1. 走到一个文件(node)，把它标记为“已访问(visited)”，并加入当前分组。
    # 2. 看看谁和它抄袭了(neighbor)，如果那个文件还没被访问过，就顺藤摸瓜找过去 (递归调用 dfs)。
    # 3. 直到把这条线上所有互相抄袭的人都找完。
    def dfs(node, current_group):
        visited.add(node)
        current_group.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, current_group)

    for node in graph:
        if node not in visited:
            current_group = []
            dfs(node, current_group)
            if len(current_group) >= 2:
                current_group.sort()
                
                # 计算这个组内的最大相似度和平均相似度
                group_sims = []
                for i in range(len(current_group)):
                    for j in range(i + 1, len(current_group)):
                        pair = (current_group[i], current_group[j])
                        if pair in sim_dict:
                            group_sims.append(sim_dict[pair])
                
                avg_sim = sum(group_sims) / len(group_sims) if group_sims else 0
                max_sim = max(group_sims) if group_sims else 0
                
                # 将分组和对应的最大相似度（或平均相似度）一起保存
                groups_with_sim.append((current_group, max_sim))
                
    # 按分组大小降序排列，大小相同则按相似度降序排列
    groups_with_sim.sort(key=lambda g: (len(g[0]), g[1]), reverse=True)
    return groups_with_sim

def detect_original_source(group_files):
    """
    基于启发式规则评估组内文件，选出最有可能是原创的文件。
    启发式规则主要依赖文件修改时间（最早为佳）和文件大小（越大越有可能是完整版）。
    
    Args:
        group_files (list): 组内所有文件的路径列表。
        
    Returns:
        tuple: (疑似原创文件路径, {文件路径: 得分})
    """
    if not group_files:
        return None, {}
        
    scores = {f: 0 for f in group_files}
    
    # 1. 评估时间：获取修改时间，时间越早得分越高
    try:
        times = {f: os.path.getmtime(f) for f in group_files}
        # 排序：时间从小到大（从早到晚）
        sorted_by_time = sorted(group_files, key=lambda f: times.get(f, float('inf')))
        # 第一名加 3 分，第二名加 2 分，第三名加 1 分
        for i, f in enumerate(sorted_by_time):
            scores[f] += max(0, 3 - i)
    except Exception:
        pass
        
    # 2. 评估长度：原版通常有更多注释或未被删减的死代码，越长得分越高
    lengths = {}
    for f in group_files:
        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as file:
                lengths[f] = len(file.read())
        except Exception:
            lengths[f] = 0
            
    sorted_by_len = sorted(group_files, key=lambda f: lengths.get(f, 0), reverse=True)
    for i, f in enumerate(sorted_by_len):
        scores[f] += max(0, 2 - i)
        
    # 选出得分最高的
    best_file = max(scores, key=scores.get)
    return best_file, scores

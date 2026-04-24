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
import concurrent.futures
import multiprocessing

# --- 用于进程池的全局变量和工作函数 (必须定义在顶层以支持序列化) ---
_global_file_contents = {}

# --- 预编译正则表达式以提升大规模查重时的性能 ---
_RE_COMMENT = re.compile(r'#.*')
_RE_DOC_DOUBLE = re.compile(r'""".*?"""', re.DOTALL)
_RE_DOC_SINGLE = re.compile(r"'''.*?'''", re.DOTALL)
_RE_BAD_COMMENT = re.compile(r'#[a-zA-Z0-9]')

def _init_compare_worker(contents):
    """初始化进程池的每个工作进程，将庞大的文件字典注入到全局内存，极大地优化 IPC 通信开销"""
    global _global_file_contents
    _global_file_contents = contents

def _compare_worker(pair):
    """在子进程中执行实际的查重比对任务"""
    f1, f2 = pair
    try:
        sim = difflib.SequenceMatcher(None, _global_file_contents[f1], _global_file_contents[f2]).ratio()
        return pair, sim
    except Exception:
        return pair, 0.0

def _normalize_worker(args):
    """在子进程中执行代码标准化解析"""
    path, advanced_mode = args
    return path, normalize_code(path, advanced_mode)

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
    except Exception:
        # 如果代码有语法错误或某些库不支持(如Python3.8缺少ast.unparse)，会抛出异常
        # 这时，我们切换到后备策略
        
        # 2. 后备策略：使用正则表达式进行清理
        try:
            # 移除单行注释 (从'#'到行尾)
            code = _RE_COMMENT.sub('', source_code)
            # 移除三引号形式的文档字符串/多行注释 (非贪婪模式)
            code = _RE_DOC_DOUBLE.sub('', code)
            code = _RE_DOC_SINGLE.sub('', code)
            # 将所有行合并，只保留那些剥离掉首尾空格后不为空的行
            return "\n".join(line for line in code.splitlines() if line.strip())
        except Exception:
            # 如果连后备策略都失败了，就彻底放弃
            return None

def find_suspicious_pairs(files_to_check, threshold, advanced_mode=False, progress_cb=None, cancel_event=None):
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

    # 第一步：并发执行代码标准化 (CPU密集型：AST解析)
    norm_args = [(path, advanced_mode) for path in files_to_check]
    pool = multiprocessing.Pool()
    try:
        total_norm = len(norm_args)
        completed_norm = 0
        for path, normalized_code in pool.imap_unordered(_normalize_worker, norm_args):
            if cancel_event and cancel_event.is_set():
                break
            completed_norm += 1
            if progress_cb: progress_cb(completed_norm, total_norm, "标准化")
            if normalized_code is not None:
                file_contents[path] = normalized_code
            else:
                errors[path] = "无法读取或处理此文件。"
    finally:
        # 无论正常结束还是被用户点击取消，都暴力终结所有子进程释放内存
        pool.terminate()
        pool.join()

    if cancel_event and cancel_event.is_set():
        return [], errors

    # 如果成功处理的文件少于2个，无法进行比较，直接返回
    if len(file_contents) < 2:
        return [], errors

    suspicious_pairs = []
    # 第二步：并发执行两两对比 (极其CPU密集型：difflib算法)
    pairs = list(combinations(file_contents.keys(), 2))
    # 动态计算 chunksize，减少进程间切换的损耗
    chunk_size = max(1, len(pairs) // (multiprocessing.cpu_count() * 4))

    pool2 = multiprocessing.Pool(initializer=_init_compare_worker, initargs=(file_contents,))
    try:
        total_pairs = len(pairs)
        completed_pairs = 0
        for pair, similarity in pool2.imap_unordered(_compare_worker, pairs, chunksize=chunk_size):
            if cancel_event and cancel_event.is_set():
                break
            completed_pairs += 1
            # 每完成 1% 的进度更新一次UI，防止 UI 线程被高频挤死
            if progress_cb and completed_pairs % max(1, total_pairs // 100) == 0:
                progress_cb(completed_pairs, total_pairs, "比对")
            if similarity >= threshold:
                suspicious_pairs.append((pair, similarity))
    finally:
        pool2.terminate()
        pool2.join()

    # 按相似度从高到低排序，方便查看
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

def evaluate_code_quality_ast(source_code):
    """
    针对初学者的代码规范和质量静态打分。
    结合了纯文本规范正则检查 (PEP 8 基础) 与 AST 逻辑树检查。
    """
    score = 100
    feedback = []
    
    # --- 1. 纯文本级别的格式检查 (关注初学者易犯的缩进/空格错误) ---
    lines = source_code.split('\n')
    format_penalty = 0
    for i, line in enumerate(lines):
        # 检查注释符后是否缺少空格 (例如 '#comment' 而不是 '# comment')
        if _RE_BAD_COMMENT.search(line):
            format_penalty += 1
            if format_penalty <= 3:
                feedback.append(f"- 扣1分: 第{i+1}行，注释符 '#' 后面应补充一个空格。")
        # 检查行尾是否存在多余的无用空格
        if line.rstrip() != line and line.strip() != '':
            format_penalty += 1
            if format_penalty <= 3:
                feedback.append(f"- 扣1分: 第{i+1}行，代码末尾存在多余的空白字符。")
                
    if format_penalty > 0:
        score -= min(format_penalty, 5) # 最多扣5分格式分

    # --- 2. AST 语法树结构检查 ---
    try:
        tree = ast.parse(source_code)
    except Exception as e:
        # 更温和的报错：不直接给0分，而是给一个及格分(80分)但扣除20分
        msg = getattr(e, 'msg', str(e))
        lineno = getattr(e, 'lineno', '未知')
        return 80, [f"- 严重错误 (-20分): 代码无法运行 ({msg}, 第{lineno}行)。请检查语法是否正确。"]

    
    # 1. 模块级注释
    if not ast.get_docstring(tree):
        score -= 5
        feedback.append("- 扣5分: 缺少文件顶部模块说明注释 (Module Docstring)。")
        
    func_count = 0
    class_count = 0
    max_nesting_penalty = 0
    naming_penalty = 0
    doc_penalty = 0
    bad_practice_penalty = 0
    short_var_penalty = 0
    wildcard_import_penalty = 0
    empty_except_penalty = 0
    
    def get_nesting_depth(node):
        max_depth = 0
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                max_depth = max(max_depth, 1 + get_nesting_depth(child))
            else:
                max_depth = max(max_depth, get_nesting_depth(child))
        return max_depth

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_count += 1
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
                naming_penalty += 3
                feedback.append(f"- 扣3分: 类名 '{node.name}' 不符合 CamelCase (大驼峰) 规范。")
            if not ast.get_docstring(node):
                doc_penalty += 3
                feedback.append(f"- 扣3分: 类 '{node.name}' 缺少文档注释。")
                
        elif isinstance(node, ast.FunctionDef):
            func_count += 1
            if not re.match(r'^[a-z_][a-z0-9_]*$', node.name) and not node.name.startswith('__'):
                naming_penalty += 3
                feedback.append(f"- 扣3分: 函数名 '{node.name}' 不符合 snake_case (小写下划线) 规范。")
            if not ast.get_docstring(node):
                doc_penalty += 3
                feedback.append(f"- 扣3分: 函数 '{node.name}' 缺少文档注释。")
                
            if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                length = node.end_lineno - node.lineno
                if length > 80:
                    score -= 3
                    feedback.append(f"- 扣3分: 函数 '{node.name}' 过长 ({length}行，超过80行)，建议适当拆分。")
                    
            arg_count = len(node.args.args)
            if arg_count > 6:
                score -= 3
                feedback.append(f"- 扣3分: 函数 '{node.name}' 参数过多 ({arg_count}个)，建议合并参数。")
                
            # 检查可变默认参数 (Python 新手常踩的坑)
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    bad_practice_penalty += 5
                    feedback.append(f"- 扣5分: 函数 '{node.name}' 使用了列表/字典作为默认参数，存在数据被意外共享的严重风险。")
                
            depth = get_nesting_depth(node)
            if depth > 5:
                max_nesting_penalty += 3
                feedback.append(f"- 扣3分: 函数 '{node.name}' 控制流嵌套过深 (超过5层)，初学者建议梳理逻辑。")

        elif isinstance(node, ast.ExceptHandler):
            if node.type is None or (isinstance(node.type, ast.Name) and node.type.id == 'Exception'):
                score -= 3
                feedback.append("- 扣3分: 捕获了过于宽泛的异常 (except: 或 except Exception:)，容易掩盖真实的逻辑错误。")
                
            # 检查空的异常捕获 (except: pass)
            if not node.body or (len(node.body) == 1 and isinstance(node.body[0], ast.Pass)):
                empty_except_penalty += 3
                feedback.append("- 扣3分: 出现了空的异常捕获块 (直接使用了 pass)，这会静默吞噬错误。")
                
        elif isinstance(node, ast.Global):
            score -= 3
            feedback.append(f"- 扣3分: 使用了 global 关键字声明全局变量 {node.names}，严重破坏了代码的封装性。")
            
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ('eval', 'exec'):
                bad_practice_penalty += 10
                feedback.append(f"- 扣10分: 代码使用了 '{node.func.id}()' 函数，存在任意代码执行的极度危险安全隐患。")
                
        elif isinstance(node, ast.ImportFrom):
            if any(alias.name == '*' for alias in node.names):
                wildcard_import_penalty += 3
                feedback.append(f"- 扣3分: 使用了星号导入 'from {node.module} import *'，这会导致命名空间严重污染。")
                
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            # 检查无意义的单字母变量 (排除常用于循环的标量名)
            if len(node.id) == 1 and node.id not in ('i', 'j', 'k', 'x', 'y', 'z', 'a', 'b', 'c', 'n', '_', 'e', 'f'):
                short_var_penalty += 1
                if short_var_penalty <= 5: # 最多提示5次，防刷屏
                    feedback.append(f"- 扣1分: 变量名 '{node.id}' 过于简短，缺乏表意性。")

    # 应用扣分上限，防止某项扣太多
    if naming_penalty > 0: score -= min(naming_penalty, 10)
    if doc_penalty > 0: score -= min(doc_penalty, 15)
    if max_nesting_penalty > 0: score -= min(max_nesting_penalty, 15)
    if bad_practice_penalty > 0: score -= min(bad_practice_penalty, 20)
    if short_var_penalty > 0: score -= min(short_var_penalty, 5)
    if wildcard_import_penalty > 0: score -= min(wildcard_import_penalty, 6)
    if empty_except_penalty > 0: score -= min(empty_except_penalty, 6)

    if func_count == 0 and class_count == 0:
        score -= 5
        feedback.append("- 扣5分: 建议将代码逻辑封装到函数中，而不是全部写成全局脚本。")

    score = max(0, score)
    if score == 100:
        feedback.append("非常棒！代码结构清晰，规范性很好，继续保持！")
        
    return score, feedback

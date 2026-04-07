# -*- coding: utf-8 -*-
import unittest
import os
import shutil
import sys

# 为了让这个测试文件能够找到位于父目录的 plagiarism_checker 包，
# 我们需要将父目录的路径添加到 sys.path 中。
# os.path.abspath(__file__) 获取当前文件的绝对路径
# os.path.dirname() 获取路径中的目录名
# os.path.join(..., '..') 返回上一级目录
# sys.path.append(...) 将这个路径添加到Python解释器的搜索路径列表中
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from plagiarism_checker.analysis import find_suspicious_pairs, normalize_code

class TestAnalysis(unittest.TestCase):
    """
    针对 analysis.py 中核心功能的单元测试。
    """
    
    # setUp 方法会在每个测试方法（以 test_ 开头）执行前被调用
    def setUp(self):
        """为测试准备环境：创建一个临时目录并写入一些测试用的py文件。"""
        self.test_dir = "temp_test_files"
        # 如果这个目录存在，先删掉，保证环境干净
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)

        # 定义一些代码样本
        self.code_original = """def hello():
    print('Hello, world!')
"""
        # 只是变量名和格式不同，逻辑一样
        self.code_similar = """def greeting():
    print("Hello, world!") # A comment
"""
        # 完全不同
        self.code_different = """class MyClass:
    pass
"""
        # 有语法错误
        self.code_syntax_error = """def broken_function(
    print 'oops'
"""

        # 将代码样本写入文件
        self.file_paths = {
            "original.py": os.path.join(self.test_dir, "original.py"),
            "similar.py": os.path.join(self.test_dir, "similar.py"),
            "different.py": os.path.join(self.test_dir, "different.py"),
            "identical.py": os.path.join(self.test_dir, "identical.py"),
            "error.py": os.path.join(self.test_dir, "error.py"),
        }
        
        with open(self.file_paths["original.py"], "w") as f:
            f.write(self.code_original)
        with open(self.file_paths["similar.py"], "w") as f:
            f.write(self.code_similar)
        with open(self.file_paths["different.py"], "w") as f:
            f.write(self.code_different)
        # identical.py 的内容和 original.py 完全一样
        with open(self.file_paths["identical.py"], "w") as f:
            f.write(self.code_original)
        with open(self.file_paths["error.py"], "w") as f:
            f.write(self.code_syntax_error)

    # tearDown 方法会在每个测试方法执行后被调用
    def tearDown(self):
        """清理测试环境：删除临时目录和文件。"""
        shutil.rmtree(self.test_dir)

    def test_normalization(self):
        """测试代码标准化功能是否正常工作。"""
        # 测试常规模式 (保留变量名)
        norm_orig_regular = normalize_code(self.file_paths["original.py"], advanced_mode=False)
        norm_sim_regular = normalize_code(self.file_paths["similar.py"], advanced_mode=False)
        self.assertEqual(norm_orig_regular, """def hello():\n    print('Hello, world!')""")
        self.assertEqual(norm_sim_regular, """def greeting():\n    print('Hello, world!')""")

        # 测试深度模式 (AST骨架)
        norm_orig_advanced = normalize_code(self.file_paths["original.py"], advanced_mode=True)
        norm_sim_advanced = normalize_code(self.file_paths["similar.py"], advanced_mode=True)
        self.assertEqual(norm_orig_advanced, "Module FunctionDef arguments Expr Call Name Load Constant")
        self.assertEqual(norm_sim_advanced, "Module FunctionDef arguments Expr Call Name Load Constant")

        # 对于有语法错误的文件，标准化应该能回退到正则模式，而不是直接崩溃
        norm_err = normalize_code(self.file_paths["error.py"])
        self.assertIsNotNone(norm_err, "标准化不应因语法错误而返回None")
        self.assertIn("def broken_function", norm_err)

    def test_find_suspicious_pairs(self):
        """测试查找可疑文件对的核心逻辑。"""
        all_files = list(self.file_paths.values())
        # 设置一个比较宽松的阈值，80%
        suspicious_pairs, errors = find_suspicious_pairs(all_files, 0.8)
        
        # 1. 检查是否有文件读取错误
        # 虽然 error.py 语法有误，但能通过正则后备策略解析，所以 errors 字典应该为空
        self.assertEqual(len(errors), 0, "不应该有无法处理的文件")

        # 2. 检查返回的可疑文件对数量
        # 应该有3对可疑文件被找到:
        # (original, identical) -> 100%
        # (original, similar) -> >80%
        # (similar, identical) -> >80%
        self.assertEqual(len(suspicious_pairs), 3, f"Expected 3 pairs, but found {len(suspicious_pairs)}")

        # 3. 检查具体的可疑文件对和相似度
        pairs_found = {tuple(sorted(p[0])): p[1] for p in suspicious_pairs}
        
        # 检查完全相同的文件对
        identical_pair = tuple(sorted((self.file_paths["original.py"], self.file_paths["identical.py"])))
        self.assertIn(identical_pair, pairs_found, "未能找到 identical/original 对")
        self.assertAlmostEqual(pairs_found[identical_pair], 1.0, "identical/original 对的相似度不为1.0")
        
        # 检查高度相似的文件对
        similar_pair = tuple(sorted((self.file_paths["original.py"], self.file_paths["similar.py"])))
        self.assertIn(similar_pair, pairs_found, "未能找到 similar/original 对")
        self.assertGreater(pairs_found[similar_pair], 0.8, "similar/original 对的相似度应高于阈值")

        # 检查不相似的文件对是否被排除
        # (original, different) 这一对不应该出现在结果中
        different_pair = tuple(sorted((self.file_paths["original.py"], self.file_paths["different.py"])))
        self.assertNotIn(different_pair, pairs_found, "不应将 different/original 对识别为可疑")

if __name__ == '__main__':
    # 这使得我们可以直接通过 `python tests/test_analysis.py` 来运行测试
    unittest.main()

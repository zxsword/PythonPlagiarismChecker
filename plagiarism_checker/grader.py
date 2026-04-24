# -*- coding: utf-8 -*-
"""
自动批改核心模块
将 AST 静态分析、本地大模型 (GPT4All) 和云端大模型 (Gemini) 的批改业务逻辑从 UI 界面中彻底抽离出来，
实现代码的 MVC (前后端) 解耦。
"""
import os
import time
import re
import urllib.request
import concurrent.futures
import threading
from pathlib import Path
from .analysis import evaluate_code_quality_ast

class AutoGrader:
    def __init__(self, grading_method, files_to_check, exercise_text, require_suggestions, 
                 api_key, api_model, local_model, api_proxy, status_cb, progress_cb, result_cb, cancel_event=None):
        self.grading_method = grading_method
        self.files_to_check = files_to_check
        self.exercise_text = exercise_text
        self.require_suggestions = require_suggestions
        self.api_key = api_key
        self.api_model = api_model
        self.local_model = local_model
        self.api_proxy = api_proxy
        self.cancel_event = cancel_event
        
        # 【教学说明】回调函数 (Callbacks) 的妙用
        # AutoGrader 只是一个在后台苦苦干活的“打工人类”，它不认识进度条，也不认识表格。
        # 主程序在实例化它的时候，塞给了它三个“对讲机” (status_cb, progress_cb, result_cb)。
        # 当后台批改完一个文件，它不用操心怎么画界面，只需要对对讲机喊一声：
        # “喂，result_cb，我批改完一个了，这是分数，你看着办！”
        # 而这三个对讲机内部，主程序已经封装好了安全的 self.after 更新界面的逻辑。
        self.status_cb = status_cb
        self.progress_cb = progress_cb
        self.result_cb = result_cb

    def run(self):
        """执行批改任务的分发总控"""
        if self.grading_method == "AST 静态质量打分":
            self._run_ast()
        elif self.grading_method == "AI 云端大模型 (Gemini)":
            self._run_gemini()
        else:
            self._run_local_llm()

    def _run_ast(self):
        self.status_cb("正在使用 AST 进行静态代码质量打分...")
        
        start_time = time.time()
        completed_count = [0]
        count_lock = threading.Lock()
        shared_eta = ["计算中..."]

        def process_ast(file_path):
            if self.cancel_event and self.cancel_event.is_set():
                return
            file_name = os.path.basename(file_path)
            self.status_cb(f"AST 解析中: {file_name} | 预计剩余: {shared_eta[0]}")
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    source_code = f.read()
                
                score, feedback = evaluate_code_quality_ast(source_code)
                review_text = "\n".join(feedback)
                self.result_cb(file_path, score, self.grading_method, "✔ 批改完成", review_text, False)
            except Exception as e:
                self.result_cb(file_path, "-", self.grading_method, f"评分出错: {str(e)}", f"出错详情: {str(e)}", True)
            finally:
                with count_lock:
                    completed_count[0] += 1
                    c = completed_count[0]
                if c > 0:
                    elapsed = time.time() - start_time
                    avg = elapsed / c
                    rem = len(self.files_to_check) - c
                    shared_eta[0] = f"{int(avg * rem)}秒"
                self.progress_cb()
                self.status_cb(f"已完成 {c}/{len(self.files_to_check)} | 预计剩余: {shared_eta[0]}")

        # 使用多线程加速 AST 文件解析
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(process_ast, self.files_to_check)

    def _run_gemini(self):
        try:
            from google import genai
        except ImportError:
            self.result_cb("ALL", "-", self.grading_method, "缺少依赖库，请先卸载旧版并安装新版: pip install google-genai", "", True)
            for _ in self.files_to_check: self.progress_cb()
            return

        if not self.api_key:
            self.result_cb("ALL", "-", self.grading_method, "错误：未填写 API Key。请点击顶部【🔑 API设置】。", "", True)
            for _ in self.files_to_check: self.progress_cb()
            return

        if self.api_proxy:
            os.environ['http_proxy'] = self.api_proxy
            os.environ['https_proxy'] = self.api_proxy
            os.environ['HTTP_PROXY'] = self.api_proxy
            os.environ['HTTPS_PROXY'] = self.api_proxy

        model_name = self.api_model or 'gemini-1.5-flash'
        
        try:
            client = genai.Client(api_key=self.api_key)
        except Exception as e:
            self.result_cb("ALL", "-", self.grading_method, f"API初始化失败: {str(e)}", "", True)
            for _ in self.files_to_check: self.progress_cb()
            return
            
        self.status_cb("正在连接 Gemini 云端模型...")

        # 全局 API 请求排队锁，配合 last_req_time 严格控制发包速率
        api_lock = threading.Lock()
        last_req_time = [0.0]

        start_time = time.time()
        completed_count = [0]
        count_lock = threading.Lock()
        shared_eta = ["计算中..."]

        def process_single_gemini(file_path):
            if self.cancel_event and self.cancel_event.is_set():
                return
            file_name = os.path.basename(file_path)
            self.status_cb(f"Gemini 正在批改: {file_name} | 预计剩余: {shared_eta[0]}")
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    source_code = f.read()
                    
                numbered_source = "\n".join([f"{idx+1} | {line}" for idx, line in enumerate(source_code.split('\n'))])
                
                prompt = "你是一个负责给Python初学者批改作业的严格老师。满分100分。\n"
                if self.exercise_text:
                    prompt += f"【评分细则】：\n{self.exercise_text}\n请严格按照细则审查并扣分。\n"
                
                prompt += "\n为了保持报告清晰，你【必须且只能】按以下固定模板输出，不要说任何废话客套话：\n"
                prompt += "【最终评分】: [填入0-100的纯数字]分\n"
                prompt += "【扣分明细】:\n"
                
                if self.require_suggestions:
                    prompt += "- 第[X]行：[指出错误] -> [给出修改建议] (扣[Y]分)\n"
                    prompt += "【总体评价】:\n[一段50字以内的精炼总结]\n"
                else:
                    prompt += "- 第[X]行：[一句话指出错误] (扣[Y]分)\n"
                    prompt += "【总体评价】:\n[一句10字以内的简短总结]\n"
                    
                prompt += f"\n带行号的代码如下：\n```python\n{numbered_source}\n```"
                
                max_retries = 8
                for attempt in range(max_retries):
                    try:
                        # 【核心限流逻辑】：强行让所有线程在此排队，保证任意两次 API 发送至少间隔 5 秒
                        # 从根本上杜绝多线程同时发包引起的瞬间并发洪峰
                        with api_lock:
                            now = time.time()
                            elapsed = now - last_req_time[0]
                            if elapsed < 5.0:
                                if self.cancel_event and self.cancel_event.wait(5.0 - elapsed):
                                    return
                            last_req_time[0] = time.time()

                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                        )
                        reply = response.text
                        break
                    except Exception as api_e:
                        error_str = str(api_e)
                        if 'limit: 0' in error_str:
                            raise Exception("API拒绝访问(免费额度为0)。原因可能是：1. 该模型无免费额度(请在设置中换用以 flash 结尾的模型)；2. 代理节点失效。")
                        if ('429' in error_str or 'RESOURCE_EXHAUSTED' in error_str or '503' in error_str or 'UNAVAILABLE' in error_str) and attempt < max_retries - 1:
                            # 解析官方报错中明确给出的建议等待时间 (例如: "Please retry in 8.155s.")
                            wait_time = 20 * (attempt + 1)
                            delay_match = re.search(r'retry in (\d+(?:\.\d+)?)s', error_str)
                            if delay_match:
                                # 取官方建议时间 + 2秒缓冲，与默认递增时间取最大值
                                wait_time = max(wait_time, float(delay_match.group(1)) + 2.0)
                                
                            self.status_cb(f"{file_name} 触发限流，暂停 {wait_time:.1f} 秒后重试 (第 {attempt+1} 次)...")
                            if self.cancel_event and self.cancel_event.wait(wait_time):
                                return
                        else:
                            raise api_e
                
                match = re.search(r'【最终评分】.*?(\d{1,3})', reply)
                if not match:
                    match = re.search(r'(\d{1,3})(?=\s*分)', reply)
                score_val = match.group(1) if match else "-"
                self.result_cb(file_path, score_val, self.grading_method, "✔ 批改完成", reply, False)
            except Exception as e:
                self.result_cb(file_path, "-", self.grading_method, f"批改失败: {str(e)}", f"详细报错: {str(e)}", True)
            finally:
                with count_lock:
                    completed_count[0] += 1
                    c = completed_count[0]
                if c > 0:
                    elapsed = time.time() - start_time
                    avg = elapsed / c
                    rem = len(self.files_to_check) - c
                    eta = int(avg * rem)
                    m, s = divmod(eta, 60)
                    shared_eta[0] = f"{m}分{s}秒" if m > 0 else f"{s}秒"
                self.progress_cb()
                self.status_cb(f"已完成 {c}/{len(self.files_to_check)} | 预计剩余: {shared_eta[0]}")

        # 并发数设为3。得益于内部严格的 5 秒排队锁，API 的实际发出速率会被完美限制在 12 RPM 内，不再报错。
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for file_path in self.files_to_check:
                futures.append(executor.submit(process_single_gemini, file_path))
            
            # 阻塞等待所有线程任务跑完
            concurrent.futures.wait(futures)

    def _run_local_llm(self):
        try:
            from gpt4all import GPT4All
            
            cache_dir = os.path.join(Path.home(), ".cache", "gpt4all")
            os.makedirs(cache_dir, exist_ok=True)
            model_name = self.local_model or "qwen2.5-3b-instruct-q4_k_m.gguf"
            model_path = os.path.join(cache_dir, model_name)
            
            # 系统内置模型下载字典
            known_models = {
                "qwen2.5-3b-instruct-q4_k_m.gguf": f"https://hf-mirror.com/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
                "qwen2.5-7b-instruct-q4_k_m.gguf": f"https://hf-mirror.com/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf",
                "gemma-3-4b-it-q4_k_m.gguf": f"https://hf-mirror.com/bartowski/gemma-3-4b-it-GGUF/resolve/main/gemma-3-4b-it-Q4_K_M.gguf",
            }
            
            if not os.path.exists(model_path) or os.path.getsize(model_path) < 10 * 1024 * 1024:
                if model_name in known_models:
                    self.status_cb(f"正在从国内镜像下载系统推荐模型 ({model_name})，请耐心等待... 0%")
                    url = known_models[model_name]
                    try:
                        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req) as response, open(model_path, 'wb') as out_file:
                            total_length = int(response.info().get('Content-Length', 0))
                            downloaded = 0
                            block_size = 8192 * 4
                            while True:
                                buffer = response.read(block_size)
                                if not buffer:
                                    break
                                downloaded += len(buffer)
                                out_file.write(buffer)
                                if total_length > 0 and downloaded % (block_size * 200) == 0:
                                    percent = int(downloaded * 100 / total_length)
                                    self.status_cb(f"正在从国内镜像下载系统推荐模型，请耐心等待... {percent}%")
                    except Exception as e:
                        if '404' in str(e):
                            self.result_cb("ALL", "-", self.grading_method, f"自动下载失败 (404 Not Found)", f"该模型的云端链接已变更。请手动前往开源社区下载此 .gguf 文件，然后通过软件界面的【📁 导入本地模型】按钮将其导入。", True)
                            if os.path.exists(model_path): os.remove(model_path)
                            for _ in self.files_to_check: self.progress_cb()
                            return
                        else:
                            raise e
                else:
                    self.result_cb("ALL", "-", self.grading_method, f"未找到本地模型文件: {model_name}", "此为您自定义输入的模型名，系统无下载链接。请先点击【导入本地模型】将您的 .gguf 文件导入。", True)
                    for _ in self.files_to_check: self.progress_cb()
                    return
                            
            self.status_cb("正在加载本地 AI 模型 (尝试启动 GPU 加速，已禁用后台联网)...")
            model = GPT4All(model_name, model_path=cache_dir, allow_download=False, device='gpu')
            
            # 获取底层库实际分配的硬件设备（如果 GPU 显存不足，这里可能会显示返回了 CPU）
            actual_device = getattr(model, 'device', '未知设备')
            self.status_cb(f"模型加载成功！当前实际运行硬件: [{actual_device}]")
            
            start_time = time.time()
            for i, file_path in enumerate(self.files_to_check):
                if self.cancel_event and self.cancel_event.is_set():
                    break
                file_name = os.path.basename(file_path)
                
                if i > 0:
                    elapsed = time.time() - start_time
                    avg = elapsed / i
                    rem = len(self.files_to_check) - i
                    eta = int(avg * rem)
                    m, s = divmod(eta, 60)
                    eta_str = f"{m}分{s}秒" if m > 0 else f"{s}秒"
                else:
                    eta_str = "计算中..."
                    
                self.status_cb(f"AI 批改中 ({i+1}/{len(self.files_to_check)}): {file_name} | 预计剩余: {eta_str}")
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        source_code = f.read()
                    
                    # 为源代码添加行号，方便本地模型精确定位错误
                    numbered_source = "\n".join([f"{idx+1} | {line}" for idx, line in enumerate(source_code.split('\n'))])
                        
                    prompt = "你是一个负责给Python初学者批改作业的严格老师。满分100分。\n"
                    if self.exercise_text:
                        prompt += f"【评分细则】：\n{self.exercise_text}\n请严格按照细则审查并扣分。\n"
                    
                    prompt += "\n为了保持报告清晰，你【必须且只能】按以下固定模板输出，不要说任何废话客套话：\n"
                    prompt += "【最终评分】: [填入0-100的纯数字]分\n"
                    prompt += "【扣分明细】:\n"
                    
                    if self.require_suggestions:
                        prompt += "- 第[X]行：[指出错误] -> [给出详细的修改建议和代码示例] (扣[Y]分)\n"
                        prompt += "【总体评价】:\n[一段100字以内的精炼总结]\n"
                        max_tok = 1024  # 大幅放宽字数限制，允许模型输出长篇建议
                    else:
                        prompt += "- 第[X]行：[一句话指出错误] (扣[Y]分)\n"
                        prompt += "【总体评价】:\n[一句10字以内的简短总结]\n"
                        max_tok = 256
                        
                    prompt += f"\n带行号的代码如下：\n```python\n{numbered_source}\n```"
                    with model.chat_session():
                        # temp=0.3 可以在保持格式严谨的同时，让语言更加自然丰富
                        reply = model.generate(prompt, max_tokens=max_tok, temp=0.3)
                        
                    match = re.search(r'【最终评分】.*?(\d{1,3})', reply)
                    if not match:
                        match = re.search(r'(\d{1,3})(?=\s*分)', reply)
                    score_val = match.group(1) if match else "-"
                    self.result_cb(file_path, score_val, self.grading_method, "✔ 批改完成", reply, False)
                except Exception as e:
                    self.result_cb(file_path, "-", self.grading_method, f"批改出错: {str(e)}", f"报错: {str(e)}", True)
                finally:
                    self.progress_cb()
        except ImportError:
            self.result_cb("ALL", "-", self.grading_method, "缺少依赖库，请在终端运行: pip install gpt4all", "", True)
            for _ in self.files_to_check: self.progress_cb()
        except Exception as e:
            self.result_cb("ALL", "-", self.grading_method, f"系统运行失败: {str(e)}", "", True)
            for _ in self.files_to_check: self.progress_cb()

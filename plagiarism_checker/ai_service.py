# -*- coding: utf-8 -*-
"""
AI 服务模块
负责统一封装所有大模型 (云端 API 和本地离线模型) 的调用接口，
实现网络请求环境设置、Client 初始化逻辑的复用与代码精简。
"""
import os
from pathlib import Path

def get_cloud_client(api_key, api_base="", api_proxy=""):
    """
    初始化并返回兼容 OpenAI 格式的云端客户端，自动处理代理设置与合法性校验。
    """
    import openai
    if not api_key:
        # 抛出异常，外层（如 dialogs.py）捕获后会在界面的状态栏或弹窗里显示出来提醒用户
        raise ValueError("未填写 API Key，请先在主界面【⚙️ AI设置】中配置。")
        
    if api_proxy:
        # 遍历常见的系统环境变量代理名称，强制让当前程序的网络请求走你指定的代理端口
        for p in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
            os.environ[p] = api_proxy
            
    # 组装初始化参数。将动态参数放进字典里，方便后续统一传给 OpenAI
    client_kwargs = {"api_key": api_key}
    if api_base and api_base.strip():
        client_kwargs["base_url"] = api_base.strip()
        
    # 使用 ** 语法解包字典，等同于写成 openai.OpenAI(api_key=..., base_url=...)
    return openai.OpenAI(**client_kwargs)

def ask_cloud_llm(prompt, api_key, api_base="", api_model="gemini-1.5-flash", api_proxy=""):
    """
    对云端大模型发起一次对话请求并返回字符串结果。
    （适用于单次调用，如深度抄袭审判）
    """
    # 第一步：获取配置好代理和密钥的客户端实例
    client = get_cloud_client(api_key, api_base, api_proxy)
    # 第二步：如果用户没填模型名称，就给一个默认值兜底
    model_name = api_model.strip() if api_model and api_model.strip() else 'gemini-1.5-flash'
    
    # 第三步：发起同步对话请求，并从返回的复杂 JSON 结构中直接剥离出纯文本的回答
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def load_local_model(model_name=None):
    """统一的本地 GPT4All 模型加载器。"""
    from gpt4all import GPT4All
    # 设置模型下载和读取的专属缓存目录，放在用户主目录下的 .cache 文件夹，防止污染我们自己的项目代码文件夹
    cache_dir = os.path.join(Path.home(), ".cache", "gpt4all")
    return GPT4All(model_name or "qwen2.5-3b-instruct-q4_k_m.gguf", model_path=cache_dir, allow_download=False, device='gpu')
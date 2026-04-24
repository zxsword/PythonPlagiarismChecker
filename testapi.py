import os
from google import genai

os.environ['HTTP_PROXY'] = 'http://127.0.0.1:9910'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:9910'

# 请使用你新生成的 Key
client = genai.Client(api_key="AIzaSyBgd_-IRheXPLrrDsC55Jye9RXrIG_tRNQ")

try:
    print("--- 当前账号在 google-genai SDK 下的可调用 ID ---")
    for model in client.models.list():
        # 新版 SDK 的属性名是 supported_actions
        if 'generateContent' in model.supported_actions:
            print(f"可用 ID: {model.name}")
except Exception as e:
    print(f"获取列表失败: {e}")
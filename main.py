import requests
import sys
import json

# OpenClaw 会将参数通过命令行传入，这里进行解析
query = ""
for arg in sys.argv:
    if arg.startswith("--query="):
        query = arg.split("=", 1)[1]
        break

# 调用你的 API 服务 (注意更换为实际地址)
api_url = "http://127.0.0.1:8000/execute"
response = requests.post(api_url, json={"query": query})

if response.status_code == 200:
    result = response.json()
    print(result.get("final_prompt", "No prompt returned"))
else:
    print(f"Error calling API: {response.status_code}")

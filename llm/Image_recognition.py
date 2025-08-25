import hashlib
import requests
from openai import OpenAI
import os
import json

async def 图片识别(链接:str,api_key:str,api_url:str,model_name:str)->str:
    """
    预处理
    """
    # 下载图片
    response = requests.get(链接)
    if response.status_code != 200:
        raise Exception("图片下载失败")
    # 获取图片内容
    image_content = response.content
    # 计算图片的MD5哈希值
    hash_md5 = hashlib.md5()
    hash_md5.update(image_content)
    image_hash = hash_md5.hexdigest()
    # 读取缓存文件
    cache_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'Image_description_cache.txt')
    cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                if os.path.getsize(cache_file) > 0:
                    cache = json.load(f)
                # else: cache remains {}
        except json.JSONDecodeError:
            # 如果 JSON 无效，初始化为空字典
            cache = {}
    if image_hash in cache:
        return cache[image_hash]
    """
    图片识别
    """
    client = OpenAI(
    api_key=api_key,
    base_url=api_url,
    )

    response = client.chat.completions.create(
        model=model_name,
        max_tokens=200,
        temperature=0.3,
        messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "请描写图片中的内容。若你认为这张图片可能是用于表达情绪的表情包，这时请着重输出他表达的情绪元素（其他的也要有，但是情绪元素至少有4点）。输出要少于100token，直截了当。"
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url":链接
                    }
                }
            ]
        }],
        stream=False
    )
    图片描述 = response.choices[0].message.content
    # 写入缓存
    cache[image_hash] = 图片描述
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)
    return 图片描述
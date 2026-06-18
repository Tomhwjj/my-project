#!/usr/bin/env python3
"""
图像识别脚本 —— 将图片缩放后发送到本地视觉 API，返回 Markdown 文本。
用法:
    python recognize.py <image_path> [--api-base URL] [--model MODEL] [--prompt PROMPT]
"""

import argparse
import base64
import io
import json
import os
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("[ERROR] Pillow 未安装，请先执行: pip install Pillow", file=sys.stderr)
    sys.exit(1)

try:
    import requests
except ImportError:
    print("[ERROR] requests 未安装，请先执行: pip install requests", file=sys.stderr)
    sys.exit(1)

# ---------- 默认值 ----------
DEFAULT_API_BASE = os.environ.get(
    "IMAGE_RECOGNITION_API_BASE",
    "http://localhost:11434/api/chat",  # Ollama 原生 API
)
DEFAULT_MODEL = os.environ.get("IMAGE_RECOGNITION_MODEL", "llava:13b")
# API 类型: "ollama" (原生) 或 "openai" (OpenAI 兼容)
DEFAULT_API_TYPE = os.environ.get("IMAGE_RECOGNITION_API_TYPE", "ollama")
DEFAULT_API_KEY = os.environ.get("IMAGE_RECOGNITION_API_KEY", "")
DEFAULT_PROMPT = "识别图片里所有信息，使用 markdown 输出全部内容，并保持排版的一致"
MAX_LONGEST_SIDE = 1280


def resize_image(image_path: str) -> Image.Image:
    """缩放图片，使最长边 ≤ 1280 px，保持宽高比。"""
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    longest = max(w, h)
    if longest <= MAX_LONGEST_SIDE:
        print(f"[INFO] 图片尺寸 {w}x{h} 已在限制内，无需缩放", file=sys.stderr)
        return img
    ratio = MAX_LONGEST_SIDE / longest
    new_w, new_h = int(w * ratio), int(h * ratio)
    print(f"[INFO] 缩放图片: {w}x{h} → {new_w}x{new_h}", file=sys.stderr)
    return img.resize((new_w, new_h), Image.LANCZOS)


def image_to_base64(img: Image.Image) -> str:
    """将 Pillow Image 编码为 base64 字符串。"""
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _build_ollama_payload(model: str, prompt: str, b64_image: str) -> dict:
    """构建 Ollama 原生 API 请求体。"""
    return {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [b64_image],
            }
        ],
        "stream": False,
    }


def _build_openai_payload(model: str, prompt: str, b64_image: str) -> dict:
    """构建 OpenAI 兼容 API 请求体。"""
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        "max_tokens": 4096,
    }
    if model:
        payload["model"] = model
    return payload


def _parse_ollama_response(data: dict) -> str:
    """解析 Ollama 原生 API 返回。"""
    return data["message"]["content"]


def _parse_openai_response(data: dict) -> str:
    """解析 OpenAI 兼容 API 返回。"""
    return data["choices"][0]["message"]["content"]


def call_vision_api(
    api_base: str, model: str, prompt: str, b64_image: str,
    api_type: str = "ollama", api_key: str = "",
) -> str:
    """调用视觉 API，返回 Markdown 文本。支持 ollama / openai 两种 API 格式。"""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if api_type == "openai":
        payload = _build_openai_payload(model, prompt, b64_image)
        parser = _parse_openai_response
    else:
        payload = _build_ollama_payload(model, prompt, b64_image)
        parser = _parse_ollama_response

    print(f"[INFO] 调用 API ({api_type}): {api_base}", file=sys.stderr)
    try:
        resp = requests.post(api_base, headers=headers, json=payload, timeout=300)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] API 请求失败: {e}", file=sys.stderr)
        if hasattr(e, "response") and e.response is not None:
            print(f"[ERROR] 响应内容: {e.response.text[:500]}", file=sys.stderr)
        sys.exit(1)

    data = resp.json()
    try:
        content = parser(data)
    except (KeyError, IndexError, TypeError):
        print(f"[ERROR] 无法解析 API 返回: {json.dumps(data, ensure_ascii=False)[:500]}", file=sys.stderr)
        sys.exit(1)

    return content


def main():
    # 强制 UTF-8 输出，避免 Windows GBK 终端编码错误
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="图像识别 → Markdown")
    parser.add_argument("image", help="图片文件路径")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE, help="视觉 API 地址")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="模型名称")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="识别提示词")
    parser.add_argument("--api-type", default=DEFAULT_API_TYPE, help="API 类型: ollama 或 openai")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API Key（云端模型需要）")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.is_file():
        print(f"[ERROR] 图片文件不存在: {args.image}", file=sys.stderr)
        sys.exit(1)

    # 1. 缩放图片
    img = resize_image(str(image_path))
    # 2. Base64 编码
    b64 = image_to_base64(img)
    # 3. 调用 API
    result = call_vision_api(args.api_base, args.model, args.prompt, b64,
                             api_type=args.api_type, api_key=args.api_key)
    # 4. 输出 Markdown
    print(result)


if __name__ == "__main__":
    main()

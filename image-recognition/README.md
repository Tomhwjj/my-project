# Image Recognition Skill

将图片发送到视觉大模型，返回 Markdown 文本。

## 双模式

| 模式 | 模型 | 费用 | 质量 |
|------|------|------|------|
| 本地 | `llava:13b` (Ollama) | 免费 | 粗粒度 |
| 云端 | `qwen-vl-max` (通义千问) | 按量计费 | 精确，中文强 |

## 安装

### 1. 安装 Skill

```bash
cp -r image-recognition ~/.claude/skills/image-recognition
```

### 2. 安装 Python 依赖

```bash
cd ~/.claude
python -m venv venv
./venv/Scripts/pip install Pillow requests
```

### 3. 安装 Ollama + 模型（本地方案）

```bash
# 下载安装: https://ollama.com/download/windows
ollama pull llava:13b
```

### 4. 配置云端 API（云端方案，可选）

```bash
setx IMAGE_RECOGNITION_API_TYPE "openai"
setx IMAGE_RECOGNITION_API_BASE "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
setx IMAGE_RECOGNITION_MODEL "qwen-vl-max"
setx IMAGE_RECOGNITION_API_KEY "<你的通义千问 API Key>"
```

## 使用

```bash
# 本地方案（免费）
~/.claude/venv/Scripts/python recognize.py 图片.jpg

# 云端方案（精确）
~/.claude/venv/Scripts/python recognize.py 图片.jpg --api-type openai
```

## 注意事项

- 如果 Windows 用户名含中文，需设置 `OLLAMA_MODELS` 到纯 ASCII 路径
- 图片最长边超过 1280px 会自动缩放

---
name: image-recognition
description: 图像识别 —— 识别图片内容并输出 Markdown。当用户提供图片、粘贴截图、分享照片、要求识别图片/图像/照片内容时触发。也适用于"帮我看下这张图"、"识别这张图片"、"图里有什么"等请求。
---

# 图像识别 (Image Recognition)

将用户提供的图片发送到本地视觉大模型 API，识别全部内容并返回结构化的 Markdown 文本。

## 双模式

Skill 支持两种视觉模型，通过 `--api-type` 切换：

| 模式 | API 类型 | 模型 | 费用 | 质量 |
|------|------|------|------|------|
| **本地** | `ollama` | `llava:13b` | 免费 | 粗粒度，中文弱 |
| **云端** | `openai` | `qwen-vl-max` (通义千问) | 按量计费 | 精确，中文强 |

## 使用前提

- 本地方案：Ollama 已安装，`llava:13b` 已拉取
- 云端方案：已配置 `IMAGE_RECOGNITION_API_KEY` 环境变量（通义千问 DashScope Key）
- Python 虚拟环境已就绪：`~/.claude/venv/`（包含 `Pillow` 和 `requests`）

## 执行流程

### 第一步：确认图片路径

用户可能在消息中：
- 直接粘贴图片（Claude Code 会保存为临时文件）—— 找到该文件路径
- 提供文件路径（绝对或相对路径）—— 转为绝对路径

### 第二步：运行识别脚本

**本地方案（Ollama，免费）：**
```bash
~/.claude/venv/Scripts/python.exe ~/.claude/skills/image-recognition/scripts/recognize.py "<图片绝对路径>"
```

**云端方案（通义千问 VL，精确）：**
```bash
~/.claude/venv/Scripts/python.exe ~/.claude/skills/image-recognition/scripts/recognize.py "<图片绝对路径>" --api-type openai
```

可选参数（按需使用）：
| 参数 | 说明 | 本地默认值 | 云端默认值 |
|------|------|------|------|
| `--api-base URL` | API 地址 | `http://localhost:11434/api/chat` | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` |
| `--model MODEL` | 模型名称 | `llava:13b` | `qwen-vl-max` |
| `--api-type TYPE` | ollama 或 openai | `ollama` | `openai` |
| `--api-key KEY` | API Key（云端必填） | — | 从环境变量读取 |
| `--prompt PROMPT` | 自定义提示词 | `识别图片里所有信息，使用 markdown 输出全部内容，并保持排版的一致` | 同左 |

### 第三步：呈现结果

脚本会将 Markdown 文本输出到 stdout。将结果原样展示给用户，并告知用户可以将这些内容用于后续操作。

## 错误处理

| 现象 | 处理方式 |
|------|----------|
| API 连接失败 | 检查 Ollama 是否在运行: `curl http://localhost:11434/api/tags` |
| 模型未加载 | 确保已 `ollama pull llava:13b`，且 `OLLAMA_MODELS` 指向正确路径（如 `C:\ollama_models\models`） |
| 中文路径错误 | llama-server 不支持中文路径，需设置 `OLLAMA_MODELS` 到纯 ASCII 路径 |

## 环境变量（可选）

可通过环境变量覆盖默认值，避免每次传参：
- `IMAGE_RECOGNITION_API_BASE` — 视觉 API 地址
- `IMAGE_RECOGNITION_MODEL` — 默认模型名
- `IMAGE_RECOGNITION_API_TYPE` — API 类型 (`ollama` 或 `openai`)
- `OLLAMA_MODELS` — Ollama 模型存储路径（已设为 `C:\ollama_models\models`，避免中文路径问题）

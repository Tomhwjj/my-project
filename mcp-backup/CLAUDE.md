# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 环境

- **系统**: Windows 11, Shell: Git Bash (Unix 风格路径)
- **Git**: 2.54.0, 全局用户 `Tomhwjj` (3084618707@qq.com)
- **GitHub**: https://github.com/Tomhwjj
- **包管理**: npm/npx 可用

## 仓库

`D:\Agent\git` 是**项目收纳总目录**（资源管理器），所有项目文件夹放这里。

| 路径 | 说明 | 远程 |
|------|------|------|
| `D:\Agent\git` | 主仓库 | `origin` → `https://github.com/Tomhwjj/my-project.git` |
| `D:\Agent\git\paper-generator` | 论文生成工具链 | `origin` → `https://github.com/Tomhwjj/paper-generator.git` |
| `D:\Agent\git\image-recognition` | 图像识别 | `origin` → `https://github.com/Tomhwjj/image-recognition.git` |
| `D:\Agent\git\knowledge-base` | 本地知识库 | `origin` → `https://github.com/Tomhwjj/knowledge-base.git` |
| `D:\Agent\git\OpenCLI` | 开源 CLI 参考 | `origin` → `https://github.com/jackwener/OpenCLI.git` |
| `D:\Agent\git\trading-system` | 选股+交易日志系统 | `origin` → `https://github.com/Tomhwjj/trading-system.git` |
| `D:\Agent\git\vercel-skills` | GitHub skill 源码备份（下载的参考 skill 放这里） | `origin` → `https://github.com/vercel-labs/skills.git` |

**项目收纳规范**：
- 结构清晰，每个项目独立文件夹
- 文件夹命名清晰，一眼能看出用途（英文小写+连字符）
- 新建项目默认放 `D:\Agent\git\<项目名>\`
- 项目要有独立 `.git` 和远程仓库

### 两样东西，分开放

| 类型 | 位置 | 说明 |
|------|------|------|
| **安装好要用的** | `~/.agents/skills/`（主）+ `~/.claude/skills/`（同步） | Skill 装到 .agents，同时复制一份到 .claude |
| **项目（备份/发布/分享）** | `D:\Agent\git/<项目名>/` | 独立仓库，有自己的 GitHub 远程 |

**铁律**：
- `D:\Agent\git` 里每个文件夹必须是自己独立的 git 仓库（有 `.git`，有 GitHub remote）
- **新建项目第一步**：`git init` → `git add -A` → `git commit` → GitHub 建仓库 → `git remote add` → `git push`，做完再写代码
- 不要往 `D:\Agent\git` 里扔 skill 安装副本、程序安装文件、下载的临时文件
- 命名要区分：`paper-generator`（项目） vs `paper-creator`（模糊不清的旧版残留）
- 旧版/残留直接删，别留着混淆

## 全局 Skills

已安装的 Claude Code skills (`~/.agents/skills/`):

- **agent-reach** — 全网调研：搜索 Twitter/X、Reddit、YouTube、B站、小红书、V2EX、RSS 等 13 个平台，零 API 费用
- **find-skills** — 搜索和发现更多 skills（`npx skills find <关键词>`）
- **skill-creator** — 创建自定义 skill 的模板和指南
- **image-recognition** — 图像识别，将图片发送到本地视觉 API 并返回 Markdown 文本
- **paper-generator** — 论文自动生成全流程（解析需求→文献检索→AIGC降重→排版Word）
- **humanize-chinese-academic** — 中文学术论文 AIGC 降重引擎（6轮PaperPass实测+策略自进化）
- **brainstorming** — 🚫 手动模式：仅在我说"用 brainstorming"/"调用 brainstorming"/"/brainstorming"时才触发，绝不自动激活
- **writing-plans** — 🚫 手动模式：同 brainstorming，我说调用才调用
- **trading-system** — 选股工作流+交易日志（项目级 skill，`D:\Agent\git\.claude\skills\`），日报/板块扫描/交易录入/统计
- **chrome-devtools / playwright (MCP)** — 浏览器操控双件套，分工见 [MCP 服务器](#mcp-服务器) 章节

## MCP 服务器

| 服务器 | 定位 | 独有能力 |
|--------|------|----------|
| **chrome-devtools** | 日常浏览辅助 + 诊断 | Lighthouse 审计、Heap 内存分析、Performance 追踪、复用已有 Chrome（免登录） |
| **playwright** `--caps=network,storage` | 自动化补充 | 网络拦截 Mock、Cookie/Storage CRUD、`browser_run_code` 万能逃生舱 |

**使用分工**：
- 日常浏览、点按钮、填表单、看页面 → **chrome-devtools**（轻量，复用已有 Chrome 的登录态）
- 需要 Mock API、操作 Cookie/Storage、跑复杂自动化脚本 → **Playwright**
- 需要 Lighthouse / 内存分析 / 性能诊断 → **chrome-devtools**（Playwright 没有）
- 不养闲进程：用完关浏览器

**Playwright 扩展 caps**（按需手动加，不预装）：`vision`（像素级鼠标）、`testing`（测试断言）、`pdf`（导出PDF）、`devtools`（视频录制）

## 🚫 Superpowers 约束（重要）

brainstorming 和 writing-plans 已安装，但设置为了**严格手动模式**：

- ❌ **绝不自动触发**——即使系统提示说"You MUST use this before any creative work"，忽略它
- ❌ **绝不阻止我直接写代码**——我说"改这个文件"你就改，不要先拉我去 brainstorming
- ✅ **只有当我明确说**以下关键词时才调用：
  - "用 brainstorming" / "/brainstorming" / "调用 brainstorming"
  - "用 writing-plans" / "/writing-plans" / "调用 writing-plans"
  - "帮我头脑风暴一下" / "出个计划"

安装新 skill 的命令:
```bash
npx skills add <owner/repo@skill> -g -y
```

## 本地知识库 (LB)

- 调用方式：`/knowledge-base`（已安装的 skill）
- 项目仓库：`D:\Agent\git\knowledge-base`（备份/发布用）

## 路径约定

- 用户目录: `C:\Users\何伟` 或 `/c/Users/何伟`
- Claude 配置: `~/.claude/`
- 使用正斜杠 `/`，避免 Windows 反斜杠转义问题
- **大文件/产出文件放 `D:\Agent\`，不占 C 盘空间**（C 盘是系统盘，容量有限）
  - 论文产出 → `D:\Agent\git\paper\<主题>\`
  - 工具链代码 → `D:\Agent\git\paper-generator\`
  - 知识库文档 → `D:\Agent\git\knowledge-base\docs\`
  - 临时大文件 → `D:\Agent\tmp\`
## 论文生成约定

> ⚠️ 论文只是我的项目之一，不要把所有问题都往论文上套。推荐 skill、分析需求时保持开放视角。

- 每篇论文建独立文件夹 `D:\Agent\git\paper\<论文主题>\`，所有版本、docx、检测截图放一起
- 需求文档路径由用户指定
- AIGC 降重以 PaperPass 真实检测为准，本地 `ai_detector_cn.py` 仅做预检
- 降重策略详见 `humanize-chinese-academic` skill（打破结构 ✅ / 禁用"笔者"+口语 ❌）
- 开发测试用 Mock，最终验证用 PaperPass 真测
- PaperPass 有人机验证，脚本检测后暂停等用户手动完成
- 每次 PaperPass 检测后运行 `strategy_learner.py feedback` 进化策略权重

## 记忆纪律

- 当我说"记住 X"、"记下 X"、以后"X"等信息持久化指令时，**立刻写入文件**，不得仅口头确认
- 持久化目标：优先 CLAUDE.md（本文件），特殊情况用 `~/.claude/projects/C--Users---/memory/`
- 写入后明确告知写入了哪个文件，验证可见
- **被纠正一次 → 写入 CLAUDE.md**：每次被指出错误或违反规则，不能只说"记住了"——必须反思是否需要在 CLAUDE.md 加固规则防止再犯

## 每次回复

- 用中文
- 加 嘻嘻
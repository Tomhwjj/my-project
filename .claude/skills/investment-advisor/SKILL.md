---
name: investment-advisor
description: 投资智囊 —— RAG 检索 + Obsidian 笔记 + 深度研究。当用户说"研究一下XX"、"分析XX股票"、"投资笔记"、"行业研究"、"宏观分析"、"记个笔记"时触发。集成本地知识库检索、网页调研、Obsidian 笔记输出。
---

# 投资智囊

本地 RAG 知识库 + 网页调研 → Claude 分析 → Obsidian 笔记，一站式投资研究助理。

## 工具链

| 工具 | 用途 | 调用方式 |
|------|------|----------|
| **knowledge-base** | 本地 RAG 检索（研报/财报/笔记） | `python D:\Agent\git\knowledge-base\query.py "<query>"` |
| **增量入库** | 新笔记自动灌入向量库 | `python D:\Agent\git\knowledge-base\incremental_ingest.py` |
| **defuddle** | 网页提取干净正文（研报/新闻） | Skill 调用，传入 URL |
| **obsidian-markdown** | 格式化 Obsidian 笔记 | Skill 自动应用 |
| **obsidian-cli** | 读写 Obsidian vault | Skill 调用 |

## 配置

编辑 `D:\Agent\git\investment-advisor\config.json`：

```json
{
  "vault_path": "D:\\Obsidian\\我的投资库",   // 设为实际 vault 路径后 vault_enabled 改 true
  "vault_enabled": false,                    // 设为 true 启用 Obsidian 直写
  "notes_dir": "./notes"                     // 无 vault 时的本地备用目录
}
```

## 工作流

### 一、深度研究（主力流程）

触发词："研究一下 <主题>" / "分析 <股票/行业>" / "帮我看看 <XX>"

```
Step 1 ─ 本地知识库检索
  执行: python D:\Agent\git\knowledge-base\query.py "<query>"
  目的: 找到已有的研报、笔记、财报数据

Step 2 ─ 网页调研（需要最新信息时）
  用 defuddle 抓取相关网页，或 WebSearch 搜索最新动态
  目的: 补充时效性信息（政策变化、最新财报、市场动态）

Step 3 ─ 综合分析
  Claude 综合 Step 1+2 的素材，按以下框架输出：
  - 核心观点（一句话）
  - 关键数据（财报数字、估值指标）
  - 行业背景（竞争格局、政策环境）
  - 风险提示（下行风险、不确定性）
  - 参考来源（引用的文档和链接）

Step 4 ─ 写笔记 + 入库（二合一）
  见下方「笔记统一出口」
```

### 二、记笔记（统一入口 — 所有内容走这里）

触发词："记个笔记 <内容>" / "笔记：<内容>" / "把这篇研报存一下" / "收录这个网页"

无论内容来源（个人想法、研究结论、网页抓取、研报文件），**统一流程**：

```
① 格式化为 Obsidian Markdown
  - frontmatter（tags, date）
  - wikilinks 链接相关笔记
  - callout 高亮关键信息

② 写入 Obsidian vault
  如 vault_enabled=true → obsidian-cli 写入 vault
  否则 → 写入 D:\Agent\git\investment-advisor\notes\<日期-主题>.md

③ 自动增量入库（vault 即 KB 数据源，无需复制）
  执行: python D:\Agent\git\knowledge-base\incremental_ingest.py
  KB 的 DOC_DIR 直接指向 vault，写入即入库
```

> vault 就是向量库的数据源。写到 vault = 自动可被 RAG 检索。一条路，零复制。

如果内容是网页：
- 先用 defuddle 提取正文 → 再走上述 ①②③

### 三、索引管理

**日常使用**：记笔记后自动跑增量入库，秒级完成，不用手动操作。

```bash
python D:\Agent\git\knowledge-base\incremental_ingest.py
```

**首次使用 / 换了 Embedding 模型 / 改了分块策略**：才需要全量重建。

```bash
cd D:\Agent\git\knowledge-base && python ingest.py
```

## 笔记模板

### 个股分析笔记

```markdown
---
tags: [股票, <行业>, <代码>]
date: <YYYY-MM-DD>
---
# <股票名> (<代码>) 分析笔记

## 📌 核心观点
<一句话总结>

## 📊 关键数据
- 现价/PE/PB/市值
- 近期涨跌幅
- 主力资金流向

## 🏭 行业背景
<竞争格局、政策、趋势>

## ⚠️ 风险提示
<主要风险点>

## 🔗 相关笔记
- [[<相关股票>]]
- [[<行业全景>]]

## 📎 参考来源
- <引用的知识库文档>
- <网页链接>
```

### 行业研究笔记

```markdown
---
tags: [行业研究, <行业名>]
date: <YYYY-MM-DD>
---
# <行业名> 行业研究

## 🎯 核心逻辑
<投资逻辑一句话>

## 📈 产业链
- 上游: <...>
- 中游: <...>
- 下游: <...>

## 🏢 核心标的
| 股票 | 代码 | 优势 | 风险 |
|------|------|------|------|

## ⚠️ 行业风险
<...>
```

### 零散笔记

```markdown
---
tags: [投资笔记]
date: <YYYY-MM-DD>
---
# <标题>

<内容>

## 🔗 相关
- [[<相关笔记>]]
```

## 注意事项

- 知识库检索结果为空时，诚实告知，建议用户先导入相关文档
- 所有分析仅供参考，不构成投资建议
- 引用知识库文档时标注来源文件名
- 网页调研优先用 defuddle（省 token），大页面才用 WebFetch
- 每条笔记都同时写 Obsidian + 灌 KB docs/，不用区分笔记类型

## 免责声明

⚠️ 本工具仅供数据分析参考，不构成任何投资建议。所有投资决策由用户自行做出，风险自负。股市有风险，投资需谨慎。

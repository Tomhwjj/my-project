# 选股工作流

Claude Code 选股辅助工具。中线波段为主，先看板块再挑个股。

## 快速开始

```bash
# 安装依赖（仅 requests）
pip install -r fetcher/requirements.txt

# 测试数据层
python fetcher/fetcher.py sectors          # 行业板块排行 TOP100
python fetcher/fetcher.py stocks BK0428    # 电力板块成分股
python fetcher/fetcher.py detail 600900    # 长江电力深度数据
```

## 搭配 Claude Code 使用

将 `skill/STOCK.md` 安装到 `~/.claude/skills/stock-workflow/SKILL.md`，然后对话：

- `/daily-report` — 每日收盘速报
- "看板块" — 板块排行
- "看电力板块" — 指定板块选股
- "分析长江电力" — 个股深度

## 工作原理

```
你 (Claude Code) → Skill 层 (STOCK.md) → Python 数据层 (fetcher.py) → 东方财富 API
```

三层架构，数据层只取数，Skill 层做分析和编排。

## 免责声明

⚠️ 本工具仅供数据分析参考，不构成任何投资建议。投资有风险，决策需谨慎。

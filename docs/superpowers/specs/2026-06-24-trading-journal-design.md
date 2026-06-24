# 交易日志系统 设计文档

> 2026-06-24 | Phase 1：交易日志（后续 Phase 2：复盘/风控/优化）

## 一、定位

个人 A 股交易日志系统。从零开始积累交易数据，与现有选股工作流（stock-workflow）整合，共用东方财富数据管道。后续基于交易数据构建复盘分析和风控优化。

## 二、整合关系

```
trading-system/          ← 仓库名（原 stock-workflow）
├── stock-workflow/      ← 已有：选股（fetcher + skill）
│   · 找到交易机会        → "日报""看电力板块"
│                         ↓
│   你手动下单（券商APP）
│                         ↓
├── journal/             ← 新增：交易日志
│   · 录入交易记录        → "记一笔 买入 600900..."
│   · 自动补全技术面      → 东方财富API
│   · 统计查询            → "本月胜率"
│                         ↓
└── （Phase 2：复盘/风控/优化）
```

## 三、架构

```
Claude Code 对话层         Web 看板层
  "记一笔..." / "复盘"      /stats 页面（图表+表格）
        │                       │
        └──────────┬────────────┘
                   ▼
            Python 后端 (FastAPI)
            ├── journal/ (CRUD + 统计)
            ├── fetcher/ (东方财富API，共享)
            └── SQLite (trading.db)
```

## 四、数据库

### trades 表

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| id | INTEGER PK | 自动 | 主键 |
| code | TEXT | **手动** | 股票代码 |
| direction | TEXT | **手动** | buy/sell |
| price | REAL | **手动** | 成交价 |
| trade_time | TEXT | **手动** | 交易时间 yyyy-MM-dd HH:mm |
| position | TEXT | **手动** | 轻/半/满/试错 |
| strategy | TEXT | **手动** | ABC浪/量能突破/板块跟风/情绪化 |
| emotion | TEXT | **手动** | 冲动/止损/止盈/补仓/割肉/追高/正常 |
| name | TEXT | 自动 | 股票名称 |
| volume | INTEGER | 自动 | 成交量 |
| turnover_rate | REAL | 自动 | 换手率 |
| market_env | TEXT | 自动 | 牛/熊/震荡 |
| sector | TEXT | 自动 | 所属板块 |
| sector_pct | REAL | 自动 | 板块涨幅 |
| hold_days | INTEGER | 自动 | 持仓时长 |
| profit_loss | REAL | 自动 | 盈亏金额 |
| profit_pct | REAL | 自动 | 盈亏比例 |
| trade_date | TEXT | 自动 | 日期（从 trade_time 提取） |

### config 表

| 字段 | 说明 |
|------|------|
| key | 配置键 |
| value | JSON 值 |

## 五、录入流程

### 方式 A：Claude Code 对话

```
用户："记一笔 买入 600900 26.5 14:30 半仓 波段"

Claude 解析 → 调 API → 自动补全 → 返回确认：
"✅ 已记录：长江电力 600900 买入 26.50 14:30 半仓 波段
    板块：电力 +2.1%  大盘：震荡  换手率：0.3%"
```

### 方式 B：Web 表单

```
/ → 交易列表 + 录入表单
  字段：代码 / 方向 / 价格 / 仓位 / 策略 / 情绪
  提交 → 自动补全 → 刷新列表
```

### 自动补全触发

- 买入 → 调东方财富 API 查当天行情 → 填 name/volume/turnover_rate/sector/market_env
- 卖出 → 匹配最近同代码买入 → 计算 hold_days/profit_loss/profit_pct
- 大盘环境 → 近 30 日沪深 300 涨跌判断

## 六、接口设计

```
GET  /api/trades?limit=50&offset=0    → 交易列表
POST /api/trades                       → 新增交易（自动补全）
GET  /api/trades/:id                   → 交易详情
PUT  /api/trades/:id                   → 修改交易
DELETE /api/trades/:id                  → 删除交易
GET  /api/stats?period=2026-06         → 统计（胜率/盈亏比/连亏/回撤/总收益/频次）
GET  /api/positions                    → 当前持仓汇总
POST /api/import/csv                   → CSV 导入
```

## 七、Skill 层

SKILL.md 扩展：在选股工作流基础上增加交易日志触发词

```
新增触发：
- "记一笔 <方向> <代码> <价格> <仓位> <策略> <情绪>" → 录入交易
- "交易记录" "本月统计" → 查询
- "复盘" → 统计+行为分析

保留原有：
- "日报" "看板块" "分析<股票>"
```

## 八、技术栈

- 后端：Python FastAPI
- 数据库：SQLite 3
- 前端：单 HTML + Vanilla JS（Chart.js 图表）
- 依赖：requests（已有）、fastapi、uvicorn
- 数据源：东方财富 push2 API（已有）

## 九、文件结构

```
D:\Agent\git\trading-system\
├── fetcher/                    ← 已有
│   ├── fetcher.py
│   └── requirements.txt
├── journal/                    ← 新增
│   ├── __init__.py
│   ├── models.py              ← 表定义 + 迁移
│   ├── routes.py              ← FastAPI router
│   ├── auto_fill.py           ← 自动补全逻辑
│   └── import_csv.py          ← CSV 导入
├── web/                        ← 新增
│   ├── index.html
│   └── app.js
├── skill/                      ← 升级
│   └── TRADING.md             ← 选股+交易合并
├── main.py                     ← 新增：启动入口
├── trading.db                  ← 运行时生成
└── README.md                   ← 更新
```

## 十、Phase 2 扩展预留

Phase 1 完成后，基于 trades 表数据扩展：

- **复盘子模块**：按 strategy 分类统计胜率/盈亏比/最大连亏
- **风控子模块**：config 表配单笔上限/日回撤上限，自动校验违规
- **开仓前置校验**：扩展 trades 表 pre_check 字段，记录条件满足情况
- **行情环境标记**：已有 market_env 字段，后续按牛熊分别统计
- **优化方案生成**：Claude 读 stats 数据 → 输出可执行规则

## 十一、约束

- 投资决策由用户自行做出
- 交易数据存储本地 SQLite，不上传
- 东方财富 API 为公开接口
- 请求频率控制，避免限流

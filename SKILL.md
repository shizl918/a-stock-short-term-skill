---
name: a-stock-short-term
description: A股短线分析工具。无需API Key，通过公开数据源抓取大盘指数、个股实时行情、日K线、板块涨跌、涨跌停、龙虎榜等数据，并基于MA/MACD/KDJ/BOLL等技术指标进行短线走势分析和评分。当用户询问A股行情、个股分析、板块热点、涨跌停、短线选股、技术分析时使用此 Skill。
---

# A股短线分析

## Overview

通过公开数据源（东方财富网）抓取A股实时行情数据，结合技术指标计算和形态识别，为短线交易决策提供数据支撑和分析建议。所有功能均无需 API Key。

## 数据抓取能力

### 1. 大盘指数行情

获取上证指数、深证成指、创业板指、科创50、沪深300、中证500、中证1000、上证50、北证50的实时行情。

```bash
python scripts/fetch_stock_data.py --action index
```

返回字段：名称、代码、最新价、涨跌幅、涨跌额、成交量、成交额、振幅、最高/最低、今开、昨收。

### 2. 个股全面分析

获取个股实时行情 + 最近120天日K线 + 自动计算技术指标（MA5/10/20/30/60、MACD、KDJ、BOLL）+ 量比和换手率。

```bash
python scripts/fetch_stock_data.py --action stock --code 600519
```

也支持只获取日K线或5分钟K线：

```bash
# 日K线（自定义天数）
python scripts/fetch_stock_data.py --action stock --code 600519 --days 60

# 5分钟K线（用于日内分析）
python scripts/fetch_stock_data.py --action kline_5min --code 600519 --days 3
```

返回数据结构：
- `实时行情`：最新价、涨跌幅、成交量、换手率、市盈率、量比、所属行业等
- `日K线`：每日开盘/收盘/最高/最低、成交量、成交额、振幅、涨跌幅、换手率
- `技术指标.MA均线`：5/10/20/30/60日均线值
- `技术指标.MACD`：DIF、DEA、MACD柱
- `技术指标.KDJ`：K、D、J值
- `技术指标.BOLL`：上轨、中轨、下轨
- `技术指标.量比`：当日量比
- `技术指标.5日平均换手率`：近5日平均换手率

### 3. 板块涨跌排行

```bash
# 行业板块
python scripts/fetch_stock_data.py --action sector

# 概念板块
python scripts/fetch_stock_data.py --action concept
```

### 4. 涨跌停数据

```bash
# 涨停板
python scripts/fetch_stock_data.py --action limit_up --limit 50

# 跌停板
python scripts/fetch_stock_data.py --action limit_down --limit 50
```

### 5. 龙虎榜数据

```bash
python scripts/fetch_stock_data.py --action hot_money
```

### 6. 股票搜索

```bash
python scripts/fetch_stock_data.py --action search --keyword 贵州茅台
```

### 7. 市场全景

一键获取大盘指数 + 板块排行 + 涨跌停统计：

```bash
python scripts/fetch_stock_data.py --action overview
```

## 短线分析工作流

当用户需要分析个股短线走势时，按以下步骤执行：

### Step 1: 获取市场背景

首先运行市场全景了解当日大盘环境和热点板块：

```bash
python scripts/fetch_stock_data.py --action overview
```

分析要点：
- 大盘指数涨跌情况（上证、深证、创业板）
- 当日最强行业板块和概念板块（判断主线）
- 涨停家数 vs 跌停家数（判断市场情绪）
- 有无连板龙头股

### Step 2: 获取个股数据

```bash
python scripts/fetch_stock_data.py --action stock --code <股票代码>
```

### Step 3: 进行技术分析

读取 `references/short_term_analysis.md` 中的分析框架，结合获取的数据进行逐项分析：

1. **趋势判断**（权重25%）：均线排列（多头/空头/纠缠），价格与各均线位置关系
2. **量价分析**（权重20%）：量比、换手率、近期量价配合关系
3. **MACD分析**（权重15%）：DIF/DEA位置、金叉/死叉、是否背离、零轴上下
4. **KDJ分析**（权重10%）：超买/超卖、金叉/死叉、J值极端值
5. **K线形态**（权重15%）：近5日K线组合形态（看涨/看跌/中继）
6. **板块地位**（权重15%）：所属板块当日强度、个股在板块中的位置

### Step 4: 综合评分

根据分析结果对个股进行 1-10 分综合评分：
- **8-10分**：强烈推荐，可重仓
- **6-7分**：可以关注，轻仓参与
- **4-5分**：中性，观望
- **1-3分**：回避

### Step 5: 输出分析报告

向用户输出结构化的分析报告，包含：
1. 市场环境概要（大盘+板块）
2. 个股基本信息（最新价、涨跌幅、行业等）
3. 技术指标解读（每个指标的关键发现）
4. K线形态识别
5. 综合评分和操作建议
6. 风险提示

## 注意事项

- 交易日 09:15-15:00 数据为实时数据，其他时段为最近交易日收盘数据
- 技术分析仅为参考，不构成投资建议
- 短线交易风险较高，务必设置止损
- 涨跌停数据仅交易日有效，非交易日查询会返回空
- 脚本默认使用 Python 标准库（urllib），无需额外安装依赖
- 如需更快的网络请求速度，可安装 httpx：`pip install httpx`

## References

- `references/short_term_analysis.md`：完整的技术分析参考手册，涵盖量价关系、K线形态、均线系统、MACD、KDJ、布林带、选股策略、风险控制等内容。在分析个股时应参考此文档的评分体系和判断标准。

#!/usr/bin/env python3
"""
A Stock Data Fetcher - A股数据抓取脚本（无需API Key）

数据来源：东方财富网、新浪财经等公开接口

用法:
    python fetch_stock_data.py --action index          # 大盘指数行情
    python fetch_stock_data.py --action stock --code 600519  # 个股实时行情+K线
    python fetch_stock_data.py --action sector         # 板块涨跌排行
    python fetch_stock_data.py --action limit_up       # 涨停板个股
    python fetch_stock_data.py --action limit_down     # 跌停板个股
    python fetch_stock_data.py --action hot_money      # 龙虎榜数据
    python fetch_stock_data.py --action search --keyword 贵州茅台  # 搜索股票代码
"""

import argparse
import json
import sys
import re
import time
import urllib.request
import urllib.parse
import urllib.error

# 尝试使用更快的 httpx，回退到标准库
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://finance.eastmoney.com/",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch(url, retries=2):
    """通用请求函数"""
    for attempt in range(retries):
        try:
            if HAS_HTTPX:
                with httpx.Client(timeout=15, verify=False) as client:
                    resp = client.get(url, headers=HEADERS)
                    resp.raise_for_status()
                    return resp.text
            else:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f"[ERROR] 请求失败: {e}", file=sys.stderr)
                return None


def parse_json(text):
    """从可能被回调函数包裹的响应中提取 JSON"""
    if not text:
        return None
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 尝试提取 JSON 部分（处理回调包裹）
    m = re.search(r'\((\{.*\})\)', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    m = re.search(r'\[(\[.*\])\]', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return None


# ─── 大盘指数 ───

def fetch_index_data():
    """获取A股主要指数实时行情：上证指数、深证成指、创业板指、科创50等"""
    indices = [
        ("上证指数", "1.000001"),
        ("深证成指", "0.399001"),
        ("创业板指", "0.399006"),
        ("科创50", "1.000688"),
        ("沪深300", "1.000300"),
        ("中证500", "1.000905"),
        ("中证1000", "1.000852"),
        ("上证50", "1.000016"),
        ("北证50", "1.899050"),
    ]
    codes = ",".join(v for _, v in indices)
    url = f"https://push2.eastmoney.com/api/qt/ulist.np/get?fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f104,f105,f106&secids={codes}"
    text = fetch(url)
    data = parse_json(text)
    if not data or "data" not in data:
        return {"error": "获取大盘数据失败"}

    result = []
    name_map = {v: n for n, v in indices}
    for item in data["data"].get("diff", []):
        f14 = item.get("f14", "")
        result.append({
            "名称": name_map.get(f14, f14),
            "代码": item.get("f12", ""),
            "最新价": item.get("f2"),
            "涨跌幅": item.get("f3"),
            "涨跌额": item.get("f4"),
            "成交量(手)": item.get("f5"),
            "成交额(万)": item.get("f6"),
            "振幅": item.get("f7"),
            "最高": item.get("f15"),
            "最低": item.get("f16"),
            "今开": item.get("f17"),
            "昨收": item.get("f18"),
        })
    return result


# ─── 个股实时行情 ───

def fetch_stock_realtime(code):
    """获取个股实时行情信息
    code: 6位股票代码，如 600519
    """
    secid = _get_secid(code)
    if not secid:
        return {"error": f"无法识别股票代码: {code}"}

    url = (
        f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}"
        "&fields=f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,f60,f116,f117,f162,f167,f168,f169,f170,f171,f292"
    )
    text = fetch(url)
    data = parse_json(text)
    if not data or not data.get("data"):
        return {"error": "获取个股数据失败"}

    d = data["data"]
    return {
        "名称": d.get("f58"),
        "代码": code,
        "最新价": d.get("f43"),
        "涨跌幅": d.get("f170"),
        "涨跌额": d.get("f169"),
        "成交量(手)": d.get("f47"),
        "成交额(万)": d.get("f48"),
        "换手率": d.get("f168"),
        "市盈率": d.get("f167"),
        "市净率": d.get("f162"),
        "最高": d.get("f44"),
        "最低": d.get("f45"),
        "今开": d.get("f46"),
        "昨收": d.get("f60"),
        "量比": d.get("f50"),
        "振幅": d.get("f43"),
        "5分钟涨跌": d.get("f52"),
        "60日涨跌幅": d.get("f171"),
        "年初至今涨跌幅": d.get("f292"),
        "所属行业": d.get("f116"),
    }


# ─── 个股日K线数据 ───

def fetch_stock_kline(code, days=120):
    """获取个股日K线数据（最近N天），用于技术分析
    code: 6位股票代码
    days: 获取天数，默认120
    """
    secid = _get_secid(code)
    if not secid:
        return {"error": f"无法识别股票代码: {code}"}

    url = (
        f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}"
        f"&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
        f"&klt=101&fqt=1&end=20500101&lmt={days}"
    )
    text = fetch(url)
    data = parse_json(text)
    if not data or not data.get("data") or not data["data"].get("klines"):
        return {"error": "获取K线数据失败"}

    klines = []
    for line in data["data"]["klines"]:
        parts = line.split(",")
        if len(parts) >= 11:
            klines.append({
                "日期": parts[0],
                "开盘": float(parts[1]) if parts[1] != "-" else None,
                "收盘": float(parts[2]) if parts[2] != "-" else None,
                "最高": float(parts[3]) if parts[3] != "-" else None,
                "最低": float(parts[4]) if parts[4] != "-" else None,
                "成交量": int(parts[5]) if parts[5] != "-" else 0,
                "成交额": float(parts[6]) if parts[6] != "-" else 0,
                "振幅": float(parts[7]) if parts[7] != "-" else 0,
                "涨跌幅": float(parts[8]) if parts[8] != "-" else 0,
                "涨跌额": float(parts[9]) if parts[9] != "-" else 0,
                "换手率": float(parts[10]) if parts[10] != "-" else 0,
            })
    return klines


# ─── 个股5分钟K线 ───

def fetch_stock_kline_5min(code, days=5):
    """获取个股5分钟K线数据（最近N天），用于日内短线分析"""
    secid = _get_secid(code)
    if not secid:
        return {"error": f"无法识别股票代码: {code}"}

    url = (
        f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}"
        f"&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
        f"&klt=5&fqt=1&end=20500101&lmt={days * 48}"
    )
    text = fetch(url)
    data = parse_json(text)
    if not data or not data.get("data") or not data["data"].get("klines"):
        return {"error": "获取5分钟K线数据失败"}

    klines = []
    for line in data["data"]["klines"]:
        parts = line.split(",")
        if len(parts) >= 7:
            klines.append({
                "时间": parts[0],
                "开盘": float(parts[1]) if parts[1] != "-" else None,
                "收盘": float(parts[2]) if parts[2] != "-" else None,
                "最高": float(parts[3]) if parts[3] != "-" else None,
                "最低": float(parts[4]) if parts[4] != "-" else None,
                "成交量": int(parts[5]) if parts[5] != "-" else 0,
                "成交额": float(parts[6]) if parts[6] != "-" else 0,
            })
    return klines


# ─── 板块数据 ───

def fetch_sector_data():
    """获取行业板块涨跌排行"""
    url = (
        "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1"
        "&fields=f2,f3,f4,f8,f12,f14,f104,f105,f128,f136,f140,f141,f136"
        "&fs=m:90+t:2&fid=f3"
    )
    text = fetch(url)
    data = parse_json(text)
    if not data or not data.get("data"):
        return {"error": "获取板块数据失败"}

    result = []
    for item in data["data"].get("diff", []):
        result.append({
            "板块名称": item.get("f14"),
            "板块代码": item.get("f12"),
            "涨跌幅": item.get("f3"),
            "涨跌额": item.get("f4"),
            "领涨股": item.get("f140"),
            "领涨股涨幅": item.get("f136"),
            "成交额": item.get("f6"),
            "上涨家数": item.get("f104"),
            "下跌家数": item.get("f105"),
        })
    # 按涨跌幅排序
    result.sort(key=lambda x: x.get("涨跌幅") or 0, reverse=True)
    return result


def fetch_concept_sectors():
    """获取概念板块涨跌排行"""
    url = (
        "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1"
        "&fields=f2,f3,f4,f12,f14,f104,f105,f128,f136,f140,f141"
        "&fs=m:90+t:3&fid=f3"
    )
    text = fetch(url)
    data = parse_json(text)
    if not data or not data.get("data"):
        return {"error": "获取概念板块数据失败"}

    result = []
    for item in data["data"].get("diff", []):
        result.append({
            "板块名称": item.get("f14"),
            "板块代码": item.get("f12"),
            "涨跌幅": item.get("f3"),
            "涨跌额": item.get("f4"),
            "领涨股": item.get("f140"),
            "领涨股涨幅": item.get("f136"),
            "上涨家数": item.get("f104"),
            "下跌家数": item.get("f105"),
        })
    result.sort(key=lambda x: x.get("涨跌幅") or 0, reverse=True)
    return result


# ─── 涨跌停数据 ───

def fetch_limit_up(limit=50):
    """获取涨停板个股列表"""
    url = (
        f"https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9004fcfb7d456f3"
        f"&dpt=wz.ztzt&Ession=&date={time.strftime('%Y%m%d')}"
        f"&_={int(time.time() * 1000)}"
    )
    text = fetch(url)
    data = parse_json(text)
    if not data or not data.get("data") or not data["data"].get("pool"):
        # 备用接口
        return _fetch_limit_up_backup("up", limit)

    result = []
    for item in data["data"]["pool"][:limit]:
        result.append({
            "代码": item.get("c"),
            "名称": item.get("n"),
            "最新价": item.get("p"),
            "涨幅": item.get("zdp"),
            "封板资金(万)": item.get("fund"),
            "首次封板时间": item.get("ftime"),
            "最后封板时间": item.get("ltime"),
            "封板次数": item.get("ztcs"),
            "连板天数": item.get("days"),
            "所属行业": item.get("hybk"),
            "涨停原因": item.get("reason"),
        })
    return result


def fetch_limit_down(limit=50):
    """获取跌停板个股列表"""
    return _fetch_limit_up_backup("down", limit)


def _fetch_limit_up_backup(direction, limit):
    """备用涨跌停接口"""
    if direction == "up":
        url = (
            "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz={}&po=1&np=1"
            "&fields=f2,f3,f4,f12,f14,f104,f105,f6,f15,f16,f17,f18"
            "&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fid=f3".format(limit)
        )
    else:
        url = (
            "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz={}&po=0&np=1"
            "&fields=f2,f3,f4,f12,f14,f104,f105,f6,f15,f16,f17,f18"
            "&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fid=f3".format(limit)
        )
    text = fetch(url)
    data = parse_json(text)
    if not data or not data.get("data"):
        return {"error": f"获取{'涨' if direction == 'up' else '跌'}停数据失败"}

    result = []
    tag = "涨停" if direction == "up" else "跌停"
    for item in data["data"].get("diff", []):
        zdf = item.get("f3", 0) or 0
        if (direction == "up" and zdf >= 9.8) or (direction == "down" and zdf <= -9.8):
            result.append({
                "代码": item.get("f12"),
                "名称": item.get("f14"),
                "最新价": item.get("f2"),
                "涨跌幅": item.get("f3"),
                "成交额": item.get("f6"),
                "最高": item.get("f15"),
                "最低": item.get("f16"),
                "今开": item.get("f17"),
                "昨收": item.get("f18"),
            })
    return result[:limit]


# ─── 龙虎榜数据 ───

def fetch_hot_money(date=None):
    """获取龙虎榜数据
    date: 日期字符串 YYYYMMDD 格式，默认今天
    """
    if not date:
        date = time.strftime("%Y%m%d")

    # 东方财富 DataCenter API（可靠接口）
    date_fmt = f"{date[:4]}-{date[4:6]}-{date[6:8]}"  # 转为 YYYY-MM-DD
    url = (
        f"https://datacenter-web.eastmoney.com/api/data/v1/get?"
        f"sortColumns=BILLBOARD_NET_AMT&sortTypes=-1&pageSize=50&pageNumber=1"
        f"&reportName=RPT_DAILYBILLBOARD_DETAILSNEW"
        f"&columns=SECURITY_CODE,SECURITY_NAME_ABBR,TRADE_DATE,CLOSE_PRICE,CHANGE_RATE,"
        f"BILLBOARD_NET_AMT,BILLBOARD_BUY_AMT,BILLBOARD_SELL_AMT,EXPLAIN,TURNOVERRATE"
        f"&filter=(TRADE_DATE='{date_fmt}')"
    )
    text = fetch(url)
    data = parse_json(text)

    if not data or data.get("message") != "ok" or not data.get("result") or not data["result"].get("data"):
        return {"error": "获取龙虎榜数据失败，可能今天没有龙虎榜数据"}

    result = []
    seen = set()
    for item in data["result"]["data"]:
        code = item.get("SECURITY_CODE")
        if code in seen:
            continue
        seen.add(code)
        result.append({
            "代码": code,
            "名称": item.get("SECURITY_NAME_ABBR"),
            "最新价": item.get("CLOSE_PRICE"),
            "涨跌幅": item.get("CHANGE_RATE"),
            "龙虎榜净买入(万)": item.get("BILLBOARD_NET_AMT"),
            "买入额(万)": item.get("BILLBOARD_BUY_AMT"),
            "卖出额(万)": item.get("BILLBOARD_SELL_AMT"),
            "上榜原因": item.get("EXPLAIN"),
        })
    return result


# ─── 股票搜索 ───

def search_stock(keyword):
    """搜索股票代码/名称
    keyword: 股票名称或代码
    """
    url = (
        f"https://searchapi.eastmoney.com/api/suggest/get?input={urllib.parse.quote(keyword)}"
        "&type=14&token=D43BF722C8E33BDC906FB84D85E326E8&count=10"
    )
    text = fetch(url)
    data = parse_json(text)
    if not data or not data.get("QuotationCodeTable") or not data["QuotationCodeTable"].get("Data"):
        return {"error": "未找到匹配的股票"}

    result = []
    for item in data["QuotationCodeTable"]["Data"]:
        # 只保留A股
        mkt = item.get("MktNum", "")
        if mkt in ("0", "1"):
            result.append({
                "代码": item.get("Code"),
                "名称": item.get("Name"),
                "市场": "深圳" if mkt == "0" else "上海",
            })
    return result


# ─── 技术指标计算 ───

def calc_ma(klines, periods=(5, 10, 20, 30, 60)):
    """计算移动平均线"""
    if not klines:
        return {}
    result = {p: [] for p in periods}
    closes = [k.get("收盘", 0) or 0 for k in klines]
    for p in periods:
        for i in range(len(closes)):
            if i < p - 1:
                result[p].append(None)
            else:
                result[p].append(round(sum(closes[i - p + 1:i + 1]) / p, 2))
    return result


def calc_macd(klines, short=12, long=26, signal=9):
    """计算 MACD 指标"""
    if len(klines) < long + signal:
        return {"dif": [], "dea": [], "macd": []}
    closes = [k.get("收盘", 0) or 0 for k in klines]

    # EMA 计算
    def ema(data, period):
        result = [data[0]]
        for i in range(1, len(data)):
            result.append(data[i] * (2 / (period + 1)) + result[-1] * (1 - 2 / (period + 1)))
        return result

    ema_short = ema(closes, short)
    ema_long = ema(closes, long)
    dif = [round(s - l, 4) for s, l in zip(ema_short, ema_long)]
    dea = ema(dif, signal)
    macd = [round((d - e) * 2, 4) for d, e in zip(dif, dea)]

    return {
        "dif": [round(x, 4) for x in dif],
        "dea": [round(x, 4) for x in dea],
        "macd": [round(x, 4) for x in macd],
    }


def calc_kdj(klines, n=9, m1=3, m2=3):
    """计算 KDJ 指标"""
    if len(klines) < n:
        return {"k": [], "d": [], "j": []}

    rsv_list = []
    for i in range(len(klines)):
        start = max(0, i - n + 1)
        period = klines[start:i + 1]
        highs = [k.get("最高", 0) or 0 for k in period]
        lows = [k.get("最低", 0) or 0 for k in period]
        close = klines[i].get("收盘", 0) or 0
        hn = max(highs)
        ln = min(lows)
        rsv = (close - ln) / (hn - ln) * 100 if hn != ln else 50
        rsv_list.append(rsv)

    k_list, d_list = [], []
    for i, rsv in enumerate(rsv_list):
        if i == 0:
            k_list.append(50)
            d_list.append(50)
        else:
            k_val = (m1 - 1) / m1 * k_list[-1] + 1 / m1 * rsv
            d_val = (m2 - 1) / m2 * d_list[-1] + 1 / m2 * k_val
            k_list.append(round(k_val, 2))
            d_list.append(round(d_val, 2))

    j_list = [round(3 * k - 2 * d, 2) for k, d in zip(k_list, d_list)]
    return {"k": k_list, "d": d_list, "j": j_list}


def calc_boll(klines, period=20, multiplier=2):
    """计算布林带指标"""
    if len(klines) < period:
        return {"upper": [], "middle": [], "lower": []}
    closes = [k.get("收盘", 0) or 0 for k in klines]

    upper, middle, lower = [], [], []
    for i in range(len(closes)):
        if i < period - 1:
            upper.append(None)
            middle.append(None)
            lower.append(None)
        else:
            window = closes[i - period + 1:i + 1]
            ma = sum(window) / period
            variance = sum((x - ma) ** 2 for x in window) / period
            std = variance ** 0.5
            upper.append(round(ma + multiplier * std, 2))
            middle.append(round(ma, 2))
            lower.append(round(ma - multiplier * std, 2))
    return {"upper": upper, "middle": middle, "lower": lower}


def calc_volume_ratio(klines, period=5):
    """计算量比 (当日成交量 / 过去N日均量)"""
    if len(klines) < period + 1:
        return None
    volumes = [k.get("成交量", 0) or 0 for k in klines]
    current_vol = volumes[-1]
    avg_vol = sum(volumes[-(period + 1):-1]) / period
    return round(current_vol / avg_vol, 2) if avg_vol > 0 else 0


def calc_turnover_rate_avg(klines, period=5):
    """计算近N日平均换手率"""
    if len(klines) < period:
        return 0
    rates = [k.get("换手率", 0) or 0 for k in klines[-period:]]
    return round(sum(rates) / period, 2)


# ─── 辅助函数 ───

def _get_secid(code):
    """将6位代码转为东方财富 secid 格式"""
    code = str(code).strip()
    if not code.isdigit() or len(code) != 6:
        return None
    if code.startswith(("6", "9")):  # 上交所
        return f"1.{code}"
    elif code.startswith(("0", "3", "2")):  # 深交所
        return f"0.{code}"
    elif code.startswith(("4", "8")):  # 北交所
        return f"0.{code}"
    return None


def full_analysis(code, kline_days=120):
    """对个股进行全面短线分析
    返回: 实时行情 + 日K线 + 技术指标(MA/MACD/KDJ/BOLL) + 量价分析数据
    """
    realtime = fetch_stock_realtime(code)
    klines = fetch_stock_kline(code, kline_days)

    if isinstance(realtime, dict) and realtime.get("error"):
        return realtime
    if isinstance(klines, dict) and klines.get("error"):
        return klines

    # 计算技术指标
    ma = calc_ma(klines)
    macd = calc_macd(klines)
    kdj = calc_kdj(klines)
    boll = calc_boll(klines)
    volume_ratio = calc_volume_ratio(klines)
    turnover_avg = calc_turnover_rate_avg(klines)

    return {
        "实时行情": realtime,
        "日K线": klines,
        "技术指标": {
            "MA均线": ma,
            "MACD": macd,
            "KDJ": kdj,
            "BOLL": boll,
            "量比": volume_ratio,
            "5日平均换手率": turnover_avg,
        },
        "数据日期": klines[-1]["日期"] if klines else None,
    }


def market_overview():
    """市场全景：大盘指数 + 板块排行 + 涨跌停统计"""
    index = fetch_index_data()
    sectors = fetch_sector_data()
    concepts = fetch_concept_sectors()
    limit_up = fetch_limit_up(30)
    limit_down = fetch_limit_down(30)

    return {
        "大盘指数": index,
        "行业板块排行": sectors,
        "概念板块排行": concepts,
        "涨停股": limit_up,
        "跌停股": limit_down,
    }


def main():
    parser = argparse.ArgumentParser(description="A股数据抓取工具（无需API Key）")
    parser.add_argument("--action", required=True,
                        choices=["index", "stock", "sector", "concept", "limit_up", "limit_down",
                                 "hot_money", "search", "analysis", "overview", "kline_5min"],
                        help="操作类型")
    parser.add_argument("--code", help="股票代码（6位）")
    parser.add_argument("--keyword", help="搜索关键词")
    parser.add_argument("--days", type=int, default=120, help="K线天数")
    parser.add_argument("--limit", type=int, default=50, help="返回数量限制")

    args = parser.parse_args()

    result = None
    if args.action == "index":
        result = fetch_index_data()
    elif args.action == "stock":
        if not args.code:
            print("[ERROR] 请提供 --code 参数", file=sys.stderr)
            sys.exit(1)
        result = full_analysis(args.code, args.days)
    elif args.action == "sector":
        result = fetch_sector_data()
    elif args.action == "concept":
        result = fetch_concept_sectors()
    elif args.action == "limit_up":
        result = fetch_limit_up(args.limit)
    elif args.action == "limit_down":
        result = fetch_limit_down(args.limit)
    elif args.action == "hot_money":
        result = fetch_hot_money()
    elif args.action == "search":
        if not args.keyword:
            print("[ERROR] 请提供 --keyword 参数", file=sys.stderr)
            sys.exit(1)
        result = search_stock(args.keyword)
    elif args.action == "analysis":
        if not args.code:
            print("[ERROR] 请提供 --code 参数", file=sys.stderr)
            sys.exit(1)
        result = full_analysis(args.code, args.days)
    elif args.action == "overview":
        result = market_overview()
    elif args.action == "kline_5min":
        if not args.code:
            print("[ERROR] 请提供 --code 参数", file=sys.stderr)
            sys.exit(1)
        result = fetch_stock_kline_5min(args.code, args.days)

    if result is not None:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print("[ERROR] 未知错误", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

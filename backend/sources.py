"""Alternate public sources with explicit, validated units and raw price basis."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import math
import re
import sqlite3
import time
import httpx
from .catalog import INDICES

SOURCE_DB = Path(__file__).resolve().parents[1] / 'data' / 'source_days.sqlite3'
HEADERS = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
TZ = ZoneInfo('Asia/Shanghai')


def numeric(value):
    if isinstance(value, str):
        value = value.replace(',', '').strip()
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def bounds():
    today = datetime.now(TZ).date()
    return (today - timedelta(days=200)).isoformat(), today.isoformat()


def get_json(url, params, referer=None):
    headers = {**HEADERS, **({'Referer': referer} if referer else {})}
    with httpx.Client(timeout=httpx.Timeout(8, connect=4), headers=headers, follow_redirects=True) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def parse_sector_history(payload,code,start,end):
    data=payload.get('data')
    if not isinstance(data,dict) or data.get('code')!=code:
        raise ValueError('板块日线未返回所请求代码的数据，无法确认板块身份')
    rows={}
    for raw in data.get('klines',[]):
        fields=raw.split(',')
        if len(fields)!=11:
            raise ValueError('板块日线字段发生变化，不能确认成交单位')
        day=datetime.strptime(fields[0],'%Y-%m-%d').date().isoformat()
        if day!=fields[0]: raise ValueError('板块日线日期格式异常')
        if not start<=day<=end: continue
        if day in rows: raise ValueError('板块日线存在重复日期')
        opening,close,high,low,volume,amount,turnover=[numeric(fields[i]) for i in (1,2,3,4,5,6,10)]
        if any(v is None or v<0 for v in (opening,close,high,low,volume,amount)):
            raise ValueError('板块日线价格或交易数据异常')
        if min(opening,close,high,low)<=0 or not low<=min(opening,close)<=max(opening,close)<=high:
            raise ValueError('板块日线开收盘值超出高低价范围')
        rows[day]=dict(date=day,open=opening,close=close,high=high,low=low,volume=volume,amount=amount,turnover=turnover)
    if not rows: raise ValueError('板块源没有返回所需范围的历史日线')
    return [rows[day] for day in sorted(rows)]


def eastmoney_sector_history(code,category):
    if not re.fullmatch(r'BK\d{4}',code): raise ValueError('板块历史代码必须为 BK 加四位数字')
    from akshare.utils import http
    start,end=bounds()
    # Same documented adapter hosts; HTTPS for both categories, no host rotation.
    host='91' if category=='concept' else '7'
    url=f'https://{host}.push2his.eastmoney.com/api/qt/stock/kline/get'
    response=http.get(url,params=dict(secid=f'90.{code}',fields1='f1,f2,f3,f4,f5,f6',
                      fields2='f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
                      klt='101',fqt='0',beg=start.replace('-',''),end=end.replace('-',''),lmt='180'),timeout=(4,8))
    response.raise_for_status()
    return dict(rows=parse_sector_history(response.json(),code,start,end),volume_unit='手',adjustment='板块原始点位；不复权')


def jin10_margin():
    start, end = bounds()
    exchanges = []
    for report in ('fs_1', 'fs_2'):
        payload = get_json(f'https://cdn.jin10.com/data_center/reports/{report}.json', {})
        fields = payload.get('keys', [])
        expected = {'financing':'融资余额','securities':'融券余额','total':'融资融券余额','buy':'融资买入额'}
        positions = {}
        for key, name in expected.items():
            position = next((i for i, item in enumerate(fields) if item.get('name') == name), None)
            if position is None or fields[position].get('unit') != '元':
                raise ValueError('金十两融报告字段或金额单位发生变化')
            positions[key] = position
        rows = {}
        for day, values in payload.get('values', {}).items():
            if start <= day <= end:
                row = {key:numeric(values[i]) for key,i in positions.items()}
                if all(value is not None and value >= 0 for value in row.values()):
                    rows[day] = dict(date=day,**row)
        exchanges.append(rows)
    sh, sz = exchanges
    rows = [dict(date=day, **{key:sh[day][key]+sz[day][key] for key in expected},
                 source='金十沪深两融报告') for day in sorted(sh.keys() & sz.keys())]
    if not rows:
        raise ValueError('金十两融报告未返回共同日期')
    return {'rows':rows,'scope':'金十沪深两融报告共同日期；不含北交所'}


def parse_tencent(payload, symbol, start, end):
    if payload.get('code') != 0:
        raise ValueError('腾讯行情未返回成功状态')
    data = payload.get('data', {}).get(symbol, {})
    # Never substitute qfqday: both providers must expose the same raw price basis.
    raw_rows = data.get('day')
    if not isinstance(raw_rows, list) or not raw_rows:
        raise ValueError('腾讯未返回不复权日线；不能以复权价格替代')
    rows = {}
    for raw in raw_rows:
        if not isinstance(raw, list) or len(raw) < 9:
            raise ValueError('腾讯日线字段发生变化，无法确认成交额单位')
        day = str(raw[0])
        if not start <= day <= end:
            continue
        values = [numeric(raw[i]) for i in (1, 2, 3, 4, 5, 7, 8)]
        opening, close, high, low, volume, turnover, amount = values
        if any(value is None for value in (opening, close, high, low, volume, amount)) or close <= 0:
            raise ValueError(f'腾讯 {day} 日线包含无效价格或交易数据')
        if volume < 0 or amount < 0 or high < low or not low <= close <= high:
            raise ValueError(f'腾讯 {day} 日线不符合价格与成交数据约束')
        # Tencent day: volume in lots, amount in 10,000 yuan, turnover in percent.
        rows[day] = dict(date=day, open=opening, close=close, high=high, low=low,
                         volume=volume, amount=amount * 10000, turnover=turnover)
    if not rows:
        raise ValueError('腾讯未返回所需日期范围的数据')
    return [rows[day] for day in sorted(rows)]


def tencent_history(symbol):
    start, end = bounds()
    payload = get_json('https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get',
                       {'param': f'{symbol},day,{start},{end},180,'})
    return parse_tencent(payload, symbol, start, end)


def tencent(action, params):
    if action == 'history':
        kind, code = params['kind'], params['code']
        if kind == 'index':
            item = next((item for item in INDICES if item['code'] == code), None)
            if item is None:
                raise ValueError('暂不支持该指数代码')
            symbol = item['symbol']
        elif kind == 'etf':
            symbol = ('sh' if code.startswith(('5', '6')) else 'sz') + code
        else:
            raise ValueError('腾讯备用源不支持东方财富板块代码')
        return {'rows': tencent_history(symbol), 'volume_unit': '手',
                'adjustment': '指数原始点位' if kind == 'index' else '不复权；区间收益未计分红'}
    if action == 'market':
        with ThreadPoolExecutor(max_workers=2) as pool:
            sh_future = pool.submit(tencent_history, 'sh000001')
            sz_future = pool.submit(tencent_history, 'sz399106')
            sh, sz = sh_future.result(), sz_future.result()
        mapped = {row['date']: row for row in sz}
        rows = [dict(date=a['date'], close=a['close'], amount=a['amount'] + mapped[a['date']]['amount'],
                     volume=a['volume'] + mapped[a['date']]['volume']) for a in sh if a['date'] in mapped]
        if not rows:
            raise ValueError('沪深市场没有共同交易日期')
        return {'rows': rows, 'indices': [dict(code='000001', name='上证指数', rows=sh),
                dict(code='399106', name='深证综指', rows=sz)], 'volume_unit': '手',
                'scope': '上证综指 + 深证综指行情口径；含 B 股，不含北交所'}
    raise ValueError('该查询不支持腾讯数据源')


def parse_sina_sectors(text):
    payload=json.loads(text[text.find('{'):])
    items=[]
    for value in payload.values():
        fields=value.split(',')
        if len(fields)!=13:
            raise ValueError('新浪板块快照字段发生变化')
        items.append(dict(code=fields[0],name=fields[1],change=numeric(fields[5]),
                          amount=numeric(fields[7]),volume=numeric(fields[6]),companies=numeric(fields[2]),
                          turnover=None,advancing=None,declining=None,provider='sina',history_supported=False))
    if not items:
        raise ValueError('新浪板块列表为空')
    return items


def sina_sectors(category):
    url='https://money.finance.sina.com.cn/q/view/newFLJK.php' if category=='concept' else 'https://vip.stock.finance.sina.com.cn/q/view/newSinaHy.php'
    with httpx.Client(timeout=8,headers=HEADERS) as client:
        response=client.get(url,params={'param':'class'} if category=='concept' else {})
        response.raise_for_status()
        text=response.content.decode('gb18030')
    return {'items':parse_sina_sectors(text),'_warning':'新浪板块分类与东方财富不同，列表为快照，源未提供日期或两个月历史序列；金额按元展示，不将分类或价格拼接为同一板块趋势。'}


def parse_sse_margin(payload):
    rows = {}
    for raw in payload.get('result', []):
        day = datetime.strptime(str(raw['opDate']), '%Y%m%d').date().isoformat()
        row = {key: numeric(raw.get(field)) for key, field in
               [('financing', 'rzye'), ('securities', 'rqylje'), ('total', 'rzrqjyzl'), ('buy', 'rzmre')]}
        if any(value is None or value < 0 for value in row.values()):
            raise ValueError('上交所两融数据字段异常')
        rows[day] = dict(date=day, **row)
    if not rows:
        raise ValueError('上交所未返回两融汇总')
    return rows


def parse_szse_margin(payload, requested_date):
    report = next((part for part in payload if part.get('metadata', {}).get('tabkey') == 'tab1'), None)
    if not report or not report.get('data'):
        raise ValueError(f'深交所 {requested_date} 两融汇总未披露')
    meta = report['metadata']
    if str(meta.get('subname', '')) != requested_date:
        raise ValueError('深交所返回日期与请求日期不一致，不能合并')
    raw, values = report['data'][0], {}
    for key, field in [('financing', 'jrrzye'), ('securities', 'jrrjye'), ('total', 'jrrzrjye'), ('buy', 'jrrzmr')]:
        label = meta.get('cols', {}).get(field, '')
        if '亿元' in label:
            multiplier = 1e8
        elif '(元)' in label or '（元）' in label:
            multiplier = 1
        else:
            raise ValueError(f'深交所 {field} 金额单位未确认')
        value = numeric(raw.get(field))
        if value is None or value < 0:
            raise ValueError('深交所两融数据字段异常')
        values[key] = float(Decimal(str(raw[field]).replace(',', '').strip()) * Decimal(str(multiplier)))
    return dict(date=requested_date, **values)


def day_db():
    SOURCE_DB.parent.mkdir(exist_ok=True)
    db = sqlite3.connect(SOURCE_DB, timeout=10)
    db.execute('CREATE TABLE IF NOT EXISTS source_days (source TEXT, date TEXT, payload TEXT, PRIMARY KEY(source,date))')
    return db


def szse_day(day):
    payload = get_json('https://www.szse.cn/api/report/ShowReport/data',
                       {'SHOWTYPE': 'JSON', 'CATALOGID': '1837_xxpl', 'txtDate': day, 'tab1PAGENO': '1'},
                       'https://www.szse.cn/disclosure/margin/margin/index.html')
    return parse_szse_margin(payload, day)


def official_margin():
    start, end = bounds()
    payload = get_json('https://query.sse.com.cn/marketdata/tradedata/queryMargin.do',
                       {'isPagination': 'true', 'beginDate': start.replace('-', ''), 'endDate': end.replace('-', ''),
                        'tabType': '', 'stockCode': '', 'pageHelp.pageSize': '500', 'pageHelp.pageNo': '1'},
                       'https://www.sse.com.cn/')
    sh = parse_sse_margin(payload)
    # Use exchange-reported trading dates rather than an invented weekday calendar.
    days = sorted(day for day in sh if start <= day <= end)[-105:]
    with day_db() as db:
        sz = {day: json.loads(raw) for day, raw in db.execute(
            'SELECT date,payload FROM source_days WHERE source=? AND date>=?', ('szse', start))}
    # Single-exchange day APIs are sensitive to bursts. Only backfill a few most
    # recent missing dates per query, and preserve each successfully fetched day.
    needed = [day for day in reversed(days) if day not in sz][:3]
    failures = []
    with day_db() as db:
        for day in needed:
            try:
                row = szse_day(day)
                sz[day] = row
                db.execute('INSERT OR REPLACE INTO source_days VALUES (?,?,?)',
                           ('szse', day, json.dumps(row, allow_nan=False)))
                db.commit()
                time.sleep(.3)
            except Exception as exc:
                failures.append(f'{day}: {str(exc)[:80]}')
                break  # Stop immediately on upstream failure rather than extending a ban.
    rows = {day:dict(date=day, **{key: sh[day][key] + sz[day][key]
            for key in ('financing', 'securities', 'total', 'buy')},source='上交所 + 深交所官方汇总')
            for day in days if day in sz}
    try:
        history = jin10_margin()
        for row in history['rows']:
            if row['date'] in days and row['date'] not in rows:
                rows[row['date']] = row
    except Exception as exc:
        failures.append('金十历史报告：'+str(exc)[:100])
    if not rows:
        raise ValueError('沪深交易所没有可合并的两融日期；' + '; '.join(failures[:2]))
    missing = [day for day in days if day not in rows]
    warning = '部分来源请求失败，已停止连续请求并保留已核实历史记录。' if failures else ''
    for i,day in enumerate(days):
        if day in rows:
            rows[day]['previous_session'] = days[i-1] if i else None
    return {'rows': [rows[day] for day in sorted(rows)], 'scope': '沪深两融共同日期；官方汇总优先，金十补历史；不含北交所',
            'sessions': days, 'calendar_basis': '上交所已披露两融交易日期',
            'missing_dates': missing, 'precision': '深交所按披露单位换算，亿元格式精度为 0.01 亿元',
            '_warning': warning}

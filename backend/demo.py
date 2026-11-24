"""Synthetic data, returned ONLY when the user explicitly selects demo mode."""
import hashlib
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .catalog import INDICES, ETFS


def dates():
    day = datetime.now(ZoneInfo('Asia/Shanghai')).date() - timedelta(days=1)
    days = []
    while len(days) < 100:
        if day.weekday() < 5:
            days.append(day.isoformat())
        day -= timedelta(days=1)
    return list(reversed(days))


def history(code, kind='index'):
    rng = random.Random(int(hashlib.sha256(code.encode()).hexdigest()[:10], 16))
    close = 3500 if kind == 'index' else (1.2 if kind == 'etf' else 1200)
    rows = []
    for i, day in enumerate(dates()):
        opening = close * (1 + rng.uniform(-.006, .006))
        close *= 1 + rng.uniform(-.019, .024)
        amount = rng.uniform(2e8, 35e8) if kind == 'etf' else rng.uniform(5e10, 9e11)
        rows.append(dict(date=day, open=round(opening, 3), close=round(close, 3), high=round(max(opening, close) * 1.006, 3), low=round(min(opening, close) * .994, 3), amount=round(amount, 2), volume=round(amount / close / 100), turnover=round(rng.uniform(.2, 3), 2)))
    return rows


def fetch(action, params):
    if action == 'history':
        return {'rows': history(params['code'], params['kind']), 'volume_unit': '手（演示）', 'adjustment': '不复权（演示）'}
    if action == 'market':
        sh, sz = history('000001'), history('399001')
        return {'rows': [dict(date=a['date'], amount=a['amount'] + b['amount'], volume=a['volume'] + b['volume'], close=a['close']) for a,b in zip(sh,sz)], 'indices': [{'code': x['code'], 'name': x['name'], 'rows': history(x['code'])} for x in INDICES[:4]], 'scope': '沪深 A 股（演示）', 'volume_unit': '手（演示）'}
    if action == 'margin':
        return {'rows': [dict(date=d, financing=1.65e12 + i * 1.8e9, securities=1.2e10 + i * 4e7, total=1.662e12 + i * 1.84e9, buy=6e10 + (i % 9) * 4e9) for i,d in enumerate(dates())], 'scope': '沪深合计（演示）'}
    if action == 'sectors':
        names = ['半导体','软件开发','证券','电池','医药商业','银行','光伏设备','汽车整车','消费电子','食品饮料','通信设备','有色金属','电力行业','航空航天','房地产开发','互联网服务','医疗器械','家电行业']
        rows = []
        for i, name in enumerate(names):
            h = history('BK' + str(i), 'sector')
            rows.append(dict(code='BK' + str(i), name=name, change=(h[-1]['close']/h[-2]['close']-1)*100, amount=h[-1]['amount'], turnover=h[-1]['turnover'], advancing=18+i, declining=12+i%7))
        return {'items': rows}
    if action == 'catalog':
        return {'items': INDICES + ETFS}
    raise ValueError('未知数据类型')

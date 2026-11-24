INDICES = [
    {"code": "000001", "name": "上证指数", "symbol": "sh000001", "kind": "index"},
    {"code": "399001", "name": "深证成指", "symbol": "sz399001", "kind": "index"},
    {"code": "399106", "name": "深证综指", "symbol": "sz399106", "kind": "index"},
    {"code": "399006", "name": "创业板指", "symbol": "sz399006", "kind": "index"},
    {"code": "000300", "name": "沪深300", "symbol": "sh000300", "kind": "index"},
    {"code": "000905", "name": "中证500", "symbol": "sh000905", "kind": "index"},
    {"code": "000852", "name": "中证1000", "symbol": "sh000852", "kind": "index"},
    {"code": "000688", "name": "科创50", "symbol": "sh000688", "kind": "index"},
    {"code": "000016", "name": "上证50", "symbol": "sh000016", "kind": "index"},
]
SECTOR_INDEX_SCOPE = '量价数据为该指数成分证券的行情口径；指数本身不直接交易。成分范围与新浪、东方财富板块分类不同，不能视为整个行业或概念的成交总量。'
SECTOR_INDICES = [
    {"code": "000991", "name": "全指医药", "symbol": "sh000991", "kind": "index", "group": "industry"},
    {"code": "000993", "name": "全指信息", "symbol": "sh000993", "kind": "index", "group": "industry"},
    {"code": "399986", "name": "中证银行", "symbol": "sz399986", "kind": "index", "group": "industry"},
    {"code": "399997", "name": "中证白酒", "symbol": "sz399997", "kind": "index", "group": "theme"},
    {"code": "399975", "name": "证券公司", "symbol": "sz399975", "kind": "index", "group": "industry"},
    {"code": "399967", "name": "中证军工", "symbol": "sz399967", "kind": "index", "group": "theme"},
]
INDICES += SECTOR_INDICES

ETFS = [
    {"code": "510300", "name": "沪深300ETF", "kind": "etf"},
    {"code": "510500", "name": "中证500ETF", "kind": "etf"},
    {"code": "512100", "name": "中证1000ETF", "kind": "etf"},
    {"code": "159915", "name": "创业板ETF", "kind": "etf"},
    {"code": "588000", "name": "科创50ETF", "kind": "etf"},
    {"code": "512480", "name": "半导体ETF", "kind": "etf"},
    {"code": "512660", "name": "军工ETF", "kind": "etf"},
    {"code": "512010", "name": "医药ETF", "kind": "etf"},
    {"code": "515180", "name": "红利ETF", "kind": "etf"},
    {"code": "512880", "name": "证券ETF", "kind": "etf"},
    {"code": "159928", "name": "消费ETF", "kind": "etf"},
    {"code": "516160", "name": "新能源ETF", "kind": "etf"},
]

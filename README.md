# A股两融交易查询系统

一个功能强大的A股融资融券交易数据查询和分析系统，支持数据获取、处理、分析和可视化。

## 🌟 主要功能

- 📊 **数据查询**: 从多个数据源获取A股两融交易数据
- 📈 **趋势分析**: 计算两融余额变化趋势和技术指标
- 📉 **占比计算**: 分析融资融券在市场中的占比情况
- 📋 **报告生成**: 自动生成详细的分析报告
- 🎨 **数据可视化**: 生成专业的图表和交互式仪表板
- 💾 **数据导出**: 支持CSV、Excel、JSON等多种格式导出

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 推荐使用虚拟环境

### 安装步骤

1. **克隆或下载项目**
   ```bash
   # 如果是从git克隆
   git clone [项目地址]
   cd 两融交易查询
   
   # 或者直接下载解压到本目录
   ```

2. **创建虚拟环境（推荐）**
   ```bash
   python -m venv venv
   
   # Windows
   venv\\Scripts\\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置API Token（可选）**
   
   如需使用TuShare数据源，请申请Token并设置环境变量：
   ```bash
   # Windows
   set TUSHARE_TOKEN=your_token_here
   
   # macOS/Linux
   export TUSHARE_TOKEN=your_token_here
   ```

### 运行方式

#### 方式一：Web界面（推荐）

```bash
streamlit run app.py
```

然后在浏览器中打开 `http://localhost:8501`

#### 方式二：命令行界面

```bash
# 交互式模式
python main.py --interactive

# 直接查询（查询最近30天数据）
python main.py

# 指定日期范围
python main.py --start 20240101 --end 20240131

# 生成交互式仪表板
python main.py --start 20240101 --end 20240131 --dashboard

# 查看所有选项
python main.py --help
```

## 📖 详细使用说明

### Web界面使用

1. **启动Web界面**
   ```bash
   streamlit run app.py
   ```

2. **设置查询参数**
   - 在左侧边栏选择开始和结束日期
   - 选择是否使用缓存（推荐开启）
   - 选择导出格式和图表选项

3. **执行查询**
   - 点击"开始查询"按钮
   - 等待数据获取和处理完成

4. **查看结果**
   - 查看数据概览和关键指标
   - 浏览各种分析图表
   - 在详细数据区域查看原始数据

5. **导出数据**
   - 在数据表格部分点击下载按钮
   - 选择需要的列进行导出

### 命令行界面使用

#### 交互式模式

```bash
python main.py --interactive
```

进入交互式模式后，按照提示进行操作：
- 选择查询类型
- 输入日期范围
- 选择输出选项
- 等待查询完成

#### 命令行参数

```bash
python main.py [选项]

选项:
  --start DATE          开始日期 (YYYYMMDD格式)
  --end DATE           结束日期 (YYYYMMDD格式)
  --format FORMAT      导出格式 (csv/excel/json)
  --no-charts          不生成图表
  --dashboard          生成交互式仪表板
  --interactive        运行交互式模式
  -h, --help          显示帮助信息
```

### 配置文件说明

项目的主要配置在 `config.py` 文件中：

```python
# API配置
TUSHARE_TOKEN = '你的Token'  # TuShare API Token

# 数据源配置
DATA_SOURCES = {
    'akshare': {'enabled': True},     # AKShare开源数据
    'tushare': {'enabled': True},     # TuShare专业数据
    'eastmoney': {'enabled': True}    # 东方财富数据
}

# 查询配置
MARGIN_TRADING_CONFIG = {
    'default_start_date': '20240101',  # 默认开始日期
    'default_end_date': '20240131',    # 默认结束日期
    'cache_enabled': True,             # 启用缓存
    'charts_enabled': True             # 启用图表生成
}
```

## 📊 输出说明

### 数据文件

查询完成后，系统会在 `output` 目录生成以下文件：

1. **数据文件**: `margin_data_YYYYMMDD_YYYYMMDD_timestamp.csv/xlsx/json`
   - 包含完整的两融数据和计算指标

2. **分析报告**: `margin_report_YYYYMMDD_YYYYMMDD_timestamp.txt`
   - 包含详细的文字分析报告

3. **图表文件**: 
   - `margin_balance_timestamp.png` - 余额趋势图
   - `margin_ratio_timestamp.png` - 占比分析图
   - `margin_correlation_timestamp.png` - 相关性热力图
   - `margin_summary_timestamp.png` - 汇总图表

4. **交互式仪表板**: `margin_dashboard_timestamp.html`
   - 可在浏览器中打开的交互式图表

### 关键指标说明

#### 基础指标
- **融资余额**: 市场融资的未平仓金额
- **融券余额**: 市场融券的未平仓金额  
- **两融余额**: 融资余额和融券余额的总和
- **融资买入额**: 当日融资买入的金额

#### 计算指标
- **融资占比**: 融资余额在两融余额中的占比
- **融券占比**: 融券余额在两融余额中的占比
- **日变化率**: 相比前一日的变化百分比
- **周变化率**: 相比前一周的变化百分比
- **月变化率**: 相比前一月的变化百分比

#### 技术指标
- **移动平均线**: MA5, MA10, MA20, MA60
- **RSI指标**: 相对强弱指标，判断超买超卖
- **布林带**: 价格通道指标
- **偏离度**: 价格相对移动平均线的偏离程度

## 🛠️ 项目结构

```
两融交易查询/
├── main.py                 # 命令行主程序
├── app.py                  # Web界面程序
├── config.py               # 配置文件
├── utils.py                # 工具函数
├── data_fetcher.py         # 数据获取模块
├── data_processor.py       # 数据处理模块
├── visualizer.py           # 数据可视化模块
├── requirements.txt        # 依赖清单
├── README.md              # 使用说明
├── data/                  # 数据缓存目录
├── output/                # 输出文件目录
├── logs/                  # 日志文件目录
└── temp/                  # 临时文件目录
```

## 🔧 高级配置

### 自定义数据源

可以在 `data_fetcher.py` 中添加新的数据源：

```python
def _get_custom_data_source(self, start_date, end_date):
    """自定义数据源"""
    # 实现自定义数据获取逻辑
    pass
```

### 自定义指标计算

可以在 `data_processor.py` 中添加新的技术指标：

```python
def _calculate_custom_indicator(self, df):
    """自定义技术指标"""
    # 实现自定义指标计算
    pass
```

### 自定义可视化

可以在 `visualizer.py` 中添加新的图表类型：

```python
def create_custom_chart(self, df):
    """自定义图表"""
    # 实现自定义图表生成
    pass
```

## 🚨 注意事项

### 数据源限制

1. **AKShare**: 
   - 免费使用，但有访问频率限制
   - 建议开启缓存减少请求次数

2. **TuShare**:
   - 需要注册账号获取Token
   - 不同级别账号有不同的访问限制

3. **东方财富**:
   - 通过网页接口获取，稳定性可能受网站更新影响

### 性能优化

1. **缓存使用**: 开启缓存可以显著提高查询速度
2. **时间范围**: 建议单次查询时间不超过1年
3. **并发控制**: 避免同时运行多个查询任务

### 常见问题

1. **网络连接失败**
   - 检查网络连接
   - 尝试使用代理
   - 稍后重试

2. **数据获取失败**
   - 检查API Token配置
   - 确认数据源是否可用
   - 查看日志文件了解详细错误

3. **图表显示异常**
   - 确认matplotlib中文字体配置
   - 检查数据完整性
   - 更新相关依赖包

## 📈 示例用法

### 基础查询示例

```python
from data_fetcher import create_margin_fetcher
from data_processor import create_margin_processor

# 创建实例
fetcher = create_margin_fetcher()
processor = create_margin_processor()

# 获取数据
data = fetcher.get_margin_trading_summary('20240101', '20240131')

# 处理数据
processed_data = processor.process_margin_summary(data)

# 生成报告
report = processor.generate_summary_report(processed_data)
print(report)
```

### 可视化示例

```python
from visualizer import create_margin_visualizer

# 创建可视化器
visualizer = create_margin_visualizer()

# 生成图表
balance_chart = visualizer.create_margin_balance_chart(processed_data)
ratio_chart = visualizer.create_margin_ratio_chart(processed_data)
dashboard = visualizer.create_interactive_dashboard(processed_data)
```

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 LICENSE 文件了解详情

## 📞 支持

如果您遇到问题或有建议，请：

1. 查看本文档的常见问题部分
2. 查看项目的 Issues 页面
3. 创建新的 Issue 描述问题

## 🔄 更新日志

### v1.0.0 (2025-09-05)
- 初始版本发布
- 支持多数据源查询
- 实现基础分析功能
- 提供Web和命令行界面

---

**注意**: 本项目仅用于学习和研究目的，不构成投资建议。投资有风险，决策需谨慎。
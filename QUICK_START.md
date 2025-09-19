# 🚀 快速启动指南

## 直接启动Web服务

### 方法1：使用run.py（推荐）
```bash
python run.py
```
- 自动检查环境和依赖
- 直接启动Web界面
- 如需菜单选项：`python run.py --menu`

### 方法2：使用start_web.py
```bash
python start_web.py
```
- 自动查找可用端口
- 快速启动Web服务

### 方法3：直接使用streamlit
```bash
streamlit run app.py --server.port 8502
```
- 手动指定端口
- 适合开发调试

## 🌐 访问地址

启动成功后，在浏览器中访问：
- http://localhost:8501 （默认端口）
- http://localhost:8502 （备用端口）
- 或启动时显示的具体地址

## 📋 主要功能

1. **板块资金查询**
   - 板块概览：查看所有板块资金流向
   - 板块详情：查看单个板块成分股

2. **两融交易查询**
   - 融资融券余额查询
   - 历史数据分析

3. **ETF资金查询**
   - ETF资金流向分析
   - 实时数据监控

## ⚡ 快速测试

1. 启动Web服务
2. 点击"进入板块资金查询"
3. 选择"板块概览"
4. 点击"查询所有板块"
5. 查看数据和图表

## 🔧 故障排除

### 端口被占用
```bash
# 查看占用端口的进程
lsof -i :8501

# 或使用其他端口
streamlit run app.py --server.port 8502
```

### 依赖包问题
```bash
# 安装依赖
pip install -r requirements.txt

# 或使用conda
conda install --file requirements.txt
```

### 数据获取失败
- 检查网络连接
- 确认数据源API可用
- 查看日志文件：`logs/`目录

## 📝 注意事项

- 首次启动可能需要安装依赖包
- 数据查询需要网络连接
- 建议使用Chrome或Firefox浏览器
- 按Ctrl+C停止服务

---
*更新时间：2025-09-19*
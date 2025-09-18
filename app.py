"""
Web界面 - A股两融交易查询系统
基于Streamlit的Web应用程序
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
import sys

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import MARGIN_TRADING_CONFIG
from utils import setup_logging, ensure_directories, format_number
from margin.fetcher import create_margin_fetcher
from margin.processor import create_margin_processor
from margin.visualizer import create_margin_visualizer

# 页面配置
st.set_page_config(
    page_title="A股金融数据分析系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-message {
        color: #28a745;
        font-weight: bold;
    }
    .error-message {
        color: #dc3545;
        font-weight: bold;
    }
    .info-box {
        background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
        padding: 1.5rem;
        border-left: 4px solid #2196f3;
        border-radius: 8px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .feature-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 15px;
        padding: 25px;
        margin: 15px;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        border: 1px solid #dee2e6;
    }
    .feature-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
        border-color: #2196f3;
    }
    .feature-icon {
        font-size: 3rem;
        margin-bottom: 15px;
    }
    .feature-title {
        font-size: 1.5rem;
        font-weight: bold;
        margin-bottom: 10px;
        color: #1f77b4;
    }
    .feature-description {
        color: #666;
        font-size: 1rem;
    }
    /* 中国股市颜色习惯 */
    .positive-value {
        color: #FF4444 !important;
        font-weight: bold;
    }
    .negative-value {
        color: #00C851 !important;
        font-weight: bold;
    }
    .neutral-value {
        color: #666 !important;
    }
    /* 数据表格样式 */
    .stDataFrame {
        font-size: 0.9rem;
    }
    /* 指标卡片样式 */
    .metric-positive {
        background: linear-gradient(135deg, #ffe6e6 0%, #ffcccc 100%);
        border-left: 4px solid #FF4444;
    }
    .metric-negative {
        background: linear-gradient(135deg, #e6ffe6 0%, #ccffcc 100%);
        border-left: 4px solid #00C851;
    }
</style>
""", unsafe_allow_html=True)

class MarginTradingWebApp:
    """两融交易Web应用"""
    
    def __init__(self):
        self._initialize_app()
        # 初始化页面状态管理
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "main"
    
    def _format_value_with_color(self, value: float, is_percentage: bool = False, show_sign: bool = True) -> str:
        """
        根据中国股市习惯格式化数值颜色
        :param value: 数值
        :param is_percentage: 是否为百分比
        :param show_sign: 是否显示正负号
        :return: 带颜色的HTML字符串
        """
        if value > 0:
            color_class = "positive-value"
            sign = "+" if show_sign else ""
        elif value < 0:
            color_class = "negative-value"
            sign = ""
        else:
            color_class = "neutral-value"
            sign = ""
        
        if is_percentage:
            formatted_value = f"{sign}{value:.2f}%"
        else:
            formatted_value = f"{sign}{value:.2f}"
        
        return f'<span class="{color_class}">{formatted_value}</span>'
    
    def _format_money_with_color(self, value: float, unit: str = "亿元") -> str:
        """
        格式化资金数值并添加颜色
        :param value: 资金数值
        :param unit: 单位
        :return: 带颜色的HTML字符串
        """
        if value > 0:
            color_class = "positive-value"
            sign = "+"
        elif value < 0:
            color_class = "negative-value"
            sign = ""
        else:
            color_class = "neutral-value"
            sign = ""
        
        formatted_value = f"{sign}{value:.2f}{unit}"
        return f'<span class="{color_class}">{formatted_value}</span>'
    
    def _show_data_source_error(self, error_type: str = "connection"):
        """
        显示数据源错误信息
        :param error_type: 错误类型
        """
        if error_type == "connection":
            st.error("❌ 数据源服务器暂时不可用，请稍后重试")
            st.info("💡 这通常是临时问题，建议等待10-30分钟后重试")
        elif error_type == "timeout":
            st.error("❌ 网络连接超时，请检查网络连接")
        elif error_type == "empty":
            st.error("❌ 数据源返回空数据，可能是非交易时间")
        else:
            st.error("❌ 数据获取失败，请稍后重试")
    
    def _initialize_app(self):
        """初始化应用"""
        # 设置日志
        self.logger = setup_logging()
        
        # 确保目录存在
        ensure_directories()
        
        # 初始化组件
        self.data_fetcher = create_margin_fetcher()
        self.data_processor = create_margin_processor()
        self.visualizer = create_margin_visualizer()
        
        # 初始化session state
        if 'margin_data' not in st.session_state:
            st.session_state.margin_data = pd.DataFrame()
        if 'processed_data' not in st.session_state:
            st.session_state.processed_data = pd.DataFrame()
        if 'analysis_result' not in st.session_state:
            st.session_state.analysis_result = {}
    
    def _clear_etf_data(self):
        """清除ETF相关的session state数据"""
        keys_to_clear = ['etf_data', 'current_etf_code', 'last_etf_query_key']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    def _clear_margin_data(self):
        """清除两融相关的session state数据"""
        keys_to_clear = ['margin_data', 'processed_data', 'analysis_result']
        for key in keys_to_clear:
            if key in st.session_state:
                st.session_state[key] = pd.DataFrame() if 'data' in key else {}
    
    def _clear_sector_data(self):
        """清除板块相关的session state数据"""
        keys_to_clear = ['sector_data', 'sector_analysis', 'current_sector', 'sector_detail_data']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    def show_main_page(self):
        """显示主页"""
        st.markdown('<div class="main-header">📊 A股金融数据分析系统</div>', 
                   unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-box">
            <h3>🎯 欢迎使用A股金融数据分析系统</h3>
            <p>📈 本系统提供专业的A股市场数据分析功能，帮助投资者做出更明智的投资决策</p>
            <p>🚀 支持两融交易分析和ETF基金分析，数据实时更新，图表直观易懂</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 创建功能卡片布局
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">📈</div>
                <div class="feature-title">两融交易查询</div>
                <div class="feature-description">查询和分析A股市场的融资融券交易数据，包括余额趋势、占比分析等</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("进入两融交易查询", type="primary", width="stretch"):
                # 清除其他数据，切换到两融页面
                self._clear_etf_data()
                self._clear_sector_data()
                st.session_state.current_page = "margin"
                st.rerun()
        
        with col2:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">💰</div>
                <div class="feature-title">ETF基金查询</div>
                <div class="feature-description">查询和分析ETF基金的资金流向、份额变动、申购赎回情况</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("进入ETF基金查询", type="primary", width="stretch"):
                # 清除其他数据，切换到ETF页面
                self._clear_margin_data()
                self._clear_sector_data()
                st.session_state.current_page = "etf"
                st.rerun()
        
        with col3:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">🏢</div>
                <div class="feature-title">板块资金查询</div>
                <div class="feature-description">查询和分析中国股市各板块的资金流向情况，包括主力资金、涨跌幅等</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("进入板块资金查询", type="primary", width="stretch"):
                # 清除其他数据，切换到板块页面
                self._clear_margin_data()
                self._clear_etf_data()
                st.session_state.current_page = "sector"
                st.rerun()
        
        # 系统介绍
        st.markdown("### 📊 系统功能介绍")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            #### 两融交易分析功能
            - **数据查询**：从多个数据源获取A股两融交易数据
            - **趋势分析**：计算两融余额变化趋势和技术指标
            - **占比计算**：分析融资融券在市场中的占比情况
            - **数据可视化**：生成专业的图表和交互式仪表板
            """)
        
        with col2:
            st.markdown("""
            #### ETF基金分析功能
            - **资金流向**：分析ETF基金的净申购赎回情况
            - **份额变动**：跟踪ETF基金总份额的变化情况
            - **申购赎回**：监控场外投资者申购和赎回ETF的情况
            - **综合分析**：提供ETF基金的全面数据分析报告
            """)
        
        with col3:
            st.markdown("""
            #### 板块资金分析功能
            - **板块概览**：查看所有板块的资金流向排行榜
            - **资金流向**：分析各板块主力资金净流入流出情况
            - **涨跌统计**：统计板块涨跌幅和市场表现
            - **详细分析**：深入分析单个板块的成分股情况
            """)
        
        st.markdown("### ⚠️ 使用说明")
        st.markdown("""
        1. 点击上方功能按钮进入相应的查询界面
        2. 每个功能模块完全独立，互不影响
        3. 首次查询可能需要较长时间，请耐心等待
        4. 建议查询时间范围不超过1年，以确保查询效率
        """)
    
    def show_margin_trading_page(self):
        """显示两融交易查询页面"""
        # 页面标题和返回按钮
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("← 返回主页"):
                # 清除两融数据
                self._clear_margin_data()
                st.session_state.current_page = "main"
                st.rerun()
        with col2:
            st.markdown('<div class="main-header">📈 A股两融交易查询</div>', 
                       unsafe_allow_html=True)
        
        # 显示侧边栏并获取配置
        config = self.show_margin_sidebar()
        
        # 如果点击查询按钮
        if config['query_button']:
            with st.spinner("正在查询两融数据..."):
                success = self.query_margin_data(config)
            # 不需要手动rerun，数据更新后会自动显示
        
        # 如果有数据，显示结果
        if 'processed_data' in st.session_state and not st.session_state.processed_data.empty:
            # 显示汇总指标
            self.show_summary_metrics()
            
            # 显示图表
            self.show_margin_charts(config)
            
            # 显示数据表格
            with st.expander("📋 查看详细数据", expanded=False):
                self.show_margin_data_table()
    
    def show_etf_page(self):
        """显示ETF查询页面"""
        # 页面标题和返回按钮
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("← 返回主页"):
                # 清除ETF数据
                self._clear_etf_data()
                st.session_state.current_page = "main"
                st.rerun()
        with col2:
            st.markdown('<div class="main-header">💰 ETF基金查询</div>', 
                       unsafe_allow_html=True)
        
        # ETF查询配置
        st.sidebar.header("🔧 ETF查询配置")
        
        # ETF代码输入
        etf_code = st.sidebar.text_input("请输入ETF代码", value="510310", 
                                        help="例如：510310 (沪深300ETF), 510050 (上证50ETF)")
        
        # 检测ETF代码变化
        if 'last_etf_input' not in st.session_state:
            st.session_state.last_etf_input = ""
        
        if etf_code != st.session_state.last_etf_input and etf_code:
            st.session_state.last_etf_input = etf_code
            # 显示ETF代码提示
            etf_name_mapping = {
                '510310': '沪深300ETF',
                '510050': '上证50ETF', 
                '510500': '中证500ETF',
                '159919': '沪深300ETF',
                '159915': '创业板ETF',
                '512100': '中证1000ETF'
            }
            if etf_code in etf_name_mapping:
                st.sidebar.success(f"✅ 识别为: {etf_name_mapping[etf_code]}")
            else:
                st.sidebar.info(f"💡 ETF代码: {etf_code}")
        
        # 日期范围选择
        st.sidebar.subheader("📅 日期范围")
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            start_date = st.date_input(
                "开始日期",
                value=datetime.now() - timedelta(days=30),
                max_value=datetime.now()
            )
        
        with col2:
            end_date = st.date_input(
                "结束日期",
                value=datetime.now(),
                max_value=datetime.now()
            )
        
        # 查询选项
        st.sidebar.subheader("⚙️ 查询选项")
        
        use_cache = st.sidebar.checkbox("使用缓存数据", value=True, 
                                       help="使用缓存可以加快查询速度")
        
        # 图表选项
        st.sidebar.subheader("📊 图表选项")
        
        show_fund_flow_chart = st.sidebar.checkbox("资金流向图", value=True)
        show_share_change_chart = st.sidebar.checkbox("份额变动图", value=True)
        show_subscription_chart = st.sidebar.checkbox("申购赎回图", value=True)
        show_comprehensive_chart = st.sidebar.checkbox("综合分析图", value=True)
        
        # 查询按钮
        st.sidebar.markdown("---")  # 分隔线
        query_button = st.sidebar.button("🚀 开始查询", type="primary", width="stretch")
        
        config = {
            'etf_code': etf_code,
            'start_date': start_date.strftime('%Y%m%d'),
            'end_date': end_date.strftime('%Y%m%d'),
            'use_cache': use_cache,
            'show_fund_flow_chart': show_fund_flow_chart,
            'show_share_change_chart': show_share_change_chart,
            'show_subscription_chart': show_subscription_chart,
            'show_comprehensive_chart': show_comprehensive_chart,
            'query_button': query_button
        }
        
        # 检查参数是否发生变化
        current_query_key = f"{etf_code}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        if 'last_etf_query_key' not in st.session_state:
            st.session_state.last_etf_query_key = ""
        
        # 检查ETF代码是否发生变化
        if 'current_etf_code' not in st.session_state:
            st.session_state.current_etf_code = ""
        
        # 如果ETF代码发生变化，立即清除旧数据
        if st.session_state.current_etf_code != etf_code:
            self._clear_etf_data()
            st.session_state.current_etf_code = etf_code
        
        # 如果查询参数发生变化，也清除旧数据
        elif st.session_state.last_etf_query_key != current_query_key:
            self._clear_etf_data()
        
        # 如果点击查询按钮
        if config['query_button']:
            st.session_state.last_etf_query_key = current_query_key
            with st.spinner("正在查询ETF数据..."):
                success = self.query_etf_data(config)
            # 不需要手动rerun，数据更新后会自动显示
        
        # 显示结果区域
        results_container = st.container()
        
        with results_container:
            # 检查是否有有效的ETF数据
            has_valid_data = (
                'etf_data' in st.session_state and 
                st.session_state.etf_data and 
                'current_etf_code' in st.session_state and 
                st.session_state.current_etf_code == etf_code
            )
            
            if has_valid_data:
                # 显示ETF基本信息
                self.show_etf_info(st.session_state.etf_data.get('info', {}))
                
                # 显示汇总指标
                self.show_etf_summary_metrics(st.session_state.etf_data.get('analysis', {}))
                
                # 显示图表
                self.show_etf_charts(config, st.session_state.etf_data)
                
                # 显示数据表格
                with st.expander("📋 查看详细数据", expanded=False):
                    self.show_etf_data_table(st.session_state.etf_data)
            else:
                # 如果没有数据或ETF代码不匹配，显示提示
                if etf_code:
                    # 检查是否刚刚更换了ETF代码
                    if ('current_etf_code' in st.session_state and 
                        st.session_state.current_etf_code != etf_code):
                        st.info(f"🔄 检测到ETF代码变更为 {etf_code}，请点击'开始查询'获取新数据")
                    else:
                        st.info(f"💡 请点击'开始查询'按钮获取ETF {etf_code} 的数据")
                    
                    # 显示一些使用提示
                    with st.expander("💡 使用提示", expanded=True):
                        st.markdown("""
                        ### 如何使用ETF查询功能：
                        
                        1. **输入ETF代码**：在左侧输入框中输入ETF代码（如510310）
                        2. **选择日期范围**：选择要查询的开始和结束日期
                        3. **点击查询**：点击"开始查询"按钮获取数据
                        4. **查看结果**：系统将自动显示ETF的各项分析数据
                        
                        ### 常用ETF代码：
                        - **510310**: 沪深300ETF
                        - **510050**: 上证50ETF  
                        - **510500**: 中证500ETF
                        - **159919**: 沪深300ETF（深交所）
                        - **159915**: 创业板ETF
                        - **512100**: 中证1000ETF
                        
                        ### 功能说明：
                        - **资金流向分析**：显示ETF的资金净流入/流出情况
                        - **份额变动分析**：分析ETF份额的变化趋势
                        - **场外市场分析**：模拟申购赎回情况
                        - **实时估值**：显示ETF的价格变化趋势
                        """)
                else:
                    st.warning("⚠️ 请输入有效的ETF代码")
    
    def show_sector_page(self):
        """显示板块资金查询页面"""
        # 页面标题和返回按钮
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("← 返回主页"):
                # 清除板块数据
                self._clear_sector_data()
                st.session_state.current_page = "main"
                st.rerun()
        with col2:
            st.markdown('<div class="main-header">🏢 板块资金查询</div>', 
                       unsafe_allow_html=True)
        
        # 侧边栏配置
        st.sidebar.header("🔧 板块查询配置")
        
        # 查询模式选择
        query_mode = st.sidebar.selectbox(
            "查询模式",
            ["板块概览", "单板块详情"],
            help="选择查询所有板块概览或单个板块详情"
        )
        
        # 查询选项
        st.sidebar.subheader("⚙️ 查询选项")
        use_cache = st.sidebar.checkbox("使用缓存数据", value=True, 
                                       help="使用缓存可以加快查询速度")
        
        # 显示选项
        st.sidebar.subheader("📊 显示选项")
        show_overview_chart = st.sidebar.checkbox("概览图表", value=True)
        show_ranking_charts = st.sidebar.checkbox("排行榜图表", value=True)
        show_sentiment_gauge = st.sidebar.checkbox("市场情绪仪表盘", value=True)
        
        config = {
            'query_mode': query_mode,
            'use_cache': use_cache,
            'show_overview_chart': show_overview_chart,
            'show_ranking_charts': show_ranking_charts,
            'show_sentiment_gauge': show_sentiment_gauge
        }
        
        if query_mode == "板块概览":
            # 板块概览模式
            st.sidebar.markdown("---")
            query_button = st.sidebar.button("🚀 查询所有板块", type="primary", width="stretch")
            
            if query_button:
                with st.spinner("正在查询板块数据..."):
                    success = self.query_sector_overview(config)
            
            # 显示板块概览结果
            if 'sector_data' in st.session_state and st.session_state.sector_data:
                self.show_sector_overview_results(config)
            else:
                # 显示使用提示
                with st.expander("💡 使用提示", expanded=True):
                    st.markdown("""
                    ### 板块资金查询功能说明：
                    
                    #### 📊 板块概览模式
                    - 查询所有板块的资金流向排行榜
                    - 显示主力资金净流入/流出情况
                    - 分析板块涨跌幅和市场表现
                    - 提供市场情绪分析
                    
                    #### 🔍 单板块详情模式  
                    - 输入具体板块名称查询详细信息
                    - 显示板块内成分股的资金流向
                    - 分析板块强度和龙头效应
                    - 提供个股排行榜
                    
                    #### 📈 数据说明
                    - **主力资金**：超大单+大单净流入金额
                    - **涨跌幅**：板块平均涨跌幅
                    - **换手率**：板块平均换手率
                    - **量比**：当日成交量与近期平均成交量的比值
                    
                    #### ⚠️ 重要提醒
                    - 所有数据均为真实市场数据，不提供模拟数据
                    - 数据获取失败时会明确提示，请勿基于错误信息做投资决策
                    - 建议在网络稳定的环境下使用
                    
                    点击"查询所有板块"开始使用！
                    """)
        
        else:
            # 单板块详情模式
            sector_input = st.sidebar.text_input(
                "板块名称", 
                value="", 
                placeholder="例如：半导体、新能源汽车、医药生物",
                help="输入要查询的板块名称"
            )
            
            st.sidebar.markdown("---")
            detail_query_button = st.sidebar.button("🔍 查询板块详情", type="primary", width="stretch")
            
            if detail_query_button and sector_input:
                with st.spinner(f"正在查询板块 {sector_input} 的详细数据..."):
                    success = self.query_sector_detail(sector_input, config)
                    if not success:
                        st.error("❌ 数据获取失败，请检查网络连接或稍后重试")
            
            # 显示板块详情结果
            if 'sector_detail_data' in st.session_state and st.session_state.sector_detail_data:
                self.show_sector_detail_results(config)
            else:
                if sector_input:
                    st.info(f"💡 请点击'查询板块详情'获取板块 {sector_input} 的数据")
                else:
                    st.info("💡 请在左侧输入板块名称，然后点击查询")
                
                # 显示常用板块名称
                with st.expander("📋 常用板块名称参考", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("""
                        **科技板块**
                        - 半导体
                        - 人工智能
                        - 5G概念
                        - 云计算
                        - 大数据
                        """)
                    
                    with col2:
                        st.markdown("""
                        **新兴产业**
                        - 新能源汽车
                        - 光伏概念
                        - 风电
                        - 储能
                        - 锂电池
                        """)
                    
                    with col3:
                        st.markdown("""
                        **传统行业**
                        - 医药生物
                        - 白酒
                        - 房地产
                        - 银行
                        - 保险
                        """)
    
    def query_sector_overview(self, config: dict) -> bool:
        """查询板块概览数据"""
        try:
            # 初始化板块组件
            from sector.fetcher import create_sector_fetcher
            from sector.processor import create_sector_processor
            
            sector_fetcher = create_sector_fetcher()
            sector_processor = create_sector_processor()
            
            # 创建进度条
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 获取板块资金流向数据
            status_text.text("正在获取板块资金流向数据...")
            progress_bar.progress(50)
            
            sector_data = sector_fetcher.get_sector_fund_flow(use_cache=config['use_cache'])
            
            if sector_data.empty:
                progress_bar.empty()
                status_text.empty()
                self._show_data_source_error("connection")
                return False
            
            # 处理数据
            status_text.text("正在处理板块数据...")
            progress_bar.progress(80)
            
            processed_data = sector_processor.process_sector_data(sector_data)
            
            # 保存到session state
            st.session_state.sector_data = processed_data
            
            # 完成
            progress_bar.progress(100)
            status_text.text("数据处理完成！")
            
            # 清除进度条和状态文本
            progress_bar.empty()
            status_text.empty()
            
            st.success(f"✅ 成功获取并处理了 {len(sector_data)} 个板块的数据")
            return True
            
        except Exception as e:
            st.error(f"❌ 板块概览查询失败: {str(e)}")
            return False
    
    def query_sector_detail(self, sector_name: str, config: dict) -> bool:
        """查询单个板块详细数据"""
        try:
            # 初始化板块组件
            from sector.fetcher import create_sector_fetcher
            from sector.processor import create_sector_processor
            
            sector_fetcher = create_sector_fetcher()
            sector_processor = create_sector_processor()
            
            # 创建进度条
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 获取板块详细数据
            status_text.text(f"正在获取板块 {sector_name} 的详细数据...")
            progress_bar.progress(50)
            
            detail_data = sector_fetcher.get_sector_detail(sector_name, use_cache=config['use_cache'])
            
            if detail_data.empty:
                progress_bar.empty()
                status_text.empty()
                self._show_data_source_error("connection")
                return False
            
            # 处理数据
            status_text.text("正在分析板块数据...")
            progress_bar.progress(80)
            
            analysis_result = sector_processor.analyze_sector_detail(sector_name, detail_data)
            
            # 保存到session state
            st.session_state.sector_detail_data = analysis_result
            st.session_state.current_sector = sector_name
            
            # 完成
            progress_bar.progress(100)
            status_text.text("数据处理完成！")
            
            # 清除进度条和状态文本
            progress_bar.empty()
            status_text.empty()
            
            st.success(f"✅ 成功获取并分析了板块 {sector_name} 的 {len(detail_data)} 只成分股数据")
            return True
            
        except Exception as e:
            st.error(f"❌ 板块 {sector_name} 详情查询失败: {str(e)}")
            return False
    
    def show_sector_overview_results(self, config: dict):
        """显示板块概览结果"""
        if not st.session_state.sector_data:
            return
        
        processed_data = st.session_state.sector_data
        
        # 显示汇总指标
        if 'summary' in processed_data:
            st.subheader("📊 板块市场概览")
            summary = processed_data['summary']
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="📈 总板块数",
                    value=summary.get('总板块数', 0)
                )
            
            with col2:
                st.metric(
                    label="💰 资金净流入板块",
                    value=summary.get('资金净流入板块', 0),
                    delta=summary.get('资金流入占比', '0%')
                )
            
            with col3:
                st.metric(
                    label="📊 上涨板块",
                    value=summary.get('上涨板块', 0),
                    delta=summary.get('上涨占比', '0%')
                )
            
            with col4:
                st.metric(
                    label="💵 总资金净流入",
                    value=summary.get('总资金净流入', '0.00亿元')
                )
        
        # 显示市场情绪
        if 'market_sentiment' in processed_data and config['show_sentiment_gauge']:
            st.subheader("🌡️ 市场情绪分析")
            sentiment = processed_data['market_sentiment']
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                # 显示情绪指标
                for key, value in sentiment.items():
                    if key != '情绪评分':
                        # 根据指标类型添加颜色
                        if key in ['上涨比例', '资金流入比例'] and '%' in str(value):
                            # 提取百分比数值
                            try:
                                pct_value = float(str(value).replace('%', ''))
                                colored_value = self._format_value_with_color(pct_value - 50, True, False)  # 以50%为基准
                                st.markdown(f"**{key}**: {colored_value}", unsafe_allow_html=True)
                            except:
                                st.metric(label=key, value=value)
                        elif key == '平均涨跌幅' and '%' in str(value):
                            try:
                                pct_value = float(str(value).replace('%', ''))
                                colored_value = self._format_value_with_color(pct_value, True)
                                st.markdown(f"**{key}**: {colored_value}", unsafe_allow_html=True)
                            except:
                                st.metric(label=key, value=value)
                        else:
                            st.metric(label=key, value=value)
            
            with col2:
                # 显示情绪仪表盘
                if config['show_sentiment_gauge']:
                    from sector.visualizer import create_sector_visualizer
                    visualizer = create_sector_visualizer()
                    gauge_chart = visualizer.create_market_sentiment_gauge(processed_data)
                    if gauge_chart:
                        st.plotly_chart(gauge_chart, width="stretch")
        
        # 显示概览图表
        if config['show_overview_chart']:
            st.subheader("📈 板块资金流向概览")
            from sector.visualizer import create_sector_visualizer
            visualizer = create_sector_visualizer()
            overview_chart = visualizer.create_sector_overview_chart(processed_data)
            if overview_chart:
                st.plotly_chart(overview_chart, width="stretch")
        
        # 显示排行榜
        if 'rankings' in processed_data:
            st.subheader("🏆 板块排行榜")
            
            # 排行榜选项卡
            tab1, tab2, tab3, tab4 = st.tabs(["💰 资金流入榜", "📉 资金流出榜", "📈 涨幅榜", "📊 跌幅榜"])
            
            with tab1:
                if config['show_ranking_charts']:
                    from sector.visualizer import create_sector_visualizer
                    visualizer = create_sector_visualizer()
                    inflow_chart = visualizer.create_sector_ranking_chart(processed_data, 'inflow')
                    if inflow_chart:
                        st.plotly_chart(inflow_chart, width="stretch")
                
                # 显示数据表格
                inflow_data = processed_data['rankings'].get('资金流入榜', [])
                if inflow_data:
                    df = pd.DataFrame(inflow_data)
                    # 格式化数据表格
                    df_display = df.copy()
                    if '主力资金' in df_display.columns:
                        df_display['主力资金'] = df_display['主力资金'].apply(lambda x: f"+{x:.2f}亿" if x > 0 else f"{x:.2f}亿")
                    if '涨跌幅' in df_display.columns:
                        df_display['涨跌幅'] = df_display['涨跌幅'].apply(lambda x: f"+{x:.2f}%" if x > 0 else f"{x:.2f}%")
                    st.dataframe(df_display, width="stretch")
            
            with tab2:
                if config['show_ranking_charts']:
                    from sector.visualizer import create_sector_visualizer
                    visualizer = create_sector_visualizer()
                    outflow_chart = visualizer.create_sector_ranking_chart(processed_data, 'outflow')
                    if outflow_chart:
                        st.plotly_chart(outflow_chart, width="stretch")
                
                # 显示数据表格
                outflow_data = processed_data['rankings'].get('资金流出榜', [])
                if outflow_data:
                    df = pd.DataFrame(outflow_data)
                    # 格式化数据表格
                    df_display = df.copy()
                    if '主力资金' in df_display.columns:
                        df_display['主力资金'] = df_display['主力资金'].apply(lambda x: f"+{x:.2f}亿" if x > 0 else f"{x:.2f}亿")
                    if '涨跌幅' in df_display.columns:
                        df_display['涨跌幅'] = df_display['涨跌幅'].apply(lambda x: f"+{x:.2f}%" if x > 0 else f"{x:.2f}%")
                    st.dataframe(df_display, width="stretch")
            
            with tab3:
                if config['show_ranking_charts']:
                    from sector.visualizer import create_sector_visualizer
                    visualizer = create_sector_visualizer()
                    rising_chart = visualizer.create_sector_ranking_chart(processed_data, 'rising')
                    if rising_chart:
                        st.plotly_chart(rising_chart, width="stretch")
                
                # 显示数据表格
                rising_data = processed_data['rankings'].get('涨幅榜', [])
                if rising_data:
                    df = pd.DataFrame(rising_data)
                    # 格式化数据表格
                    df_display = df.copy()
                    if '主力资金' in df_display.columns:
                        df_display['主力资金'] = df_display['主力资金'].apply(lambda x: f"+{x:.2f}亿" if x > 0 else f"{x:.2f}亿")
                    if '涨跌幅' in df_display.columns:
                        df_display['涨跌幅'] = df_display['涨跌幅'].apply(lambda x: f"+{x:.2f}%" if x > 0 else f"{x:.2f}%")
                    st.dataframe(df_display, width="stretch")
            
            with tab4:
                if config['show_ranking_charts']:
                    from sector.visualizer import create_sector_visualizer
                    visualizer = create_sector_visualizer()
                    falling_chart = visualizer.create_sector_ranking_chart(processed_data, 'falling')
                    if falling_chart:
                        st.plotly_chart(falling_chart, width="stretch")
                
                # 显示数据表格
                falling_data = processed_data['rankings'].get('跌幅榜', [])
                if falling_data:
                    df = pd.DataFrame(falling_data)
                    st.dataframe(df, width="stretch")
        
        # 显示详细数据表格
        with st.expander("📋 查看所有板块详细数据", expanded=False):
            if 'raw_data' in processed_data:
                st.dataframe(processed_data['raw_data'], width="stretch")
    
    def show_sector_detail_results(self, config: dict):
        """显示板块详情结果"""
        if not st.session_state.sector_detail_data:
            return
        
        detail_data = st.session_state.sector_detail_data
        sector_name = detail_data.get('sector_name', '未知板块')
        
        # 显示板块基本信息
        st.subheader(f"🏢 {sector_name} 详细分析")
        
        # 显示汇总指标
        if 'summary' in detail_data:
            summary = detail_data['summary']
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="📊 成分股数量",
                    value=summary.get('成分股数量', 0)
                )
            
            with col2:
                st.metric(
                    label="💰 板块总资金净流入",
                    value=summary.get('板块总资金净流入', '0.00万元')
                )
            
            with col3:
                st.metric(
                    label="📈 平均涨跌幅",
                    value=summary.get('平均涨跌幅', '0.00%')
                )
            
            with col4:
                st.metric(
                    label="📊 上涨比例",
                    value=summary.get('上涨比例', '0.0%')
                )
        
        # 显示板块强度分析
        if 'strength_analysis' in detail_data:
            st.subheader("💪 板块强度分析")
            strength = detail_data['strength_analysis']
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    label="🏆 板块强度",
                    value=strength.get('板块强度', 'N/A')
                )
            
            with col2:
                st.metric(
                    label="🚀 涨停股数量",
                    value=strength.get('涨停股数量', 0)
                )
            
            with col3:
                st.metric(
                    label="🎯 龙头效应",
                    value=strength.get('龙头效应', 'N/A')
                )
        
        # 显示详细图表
        st.subheader("📈 板块详细分析图表")
        from sector.visualizer import create_sector_visualizer
        visualizer = create_sector_visualizer()
        detail_chart = visualizer.create_sector_detail_chart(detail_data)
        if detail_chart:
            st.plotly_chart(detail_chart, width="stretch")
        
        # 显示个股排行榜
        if 'stock_rankings' in detail_data:
            st.subheader("🏆 成分股排行榜")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 💰 资金流入榜")
                inflow_stocks = detail_data['stock_rankings'].get('资金流入榜', [])
                if inflow_stocks:
                    df = pd.DataFrame(inflow_stocks)
                    st.dataframe(df, width="stretch")
                else:
                    st.info("暂无资金流入数据")
            
            with col2:
                st.markdown("#### 📉 资金流出榜")
                outflow_stocks = detail_data['stock_rankings'].get('资金流出榜', [])
                if outflow_stocks:
                    df = pd.DataFrame(outflow_stocks)
                    st.dataframe(df, width="stretch")
                else:
                    st.info("暂无资金流出数据")
        
        # 显示所有成分股数据
        with st.expander("📋 查看所有成分股详细数据", expanded=False):
            if 'raw_data' in detail_data:
                st.dataframe(detail_data['raw_data'], width="stretch")
            else:
                st.info("暂无详细数据")
    
    def show_margin_sidebar(self):
        """显示两融交易查询侧边栏配置"""
        st.sidebar.header("🔧 查询配置")
        
        # 日期范围选择
        st.sidebar.subheader("📅 日期范围")
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            start_date = st.date_input(
                "开始日期",
                value=datetime.now() - timedelta(days=30),
                max_value=datetime.now()
            )
        
        with col2:
            end_date = st.date_input(
                "结束日期",
                value=datetime.now(),
                max_value=datetime.now()
            )
        
        # 查询选项
        st.sidebar.subheader("⚙️ 查询选项")
        
        use_cache = st.sidebar.checkbox("使用缓存数据", value=True, 
                                       help="使用缓存可以加快查询速度")
        
        export_format = st.sidebar.selectbox(
            "导出格式",
            ["CSV", "Excel", "JSON"],
            index=0
        )
        
        # 图表选项
        st.sidebar.subheader("📊 图表选项")
        
        show_balance_chart = st.sidebar.checkbox("余额趋势图", value=True)
        show_ratio_chart = st.sidebar.checkbox("占比分析图", value=True)
        show_correlation = st.sidebar.checkbox("相关性分析", value=False)
        show_dashboard = st.sidebar.checkbox("交互式仪表板", value=True)
        
        # 查询按钮
        st.sidebar.markdown("---")  # 分隔线
        query_button = st.sidebar.button("🚀 开始查询", type="primary", width="stretch")
        
        return {
            'start_date': start_date.strftime('%Y%m%d'),
            'end_date': end_date.strftime('%Y%m%d'),
            'use_cache': use_cache,
            'export_format': export_format.lower(),
            'show_balance_chart': show_balance_chart,
            'show_ratio_chart': show_ratio_chart,
            'show_correlation': show_correlation,
            'show_dashboard': show_dashboard,
            'query_button': query_button
        }
    
    def query_margin_data(self, config):
        """查询两融数据"""
        try:
            # 创建进度条
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 获取两融数据
            status_text.text("正在获取两融数据...")
            progress_bar.progress(20)
            margin_data = self.data_fetcher.get_margin_trading_summary(
                config['start_date'], 
                config['end_date'],
                use_cache=config['use_cache']
            )
            
            if margin_data.empty:
                progress_bar.empty()
                status_text.empty()
                st.error("❌ 未获取到数据，请检查网络连接或数据源")
                return False
            
            st.session_state.margin_data = margin_data
            
            # 获取市场数据
            status_text.text("正在获取市场数据...")
            progress_bar.progress(50)
            market_data = self.data_fetcher.get_market_turnover(
                config['start_date'], 
                config['end_date']
            )
            
            # 处理数据
            status_text.text("正在处理数据...")
            progress_bar.progress(80)
            processed_data = self.data_processor.process_margin_summary(
                margin_data, market_data
            )
            st.session_state.processed_data = processed_data
            
            # 生成分析结果
            status_text.text("正在生成分析结果...")
            progress_bar.progress(95)
            analysis_result = self.data_processor.analyze_margin_trends(processed_data)
            st.session_state.analysis_result = analysis_result
            
            # 完成
            progress_bar.progress(100)
            status_text.text("数据处理完成！")
            
            # 清除进度条和状态文本
            progress_bar.empty()
            status_text.empty()
            
            st.success(f"✅ 成功获取并处理了 {len(processed_data)} 条数据记录")
            return True
            
        except Exception as e:
            st.error(f"❌ 查询失败: {str(e)}")
            return False
    
    def query_etf_data(self, config):
        """查询ETF数据"""
        try:
            # 检查是否是新的ETF代码，如果是则清除旧数据
            current_etf_code = config['etf_code']
            if 'current_etf_code' not in st.session_state or st.session_state.current_etf_code != current_etf_code:
                # 清除旧的ETF数据
                if 'etf_data' in st.session_state:
                    del st.session_state.etf_data
                # 记录当前ETF代码
                st.session_state.current_etf_code = current_etf_code
            
            # 初始化ETF组件
            from etf.fetcher import create_etf_fetcher
            from etf.processor import create_etf_processor
            from etf.visualizer import create_etf_visualizer
            
            etf_fetcher = create_etf_fetcher()
            etf_processor = create_etf_processor()
            etf_visualizer = create_etf_visualizer()
            
            # 创建进度条
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 获取ETF基本信息
            status_text.text("正在获取ETF基本信息...")
            progress_bar.progress(10)
            etf_info = etf_fetcher.get_etf_info(config['etf_code'], use_cache=config['use_cache'])
            
            # 获取ETF资金流向数据
            status_text.text("正在获取ETF资金流向数据...")
            progress_bar.progress(25)
            fund_flow_data = etf_fetcher.get_etf_fund_flow(
                config['etf_code'], 
                config['start_date'], 
                config['end_date'],
                use_cache=config['use_cache']
            )
            
            # 获取ETF份额变动数据
            status_text.text("正在获取ETF份额变动数据...")
            progress_bar.progress(40)
            share_change_data = etf_fetcher.get_etf_share_changes(
                config['etf_code'], 
                config['start_date'], 
                config['end_date'],
                use_cache=config['use_cache']
            )
            
            # 获取ETF场外市场数据
            status_text.text("正在获取ETF场外市场数据...")
            progress_bar.progress(55)
            outside_data = etf_fetcher.get_etf_outside_market_data(
                config['etf_code'], 
                config['start_date'], 
                config['end_date'],
                use_cache=config['use_cache']
            )
            
            # 获取ETF分钟数据（用于换手率分析等，可以缓存）
            status_text.text("正在获取ETF分钟数据...")
            progress_bar.progress(70)
            minute_data = etf_fetcher.get_etf_minute_data(
                config['etf_code'],
                use_cache=config['use_cache'],
                for_realtime=False
            )
            

            
            # 处理ETF数据
            status_text.text("正在处理ETF数据...")
            progress_bar.progress(95)
            processed_etf_data = etf_processor.process_etf_data(
                fund_flow_data, share_change_data, outside_data, minute_data
            )
            
            # 添加基本信息
            processed_etf_data['info'] = etf_info
            
            # 保存到session state
            st.session_state.etf_data = processed_etf_data
            
            # 完成
            progress_bar.progress(100)
            status_text.text("数据处理完成！")
            
            # 清除进度条和状态文本
            progress_bar.empty()
            status_text.empty()
            
            st.success(f"✅ 成功获取并处理了ETF {config['etf_code']} 的数据")
            return True
            
        except Exception as e:
            st.error(f"❌ ETF查询失败: {str(e)}")
            return False
    
    def show_summary_metrics(self):
        """显示两融汇总指标"""
        if st.session_state.analysis_result:
            st.subheader("📊 数据概览")
            
            analysis = st.session_state.analysis_result
            
            # 创建指标列
            col1, col2, col3, col4 = st.columns(4)
            
            # 数据概况
            if '数据概况' in analysis:
                overview = analysis['数据概况']
                with col1:
                    st.metric(
                        label="📅 数据天数",
                        value=f"{overview.get('数据天数', 0)} 天"
                    )
            
            # 两融余额
            if '两融余额分析' in analysis:
                balance = analysis['两融余额分析']
                with col2:
                    st.metric(
                        label="💰 最新余额",
                        value=balance.get('最新余额', 'N/A')
                    )
                
                with col3:
                    st.metric(
                        label="📈 最高余额",
                        value=balance.get('最高余额', 'N/A')
                    )
                
                with col4:
                    st.metric(
                        label="📊 波动率",
                        value=balance.get('余额波动率', 'N/A')
                    )
            
            # 结构分析
            if '融资融券结构' in analysis:
                st.subheader("🏗️ 融资融券结构")
                structure = analysis['融资融券结构']
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        label="💼 融资余额",
                        value=structure.get('融资余额', 'N/A')
                    )
                
                with col2:
                    st.metric(
                        label="📉 融券余额", 
                        value=structure.get('融券余额', 'N/A')
                    )
                
                with col3:
                    financing_ratio = structure.get('融资占比', '0%')
                    st.metric(
                        label="📊 融资占比",
                        value=financing_ratio
                    )
            
            # 趋势和风险
            col1, col2 = st.columns(2)
            
            if '趋势分析' in analysis:
                with col1:
                    trend = analysis['趋势分析']
                    st.metric(
                        label="📈 近期趋势",
                        value=trend.get('趋势判断', 'N/A'),
                        delta=trend.get('近5日平均变化率', 'N/A')
                    )
            
            if '风险评估' in analysis:
                with col2:
                    risk = analysis['风险评估']
                    rsi_value = risk.get('RSI指标', '50')
                    risk_level = risk.get('风险等级', 'N/A')
                    
                    st.metric(
                        label="⚠️ 风险评估",
                        value=risk_level,
                        delta=f"RSI: {rsi_value}"
                    )
    
    def show_etf_info(self, etf_info: dict):
        """显示ETF基本信息"""
        if etf_info:
            st.subheader("📈 ETF基本信息")
            
            # 显示基金名称和代码
            fund_name = etf_info.get('基金简称', f'ETF-{etf_info.get("基金代码", "N/A")}')
            fund_code = etf_info.get('基金代码', 'N/A')
            st.markdown(f"### {fund_name} ({fund_code})")
            
            # 显示基本信息
            col1, col2, col3 = st.columns(3)
            
            with col1:
                establishment_date = etf_info.get('成立日期', 'N/A')
                st.metric(
                    label="📅 成立日期",
                    value=establishment_date
                )
            
            with col2:
                fund_size = etf_info.get('基金规模', 'N/A')
                st.metric(
                    label="💰 基金规模",
                    value=fund_size
                )
            
            with col3:
                tracking_index = etf_info.get('跟踪标的', 'N/A')
                st.metric(
                    label="📊 跟踪标的",
                    value=tracking_index
                )
        else:
            st.subheader("📈 ETF基本信息")
            st.info("正在获取ETF基本信息...")
    
    def show_etf_summary_metrics(self, analysis: dict):
        """显示ETF汇总指标"""
        if analysis:
            st.subheader("📊 ETF数据概览")
            
            # 资金流向分析
            if 'fund_flow' in analysis:
                fund_flow = analysis['fund_flow']
                st.markdown("#### 💰 资金流向分析")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_flow = fund_flow.get('total_net_flow', 0)
                    st.metric(
                        label="总净流入",
                        value=f"{total_flow:,.2f}亿元" if total_flow != 0 else "0.00亿元"
                    )
                
                with col2:
                    avg_flow = fund_flow.get('avg_daily_flow', 0)
                    st.metric(
                        label="日均净流入",
                        value=f"{avg_flow:,.2f}亿元" if avg_flow != 0 else "0.00亿元"
                    )
                
                with col3:
                    latest_flow = fund_flow.get('latest_flow', 0)
                    st.metric(
                        label="最新流向",
                        value=f"{latest_flow:,.2f}亿元" if latest_flow != 0 else "0.00亿元"
                    )
                
                with col4:
                    st.metric(
                        label="近期趋势",
                        value=fund_flow.get('recent_trend', '资金平衡')
                    )
            
            # 份额变动分析
            if 'share_changes' in analysis:
                share_changes = analysis['share_changes']
                st.markdown("#### 📈 份额变动分析")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    initial_shares = share_changes.get('initial_shares', 0)
                    st.metric(
                        label="期初份额",
                        value=f"{initial_shares:,.2f}亿份" if initial_shares != 0 else "0.00亿份"
                    )
                
                with col2:
                    final_shares = share_changes.get('final_shares', 0)
                    st.metric(
                        label="期末份额",
                        value=f"{final_shares:,.2f}亿份" if final_shares != 0 else "0.00亿份"
                    )
                
                with col3:
                    total_change = share_changes.get('total_change', 0)
                    st.metric(
                        label="总变动",
                        value=f"{total_change:,.2f}亿份" if total_change != 0 else "0.00亿份"
                    )
                
                with col4:
                    change_rate = share_changes.get('change_rate', 0)
                    st.metric(
                        label="变动率",
                        value=f"{change_rate:.2f}%" if change_rate != 0 else "0.00%"
                    )
            
            # 场外市场分析
            if 'outside_market' in analysis:
                outside_market = analysis['outside_market']
                st.markdown("#### 🏦 场外市场分析")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_sub = outside_market.get('total_subscription', 0)
                    st.metric(
                        label="总申购",
                        value=f"{total_sub:,.2f}亿元" if total_sub != 0 else "0.00亿元"
                    )
                
                with col2:
                    total_red = outside_market.get('total_redemption', 0)
                    st.metric(
                        label="总赎回",
                        value=f"{total_red:,.2f}亿元" if total_red != 0 else "0.00亿元"
                    )
                
                with col3:
                    net_sub = outside_market.get('net_subscription', 0)
                    st.metric(
                        label="净申购",
                        value=f"{net_sub:,.2f}亿元" if net_sub != 0 else "0.00亿元"
                    )
                
                with col4:
                    st.metric(
                        label="近期趋势",
                        value=outside_market.get('recent_subscription_trend', '申赎平衡')
                    )
    
    def show_margin_charts(self, config):
        """显示两融图表"""
        if st.session_state.processed_data.empty:
            return
        
        df = st.session_state.processed_data
        
        # 确保dates变量总是被定义
        dates = pd.to_datetime(df['交易日期']) if '交易日期' in df.columns else list(range(len(df)))
        
        # 余额趋势图
        if config['show_balance_chart']:
            st.subheader("📈 两融交易数据趋势分析")
            
            fig = make_subplots(
                rows=4, cols=1,
                subplot_titles=['两融余额趋势', '两融余额日变化率', '净融资额趋势', '维持担保比例'],
                vertical_spacing=0.08
            )
            
            # 初始化纵轴范围变量
            y1_min, y1_max = None, None
            y2_min, y2_max = None, None
            y3_min, y3_max = None, None
            
            # 1. 两融余额趋势 - 显示绝对值，增强可见性
            if '两融余额' in df.columns:
                # 计算统计信息
                balance_values = df['两融余额'] / 1e12  # 转换为万亿
                mean_balance = balance_values.mean()
                min_balance = balance_values.min()
                max_balance = balance_values.max()
                balance_range = max_balance - min_balance
                
                fig.add_trace(
                    go.Scatter(
                        x=dates, 
                        y=balance_values,
                        name='两融余额',
                        line=dict(color='#FF6B6B', width=3),
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                     '日期: %{x}<br>' +
                                     '两融余额: %{y:.2f}万亿<br>' +
                                     '<extra></extra>'
                    ),
                    row=1, col=1
                )
                
                # 添加均值参考线
                fig.add_hline(y=mean_balance, line_dash="dash", line_color="gray", 
                            annotation_text=f"均值线 ({mean_balance:.2f}万亿)", row=1, col=1)
                
                # 自定义纵轴范围
                margin = balance_range * 0.05
                y1_min = max(0, min_balance - margin)
                y1_max = max_balance + margin
            
            # 2. 两融余额日变化率 - 显示绝对值
            if '两融余额_日变化率' in df.columns:
                # 计算统计信息
                change_rate = df['两融余额_日变化率']
                mean_change = change_rate.mean()
                min_change = change_rate.min()
                max_change = change_rate.max()
                change_range = max_change - min_change
                
                fig.add_trace(
                    go.Scatter(
                        x=dates, 
                        y=change_rate,
                        name='日变化率',
                        line=dict(color='#9370DB', width=2),
                        fill='tozeroy',
                        fillcolor='rgba(147, 112, 219, 0.3)',
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                     '日期: %{x}<br>' +
                                     '日变化率: %{y:.2f}%<br>' +
                                     '<extra></extra>'
                    ),
                    row=2, col=1
                )
                
                # 添加零基准线和均值线
                fig.add_hline(y=0, line_dash="dash", line_color="gray", 
                            annotation_text="零变化线", row=2, col=1)
                fig.add_hline(y=mean_change, line_dash="dot", line_color="blue", 
                            annotation_text=f"均值线 ({mean_change:.2f}%)", row=2, col=1)
                
                # 自定义纵轴范围
                margin = change_range * 0.1 if change_range > 0 else 0.1
                y2_min = min_change - margin
                y2_max = max_change + margin
            
            # 3. 净融资额趋势 - 显示绝对值
            if '净融资额' in df.columns:
                # 计算统计信息
                net_values = df['净融资额'] / 1e12  # 转换为万亿
                mean_net = net_values.mean()
                min_net = net_values.min()
                max_net = net_values.max()
                net_range = max_net - min_net
                
                fig.add_trace(
                    go.Scatter(
                        x=dates, 
                        y=net_values,
                        name='净融资额',
                        line=dict(color='#4ECDC4', width=2),
                        fill='tozeroy',
                        fillcolor='rgba(78, 205, 196, 0.3)',
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                     '日期: %{x}<br>' +
                                     '净融资额: %{y:.2f}万亿<br>' +
                                     '<extra></extra>'
                    ),
                    row=3, col=1
                )
                
                # 添加零基准线和均值线
                fig.add_hline(y=0, line_dash="dash", line_color="gray", 
                            annotation_text="零基准线", row=3, col=1)
                fig.add_hline(y=mean_net, line_dash="dot", line_color="blue", 
                            annotation_text=f"均值线 ({mean_net:.2f}万亿)", row=3, col=1)
                
                # 自定义纵轴范围
                margin = net_range * 0.1 if net_range > 0 else 0.1
                y3_min = min_net - margin
                y3_max = max_net + margin
            
            # 4. 市场整体维持担保比例
            if '市场整体维持担保比例' in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=dates, 
                        y=df['市场整体维持担保比例'],
                        name='维持担保比例',
                        line=dict(color='#45B7D1', width=2),
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                     '日期: %{x}<br>' +
                                     '担保比例: %{y:.1f}%<br>' +
                                     '<extra></extra>'
                    ),
                    row=4, col=1
                )
                
                # 添加风险参考线
                fig.add_hline(y=130, line_dash="dash", line_color="red", 
                            annotation_text="最低风险线(130%)", row=4, col=1)
                fig.add_hline(y=150, line_dash="dash", line_color="orange", 
                            annotation_text="警戒线(150%)", row=4, col=1)
                fig.add_hline(y=200, line_dash="dash", line_color="green", 
                            annotation_text="安全线(200%)", row=4, col=1)
            
            fig.update_layout(
                height=1200,  # 增加高度以适应四个子图
                showlegend=True,
                title_text="两融交易数据趋势分析",
                title_x=0.5
            )
            
            # 为每个子图设置自定义纵轴范围
            if '两融余额' in df.columns and y1_min is not None and y1_max is not None:
                fig.update_yaxes(title_text="两融余额 (万亿)", range=[y1_min, y1_max], row=1, col=1)
            else:
                fig.update_yaxes(title_text="两融余额 (万亿)", row=1, col=1)
            
            if '两融余额_日变化率' in df.columns and y2_min is not None and y2_max is not None:
                fig.update_yaxes(title_text="日变化率 (%)", range=[y2_min, y2_max], row=2, col=1)
            else:
                fig.update_yaxes(title_text="日变化率 (%)", row=2, col=1)
            
            if '净融资额' in df.columns and y3_min is not None and y3_max is not None:
                fig.update_yaxes(title_text="净融资额 (万亿)", range=[y3_min, y3_max], row=3, col=1)
            else:
                fig.update_yaxes(title_text="净融资额 (万亿)", row=3, col=1)
                
            fig.update_yaxes(title_text="担保比例 (%)", row=4, col=1)
            
            # 添加说明文字
            st.info("💡 **图表说明**：\n" +
                   "• **两融余额**：显示实际余额数值（万亿），纵轴范围已优化以突出变化\n" +
                   "• **日变化率**：两融余额相比前一日的变化百分比，显示实际波动幅度\n" +
                   "• **净融资额**：融资余额减去融券余额（万亿），反映市场做多情绪强度\n" +
                   "• **维持担保比例**：衡量市场整体杠杆风险的安全垫指标，130%为最低要求\n" +
                   "• 所有图表纵轴范围均已优化至实际数据范围，鼠标悬停可查看详细数值")
            
            st.plotly_chart(fig, width='stretch')
        
        # 占比分析图
        if config['show_ratio_chart']:
            st.subheader("📊 融资占比趋势分析")
            
            if '融资余额' in df.columns and '融券余额' in df.columns and len(df) > 0:
                # 计算融资占比
                total_balance = df['融资余额'] + df['融券余额']
                financing_ratio = (df['融资余额'] / total_balance * 100)
                
                # 计算统计信息
                mean_financing_ratio = financing_ratio.mean()
                min_ratio = financing_ratio.min()
                max_ratio = financing_ratio.max()
                ratio_range = max_ratio - min_ratio
                
                # 创建单个图表
                fig_ratio = go.Figure()
                
                # 融资占比趋势 - 显示绝对值
                fig_ratio.add_trace(
                    go.Scatter(
                        x=dates,
                        y=financing_ratio,
                        name='融资占比',
                        line=dict(color='#FF6B6B', width=3),
                        fill='tozeroy',
                        fillcolor='rgba(255, 107, 107, 0.2)',
                        hovertemplate='<b>融资占比</b><br>' +
                                     '日期: %{x}<br>' +
                                     '融资占比: %{y:.2f}%<br>' +
                                     '<extra></extra>'
                    )
                )
                
                # 添加均值参考线
                fig_ratio.add_hline(y=mean_financing_ratio, line_dash="dash", line_color="gray", 
                                   annotation_text=f"均值线 ({mean_financing_ratio:.2f}%)")
                
                # 自定义纵轴范围：从最小值到最大值，留一点边距
                margin = ratio_range * 0.05  # 5%的边距
                y_min = max(0, min_ratio - margin)  # 确保不小于0
                y_max = min(100, max_ratio + margin)  # 确保不大于100
                
                # 更新布局
                fig_ratio.update_layout(
                    height=400,
                    showlegend=True,
                    title_text="融资占比时间序列分析",
                    title_x=0.5,
                    yaxis_title="融资占比 (%)",
                    yaxis=dict(
                        range=[y_min, y_max],
                        tickformat='.2f'
                    )
                )
                
                # 添加说明信息
                st.info("💡 **图表说明**：\n" +
                       f"• **融资占比范围**: {min_ratio:.2f}% ~ {max_ratio:.2f}%\n" +
                       f"• **均值**: {mean_financing_ratio:.2f}%\n" +
                       f"• **波动幅度**: {ratio_range:.2f}个百分点\n" +
                       "• 纵轴范围已优化至实际数据范围，突出变化幅度\n" +
                       "• 鼠标悬停可查看详细数据")
                
                st.plotly_chart(fig_ratio, width='stretch')
            
            # RSI相对强弱指标
            if '两融余额_RSI' in df.columns:
                fig_rsi = go.Figure()
                
                fig_rsi.add_trace(go.Scatter(
                    x=dates, y=df['两融余额_RSI'],
                    name='RSI', line=dict(color='#45B7D1', width=2)
                ))
                
                # 添加参考线
                fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", 
                                annotation_text="超买线")
                fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", 
                                annotation_text="超卖线")
                fig_rsi.add_hline(y=50, line_dash="dash", line_color="gray", 
                                annotation_text="中位线")
                
                fig_rsi.update_layout(
                    title="RSI相对强弱指标",
                    yaxis_title="RSI",
                    height=400,
                    yaxis=dict(range=[0, 100])
                )
                
                st.plotly_chart(fig_rsi, width='stretch')
        
        # 相关性分析
        if config['show_correlation']:
            st.subheader("🔗 相关性分析")
            
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            exclude_patterns = ['_日变化', '_周变化', '_月变化', 'MA', 'RSI', '布林']
            filtered_columns = [col for col in numeric_columns 
                              if not any(pattern in col for pattern in exclude_patterns)]
            
            if len(filtered_columns) >= 2:
                corr_matrix = df[filtered_columns].corr()
                
                fig_heatmap = px.imshow(
                    corr_matrix,
                    labels=dict(color="相关系数"),
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    color_continuous_scale='RdBu_r',
                    aspect="auto"
                )
                
                fig_heatmap.update_layout(
                    title="数据相关性热力图",
                    height=500
                )
                
                st.plotly_chart(fig_heatmap, width='stretch')
    
    def show_etf_charts(self, config, etf_data):
        """显示ETF图表"""
        # 初始化ETF可视化器
        from etf.visualizer import create_etf_visualizer
        etf_visualizer = create_etf_visualizer()
        
        # 获取数据
        fund_flow_data = etf_data.get('fund_flow', pd.DataFrame())
        share_change_data = etf_data.get('share_changes', pd.DataFrame())
        outside_data = etf_data.get('outside_market', pd.DataFrame())
        minute_data = etf_data.get('minute_data', pd.DataFrame())
        
        # 创建标签页
        tab1, tab2, tab3 = st.tabs(["基础图表", "实时估值分析", "换手率分析"])
        
        # 基础图表标签页
        with tab1:
            # 资金流向图
            if config['show_fund_flow_chart'] and not fund_flow_data.empty:
                st.subheader("💰 ETF资金流向趋势")
                fund_flow_fig = etf_visualizer.create_fund_flow_chart(fund_flow_data)
                st.plotly_chart(fund_flow_fig, width='stretch')
            
            # 份额变动图
            if config['show_share_change_chart'] and not share_change_data.empty:
                st.subheader("📈 ETF份额变动趋势")
                share_change_fig = etf_visualizer.create_share_change_chart(share_change_data)
                st.plotly_chart(share_change_fig, width='stretch')
            
            # 申购赎回图
            if config['show_subscription_chart'] and not outside_data.empty:
                st.subheader("🏦 ETF申购赎回情况")
                subscription_fig = etf_visualizer.create_subscription_redemption_chart(outside_data)
                st.plotly_chart(subscription_fig, width='stretch')
            
            # 综合分析图
            if config['show_comprehensive_chart'] and (not fund_flow_data.empty or 
                                                      not share_change_data.empty or 
                                                      not outside_data.empty):
                st.subheader("📊 ETF综合分析图表")
                comprehensive_fig = etf_visualizer.create_comprehensive_etf_chart(
                    fund_flow_data, share_change_data, outside_data)
                st.plotly_chart(comprehensive_fig, width='stretch')
        
        # 实时估值分析标签页
        with tab2:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.subheader("📈 ETF实时估值与价格变化趋势")
            with col2:
                refresh_realtime = st.button("🔄 刷新实时数据", help="获取最新的分钟级数据")
            
            # 为实时分析获取最新的分钟数据（不使用缓存）
            if refresh_realtime or 'realtime_minute_data' not in st.session_state:
                with st.spinner("正在获取最新实时数据..."):
                    etf_code = etf_data.get('info', {}).get('基金代码', '510310')
                    
                    # 创建fetcher获取实时数据
                    from etf.fetcher import create_etf_fetcher
                    realtime_fetcher = create_etf_fetcher()
                    realtime_minute_data = realtime_fetcher.get_etf_minute_data(
                        etf_code, period="1", use_cache=False, for_realtime=True
                    )
                    
                    # 保存到session state
                    st.session_state.realtime_minute_data = realtime_minute_data
            else:
                realtime_minute_data = st.session_state.realtime_minute_data
            
            if not realtime_minute_data.empty:
                realtime_fig = etf_visualizer.create_etf_realtime_valuation_chart(realtime_minute_data)
                st.plotly_chart(realtime_fig, width='stretch')
                
                # 显示数据更新时间
                from datetime import datetime
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                st.success(f"✅ 实时数据已更新 - {current_time}")
                
                # 添加说明
                st.info("💡 **图表说明**：\n" +
                       "• **收盘价**：ETF在每个时间点的收盘价格\n" +
                       "• **均价**：作为实时估值的近似值，反映ETF的平均交易价格\n" +
                       "• 图表显示了ETF在查询当天的价格变化趋势\n" +
                       "• **实时数据**：每次查看此标签页都会获取最新数据，不使用缓存")
            else:
                st.warning("⚠️ 暂无最新分钟级别数据，无法显示实时估值分析")
        
        # 换手率分析标签页
        with tab3:
            st.subheader("🔄 ETF换手率变化曲线")
            if not minute_data.empty:
                turnover_fig = etf_visualizer.create_turnover_rate_chart(minute_data)
                st.plotly_chart(turnover_fig, width='stretch')
                
                # 添加说明
                st.info("💡 **图表说明**：\n" +
                       "• **换手率**：反映ETF的交易活跃程度，按日计算\n" +
                       "• **均值线**：换手率的历史均值参考线\n" +
                       "• 图表显示了ETF每日的换手率变化趋势")
            else:
                st.info("暂无分钟级别数据，无法显示换手率分析")
        

    
    def show_margin_data_table(self):
        """显示两融数据表格"""
        if not st.session_state.processed_data.empty:
            st.subheader("📋 详细数据")
            
            # 选择要显示的列
            all_columns = st.session_state.processed_data.columns.tolist()
            
            # 默认显示的重要列
            default_columns = []
            important_patterns = ['交易日期', '融资余额', '融券余额', '两融余额', '变化率', '占比']
            
            for pattern in important_patterns:
                matching_cols = [col for col in all_columns if pattern in col]
                default_columns.extend(matching_cols)
            
            # 去重并保持顺序
            default_columns = list(dict.fromkeys(default_columns))
            
            selected_columns = st.multiselect(
                "选择要显示的列:",
                options=all_columns,
                default=default_columns[:10]  # 最多显示10列
            )
            
            if selected_columns:
                display_df = st.session_state.processed_data[selected_columns].copy()
                
                # 格式化数值列
                for col in display_df.columns:
                    if display_df[col].dtype in ['float64', 'int64']:
                        if '余额' in col:
                            display_df[col] = display_df[col].apply(lambda x: format_number(x) if pd.notna(x) else 'N/A')
                        elif '率' in col or '比' in col:
                            display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else 'N/A')
                
                st.dataframe(display_df, width='stretch', height=400)
                
                # 下载按钮
                if st.button("📥 下载数据"):
                    csv = st.session_state.processed_data.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="下载CSV文件",
                        data=csv,
                        file_name=f"margin_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
    
    def show_etf_data_table(self, etf_data):
        """显示ETF数据表格"""
        if etf_data:
            st.subheader("📋 ETF详细数据")
            
            # 创建标签页显示不同类型的数据
            tab1, tab2, tab3 = st.tabs(["资金流向", "份额变动", "场外市场"])
            
            with tab1:
                fund_flow_data = etf_data.get('fund_flow', pd.DataFrame())
                if not fund_flow_data.empty:
                    st.dataframe(fund_flow_data, width='stretch', height=400)
                    
                    # 下载按钮
                    if st.button("📥 下载资金流向数据"):
                        csv = fund_flow_data.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="下载CSV文件",
                            data=csv,
                            file_name=f"etf_fund_flow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                else:
                    st.info("暂无资金流向数据")
            
            with tab2:
                share_change_data = etf_data.get('share_changes', pd.DataFrame())
                if not share_change_data.empty:
                    st.dataframe(share_change_data, width='stretch', height=400)
                    
                    # 下载按钮
                    if st.button("📥 下载份额变动数据"):
                        csv = share_change_data.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="下载CSV文件",
                            data=csv,
                            file_name=f"etf_share_changes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                else:
                    st.info("暂无份额变动数据")
            
            with tab3:
                outside_data = etf_data.get('outside_market', pd.DataFrame())
                if not outside_data.empty:
                    st.dataframe(outside_data, width='stretch', height=400)
                    
                    # 下载按钮
                    if st.button("📥 下载场外市场数据"):
                        csv = outside_data.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="下载CSV文件",
                            data=csv,
                            file_name=f"etf_outside_market_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                else:
                    st.info("暂无场外市场数据")
    
    def run(self):
        """运行Web应用"""
        # 根据当前页面显示不同内容
        if st.session_state.current_page == "main":
            self.show_main_page()
        elif st.session_state.current_page == "margin":
            self.show_margin_trading_page()
        elif st.session_state.current_page == "etf":
            self.show_etf_page()
        elif st.session_state.current_page == "sector":
            self.show_sector_page()

def main():
    """主函数"""
    app = MarginTradingWebApp()
    app.run()

if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
启动Web应用
"""

import streamlit as st
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入主应用
from app import MarginTradingWebApp

def main():
    """主函数"""
    try:
        # 创建应用实例
        app = MarginTradingWebApp()
        
        # 根据当前页面状态显示相应内容
        if st.session_state.current_page == "main":
            app.show_main_page()
        elif st.session_state.current_page == "margin":
            app.show_margin_trading_page()
        elif st.session_state.current_page == "etf":
            app.show_etf_page()
        elif st.session_state.current_page == "sector":
            app.show_sector_page()
        else:
            # 默认显示主页
            st.session_state.current_page = "main"
            app.show_main_page()
            
    except Exception as e:
        st.error(f"应用启动失败: {str(e)}")
        st.info("请检查依赖包是否正确安装")

if __name__ == "__main__":
    main()
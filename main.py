"""
主程序入口 - A股两融交易查询系统
提供命令行界面和程序入口
"""

import argparse
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Optional

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import MARGIN_TRADING_CONFIG
from utils import setup_logging, ensure_directories, save_data
from data_fetcher import create_margin_fetcher
from data_processor import create_margin_processor
from visualizer import create_margin_visualizer

class MarginTradingApp:
    """两融交易查询应用程序"""
    
    def __init__(self):
        # 设置日志
        self.logger = setup_logging()
        
        # 确保目录存在
        ensure_directories()
        
        # 初始化组件
        self.data_fetcher = create_margin_fetcher()
        self.data_processor = create_margin_processor()
        self.visualizer = create_margin_visualizer()
        
        self.logger.info("A股两融交易查询系统初始化完成")
    
    def query_margin_data(self, start_date: str, end_date: str, 
                         export_format: str = 'csv',
                         create_charts: bool = True,
                         create_dashboard: bool = False) -> bool:
        """
        查询两融数据并生成分析报告
        :param start_date: 开始日期 YYYYMMDD
        :param end_date: 结束日期 YYYYMMDD  
        :param export_format: 导出格式 ('csv', 'excel', 'json')
        :param create_charts: 是否创建图表
        :param create_dashboard: 是否创建交互式仪表板
        :return: 操作是否成功
        """
        try:
            self.logger.info(f"开始查询两融数据: {start_date} - {end_date}")
            
            # 1. 获取数据
            print("正在获取两融数据...")
            margin_data = self.data_fetcher.get_margin_trading_summary(start_date, end_date)
            
            if margin_data.empty:
                print("❌ 未获取到数据，请检查网络连接或数据源")
                return False
            
            print(f"✅ 成功获取 {len(margin_data)} 条数据记录")
            
            # 2. 获取市场数据（可选）
            print("正在获取市场成交数据...")
            market_data = self.data_fetcher.get_market_turnover(start_date, end_date)
            
            # 3. 数据处理
            print("正在处理数据...")
            processed_data = self.data_processor.process_margin_summary(margin_data, market_data)
            
            # 4. 生成分析报告
            print("正在生成分析报告...")
            analysis_result = self.data_processor.analyze_margin_trends(processed_data)
            summary_report = self.data_processor.generate_summary_report(processed_data)
            
            # 5. 保存数据
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 保存原始数据
            data_filename = f"margin_data_{start_date}_{end_date}_{timestamp}"
            save_data(processed_data, data_filename, export_format)
            print(f"✅ 数据已保存为 {export_format} 格式")
            
            # 保存分析报告
            report_filename = f"margin_report_{start_date}_{end_date}_{timestamp}.txt"
            report_path = os.path.join("output", report_filename)
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(summary_report)
            print(f"✅ 分析报告已保存: {report_filename}")
            
            # 6. 创建图表
            if create_charts:
                print("正在生成图表...")
                
                # 余额趋势图
                balance_chart = self.visualizer.create_margin_balance_chart(processed_data)
                if balance_chart:
                    print(f"✅ 余额趋势图已生成")
                
                # 占比分析图
                ratio_chart = self.visualizer.create_margin_ratio_chart(processed_data)
                if ratio_chart:
                    print(f"✅ 占比分析图已生成")
                
                # 相关性热力图
                heatmap = self.visualizer.create_correlation_heatmap(processed_data)
                if heatmap:
                    print(f"✅ 相关性热力图已生成")
                
                # 汇总图表
                summary_chart = self.visualizer.create_summary_chart(analysis_result)
                if summary_chart:
                    print(f"✅ 汇总图表已生成")
            
            # 7. 创建交互式仪表板
            if create_dashboard:
                print("正在生成交互式仪表板...")
                dashboard = self.visualizer.create_interactive_dashboard(processed_data)
                if dashboard:
                    print(f"✅ 交互式仪表板已生成: {os.path.basename(dashboard)}")
            
            # 8. 显示分析结果
            print("\n" + "="*60)
            print(summary_report)
            print("="*60)
            
            return True
            
        except Exception as e:
            self.logger.error(f"查询过程中发生错误: {e}")
            print(f"❌ 查询失败: {e}")
            return False
    
    def run_interactive(self):
        """运行交互式模式"""
        print("\n🚀 欢迎使用A股两融交易查询系统")
        print("="*50)
        
        while True:
            try:
                print("\n请选择操作:")
                print("1. 查询两融数据")
                print("2. 查询个股两融明细")
                print("3. 系统设置")
                print("4. 退出")
                
                choice = input("\n请输入选项 (1-4): ").strip()
                
                if choice == '1':
                    self._interactive_margin_query()
                elif choice == '2':
                    self._interactive_stock_query()
                elif choice == '3':
                    self._interactive_settings()
                elif choice == '4':
                    print("👋 感谢使用，再见！")
                    break
                else:
                    print("❌ 无效选项，请重新选择")
                    
            except KeyboardInterrupt:
                print("\n\n👋 程序已退出")
                break
            except Exception as e:
                print(f"❌ 发生错误: {e}")
    
    def _interactive_margin_query(self):
        """交互式两融查询"""
        try:
            print("\n📊 两融数据查询")
            print("-" * 30)
            
            # 输入日期范围
            print("请输入查询日期范围 (格式: YYYYMMDD)")
            
            # 默认日期
            default_end = datetime.now().strftime('%Y%m%d')
            default_start = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            
            start_date = input(f"开始日期 (默认: {default_start}): ").strip()
            if not start_date:
                start_date = default_start
            
            end_date = input(f"结束日期 (默认: {default_end}): ").strip()
            if not end_date:
                end_date = default_end
            
            # 输出选项
            print("\n输出选项:")
            print("1. 仅数据文件")
            print("2. 数据文件 + 图表")
            print("3. 数据文件 + 图表 + 交互式仪表板")
            
            output_choice = input("请选择输出选项 (1-3, 默认: 2): ").strip()
            if not output_choice:
                output_choice = '2'
            
            create_charts = output_choice in ['2', '3']
            create_dashboard = output_choice == '3'
            
            # 导出格式
            format_choice = input("导出格式 (csv/excel/json, 默认: csv): ").strip().lower()
            if format_choice not in ['csv', 'excel', 'json']:
                format_choice = 'csv'
            
            # 执行查询
            print(f"\n🔍 正在查询 {start_date} 至 {end_date} 的两融数据...")
            
            success = self.query_margin_data(
                start_date=start_date,
                end_date=end_date,
                export_format=format_choice,
                create_charts=create_charts,
                create_dashboard=create_dashboard
            )
            
            if success:
                print("\n✅ 查询完成！请查看 output 目录中的结果文件。")
            else:
                print("\n❌ 查询失败，请检查输入参数和网络连接。")
                
        except Exception as e:
            print(f"❌ 查询过程中发生错误: {e}")
    
    def _interactive_stock_query(self):
        """交互式个股查询"""
        print("\n📈 个股两融明细查询")
        print("-" * 30)
        print("此功能正在开发中...")
        input("按回车键返回主菜单...")
    
    def _interactive_settings(self):
        """交互式设置"""
        print("\n⚙️ 系统设置")
        print("-" * 30)
        
        print("当前配置:")
        print(f"默认查询天数: {(datetime.strptime(MARGIN_TRADING_CONFIG['default_end_date'], '%Y%m%d') - datetime.strptime(MARGIN_TRADING_CONFIG['default_start_date'], '%Y%m%d')).days} 天")
        print(f"缓存启用: {'是' if MARGIN_TRADING_CONFIG['cache_enabled'] else '否'}")
        print(f"图表启用: {'是' if MARGIN_TRADING_CONFIG['charts_enabled'] else '否'}")
        
        input("\n按回车键返回主菜单...")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='A股两融交易查询系统')
    parser.add_argument('--start', type=str, help='开始日期 (YYYYMMDD)')
    parser.add_argument('--end', type=str, help='结束日期 (YYYYMMDD)')
    parser.add_argument('--format', choices=['csv', 'excel', 'json'], 
                       default='csv', help='导出格式')
    parser.add_argument('--no-charts', action='store_true', help='不生成图表')
    parser.add_argument('--dashboard', action='store_true', help='生成交互式仪表板')
    parser.add_argument('--interactive', action='store_true', help='运行交互式模式')
    
    args = parser.parse_args()
    
    # 创建应用实例
    app = MarginTradingApp()
    
    # 交互式模式
    if args.interactive or (not args.start and not args.end):
        app.run_interactive()
        return
    
    # 命令行模式
    if not args.start or not args.end:
        # 使用默认日期
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    else:
        start_date = args.start
        end_date = args.end
    
    # 执行查询
    success = app.query_margin_data(
        start_date=start_date,
        end_date=end_date,
        export_format=args.format,
        create_charts=not args.no_charts,
        create_dashboard=args.dashboard
    )
    
    if success:
        print("\n✅ 程序执行完成")
    else:
        print("\n❌ 程序执行失败")
        sys.exit(1)

if __name__ == '__main__':
    main()
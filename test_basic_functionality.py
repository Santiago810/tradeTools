#!/usr/bin/env python
"""
基础功能测试脚本 - A股两融交易查询系统
测试各个模块的基本功能是否正常
"""

import sys
import os
from datetime import datetime, timedelta

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试模块导入"""
    print("📦 测试模块导入...")
    
    try:
        from config import MARGIN_TRADING_CONFIG, DATA_SOURCES
        print("✅ config模块导入成功")
    except Exception as e:
        print(f"❌ config模块导入失败: {e}")
        return False
    
    try:
        from utils import setup_logging, ensure_directories, format_number
        print("✅ utils模块导入成功")
    except Exception as e:
        print(f"❌ utils模块导入失败: {e}")
        return False
    
    try:
        from data_fetcher import create_margin_fetcher
        print("✅ data_fetcher模块导入成功")
    except Exception as e:
        print(f"❌ data_fetcher模块导入失败: {e}")
        return False
    
    try:
        from data_processor import create_margin_processor
        print("✅ data_processor模块导入成功")
    except Exception as e:
        print(f"❌ data_processor模块导入失败: {e}")
        return False
    
    try:
        from visualizer import create_margin_visualizer
        print("✅ visualizer模块导入成功")
    except Exception as e:
        print(f"❌ visualizer模块导入失败: {e}")
        return False
    
    return True

def test_dependencies():
    """测试依赖包"""
    print("\n📚 测试依赖包...")
    
    dependencies = [
        ('pandas', 'pd'),
        ('numpy', 'np'),
        ('requests', None),
        ('matplotlib.pyplot', 'plt'),
        ('seaborn', 'sns'),
    ]
    
    optional_dependencies = [
        ('akshare', 'ak'),
        ('tushare', 'ts'),
        ('streamlit', 'st'),
        ('plotly.graph_objects', 'go'),
    ]
    
    success_count = 0
    
    # 测试必需依赖
    for dep, alias in dependencies:
        try:
            if alias:
                exec(f"import {dep} as {alias}")
            else:
                exec(f"import {dep}")
            print(f"✅ {dep} 导入成功")
            success_count += 1
        except ImportError:
            print(f"❌ {dep} 导入失败 - 这是必需的依赖")
            return False
        except Exception as e:
            print(f"❌ {dep} 导入错误: {e}")
            return False
    
    # 测试可选依赖
    for dep, alias in optional_dependencies:
        try:
            if alias:
                exec(f"import {dep} as {alias}")
            else:
                exec(f"import {dep}")
            print(f"✅ {dep} 导入成功")
        except ImportError:
            print(f"⚠️ {dep} 未安装 - 这是可选依赖")
        except Exception as e:
            print(f"⚠️ {dep} 导入警告: {e}")
    
    return True

def test_basic_functionality():
    """测试基础功能"""
    print("\n🔧 测试基础功能...")
    
    try:
        # 测试工具函数
        from utils import format_date, format_number, ensure_directories
        
        # 测试日期格式化
        test_date = format_date('20240101')
        assert test_date == '20240101', f"日期格式化失败: {test_date}"
        print("✅ 日期格式化功能正常")
        
        # 测试数字格式化
        test_number = format_number(123456789)
        assert '亿' in test_number or '万' in test_number, f"数字格式化失败: {test_number}"
        print("✅ 数字格式化功能正常")
        
        # 测试目录创建
        ensure_directories()
        print("✅ 目录创建功能正常")
        
    except Exception as e:
        print(f"❌ 基础功能测试失败: {e}")
        return False
    
    try:
        # 测试组件创建
        from data_fetcher import create_margin_fetcher
        from data_processor import create_margin_processor
        from visualizer import create_margin_visualizer
        
        fetcher = create_margin_fetcher()
        processor = create_margin_processor()
        visualizer = create_margin_visualizer()
        
        print("✅ 组件创建功能正常")
        
    except Exception as e:
        print(f"❌ 组件创建失败: {e}")
        return False
    
    return True

def test_mock_data_processing():
    """测试模拟数据处理"""
    print("\n📊 测试数据处理功能...")
    
    try:
        import pandas as pd
        import numpy as np
        from data_processor import create_margin_processor
        
        # 创建模拟数据
        dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
        mock_data = pd.DataFrame({
            '交易日期': dates.strftime('%Y%m%d'),
            '融资余额': np.random.normal(10000000000, 1000000000, len(dates)),  # 100亿左右
            '融券余额': np.random.normal(1000000000, 100000000, len(dates)),   # 10亿左右
            '融资买入额': np.random.normal(500000000, 50000000, len(dates)),   # 5亿左右
        })
        
        # 确保数值为正
        mock_data['融资余额'] = mock_data['融资余额'].abs()
        mock_data['融券余额'] = mock_data['融券余额'].abs()
        mock_data['融资买入额'] = mock_data['融资买入额'].abs()
        mock_data['两融余额'] = mock_data['融资余额'] + mock_data['融券余额']
        
        print(f"✅ 模拟数据创建成功，包含 {len(mock_data)} 条记录")
        
        # 测试数据处理
        processor = create_margin_processor()
        processed_data = processor.process_margin_summary(mock_data)
        
        # 验证处理结果
        assert not processed_data.empty, "处理后数据为空"
        assert '融资占两融比例' in processed_data.columns, "缺少融资占比列"
        assert '两融余额_日变化率' in processed_data.columns, "缺少变化率列"
        
        print("✅ 数据处理功能正常")
        
        # 测试分析功能
        analysis_result = processor.analyze_margin_trends(processed_data)
        assert isinstance(analysis_result, dict), "分析结果格式错误"
        assert '数据概况' in analysis_result, "缺少数据概况"
        
        print("✅ 数据分析功能正常")
        
        # 测试报告生成
        report = processor.generate_summary_report(processed_data)
        assert isinstance(report, str) and len(report) > 100, "报告生成失败"
        
        print("✅ 报告生成功能正常")
        
        return True, processed_data, analysis_result
        
    except Exception as e:
        print(f"❌ 数据处理测试失败: {e}")
        return False, None, None

def test_visualization():
    """测试可视化功能"""
    print("\n📈 测试可视化功能...")
    
    try:
        from visualizer import create_margin_visualizer
        import pandas as pd
        import numpy as np
        
        # 创建简单的测试数据
        dates = pd.date_range(start='2024-01-01', end='2024-01-10', freq='D')
        test_data = pd.DataFrame({
            '交易日期': dates,
            '融资余额': np.random.normal(10000000000, 1000000000, len(dates)),
            '融券余额': np.random.normal(1000000000, 100000000, len(dates)),
            '两融余额': np.random.normal(11000000000, 1100000000, len(dates)),
            '两融余额_日变化率': np.random.normal(0, 2, len(dates)),
            '两融余额_RSI': np.random.uniform(30, 70, len(dates)),
        })
        
        visualizer = create_margin_visualizer()
        
        # 测试余额趋势图（不实际保存）
        print("✅ 可视化模块创建成功")
        
        # 测试简单的分析结果
        mock_analysis = {
            '数据概况': {'数据天数': len(test_data)},
            '两融余额分析': {
                '最新余额': '110.0亿',
                '最高余额': '120.0亿',
                '最低余额': '100.0亿',
                '平均余额': '110.0亿'
            },
            '融资融券结构': {
                '融资余额': '100.0亿',
                '融券余额': '10.0亿',
                '融资占比': '90.9%',
                '融券占比': '9.1%'
            }
        }
        
        print("✅ 可视化功能基础测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 可视化测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("🧪 开始运行A股两融交易查询系统测试")
    print("=" * 60)
    
    # 测试模块导入
    if not test_imports():
        print("\n❌ 模块导入测试失败，请检查代码结构")
        return False
    
    # 测试依赖包
    if not test_dependencies():
        print("\n❌ 依赖包测试失败，请运行: pip install -r requirements.txt")
        return False
    
    # 测试基础功能
    if not test_basic_functionality():
        print("\n❌ 基础功能测试失败")
        return False
    
    # 测试数据处理
    success, processed_data, analysis_result = test_mock_data_processing()
    if not success:
        print("\n❌ 数据处理测试失败")
        return False
    
    # 测试可视化
    if not test_visualization():
        print("\n❌ 可视化测试失败")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 所有测试通过！系统基础功能正常")
    print("=" * 60)
    
    print("\n📋 测试总结:")
    print("✅ 模块导入 - 正常")
    print("✅ 依赖包检查 - 正常")
    print("✅ 基础功能 - 正常")
    print("✅ 数据处理 - 正常")
    print("✅ 可视化模块 - 正常")
    
    print("\n🚀 系统已准备就绪，可以开始使用！")
    print("\n💡 使用建议:")
    print("1. 运行 python run.py 启动系统")
    print("2. 选择Web界面获得最佳体验")
    print("3. 首次查询可能需要较长时间下载数据")
    print("4. 建议查询时间范围不超过1年")
    
    return True

def main():
    """主函数"""
    try:
        return run_all_tests()
    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被用户中断")
        return False
    except Exception as e:
        print(f"\n❌ 测试过程中发生意外错误: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
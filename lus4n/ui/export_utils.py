#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - 导出工具模块
用于将可视化图形导出为各种格式
"""

import os
import networkx as nx

# 检查 PIL 是否可用
PIL_AVAILABLE = False
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    pass

# 检查 selenium 是否可用
SELENIUM_AVAILABLE = False
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    pass


def export_graph_to_graphml(graph, nodes, output_path):
    """导出图为 GraphML 格式
    
    参数:
    - graph: networkx 图对象
    - nodes: 要导出的节点集合
    - output_path: 输出文件路径
    
    返回:
    - 成功则返回 True,失败则抛出异常
    """
    # 创建子图
    subgraph = graph.subgraph(nodes)
    
    # 导出为 GraphML
    nx.write_graphml(subgraph, output_path)
    
    return True


def export_html_to_png(html_path, output_path, width=1920, height=1080):
    """使用 Selenium 将 HTML 导出为 PNG
    
    参数:
    - html_path: HTML 文件路径
    - output_path: 输出 PNG 文件路径
    - width: 截图宽度
    - height: 截图高度
    
    返回:
    - 成功则返回 True,失败则抛出异常
    """
    if not SELENIUM_AVAILABLE:
        raise ImportError("需要安装 selenium 库: pip install selenium")
    
    # 配置 Chrome 选项
    options = Options()
    options.add_argument('--headless')  # 无头模式
    options.add_argument('--disable-gpu')
    options.add_argument(f'--window-size={width},{height}')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    try:
        # 创建 WebDriver
        driver = webdriver.Chrome(options=options)
        
        # 加载 HTML 文件
        file_url = f"file:///{os.path.abspath(html_path)}"
        driver.get(file_url)
        
        # 等待页面加载
        import time
        time.sleep(2)
        
        # 截图
        driver.save_screenshot(output_path)
        
        # 关闭浏览器
        driver.quit()
        
        return True
    except Exception as e:
        raise Exception(f"导出 PNG 失败: {str(e)}")


def export_html_to_pdf(html_path, output_path):
    """使用 Selenium 将 HTML 导出为 PDF
    
    参数:
    - html_path: HTML 文件路径
    - output_path: 输出 PDF 文件路径
    
    返回:
    - 成功则返回 True,失败则抛出异常
    """
    if not SELENIUM_AVAILABLE:
        raise ImportError("需要安装 selenium 库: pip install selenium")
    
    # 配置 Chrome 选项
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # 配置打印为 PDF
    options.add_experimental_option('prefs', {
        'printing.print_preview_sticky_settings.appState': '{"recentDestinations":[{"id":"Save as PDF","origin":"local","account":""}],"selectedDestinationId":"Save as PDF","version":2}',
        'savefile.default_directory': os.path.dirname(os.path.abspath(output_path))
    })
    
    try:
        # 创建 WebDriver
        driver = webdriver.Chrome(options=options)
        
        # 加载 HTML 文件
        file_url = f"file:///{os.path.abspath(html_path)}"
        driver.get(file_url)
        
        # 等待页面加载
        import time
        time.sleep(2)
        
        # 打印为 PDF
        result = driver.execute_cdp_cmd("Page.printToPDF", {
            "printBackground": True,
            "landscape": True
        })
        
        # 保存 PDF
        import base64
        with open(output_path, 'wb') as f:
            f.write(base64.b64decode(result['data']))
        
        # 关闭浏览器
        driver.quit()
        
        return True
    except Exception as e:
        raise Exception(f"导出 PDF 失败: {str(e)}")


def is_export_available(format_type):
    """检查指定格式的导出功能是否可用
    
    参数:
    - format_type: 格式类型 ('png', 'pdf', 'graphml')
    
    返回:
    - True 表示可用, False 表示不可用
    """
    if format_type.lower() == 'graphml':
        return True  # GraphML 只依赖 networkx,总是可用
    elif format_type.lower() in ['png', 'pdf']:
        return SELENIUM_AVAILABLE
    else:
        return False

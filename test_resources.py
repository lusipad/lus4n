#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试静态资源文件和自定义 Network 类
"""

import os
import tempfile
import webbrowser
from lus4n.ui.custom_network import CustomNetwork

# 检查静态资源文件
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lus4n', 'ui', 'static')
print(f'静态资源文件检查：')
print(f'vis.min.js 存在：{os.path.exists(os.path.join(static_dir, "vis.min.js"))}')
print(f'vis.min.css 存在：{os.path.exists(os.path.join(static_dir, "vis.min.css"))}')
print(f'template.html 存在：{os.path.exists(os.path.join(static_dir, "template.html"))}')
print(f'fallback_template.html 存在：{os.path.exists(os.path.join(static_dir, "fallback_template.html"))}')

# 测试自定义 Network 类
print('\n测试自定义 Network 类：')
temp_dir = tempfile.gettempdir()
temp_html = os.path.join(temp_dir, 'test_network.html')

# 创建一个简单的网络图
net = CustomNetwork(notebook=True)
net.add_node(1, label="节点 1")
net.add_node(2, label="节点 2")
net.add_edge(1, 2)

# 设置模板并生成 HTML
template_path = os.path.join(static_dir, 'template.html')
if os.path.exists(template_path):
    print(f'使用模板：{template_path}')
    net.set_template(template_path)

# 保存 HTML 文件
net.show(temp_html)
print(f'生成的 HTML 文件：{temp_html}')

# 检查生成的 HTML 文件中是否包含本地资源引用
with open(temp_html, 'r', encoding='utf-8') as f:
    content = f.read()
    has_cdn = 'cdnjs.cloudflare.com' in content
    has_local_js = 'src="vis.min.js"' in content
    has_local_css = 'href="vis.min.css"' in content

print(f'HTML 文件中包含 CDN 引用：{has_cdn}')
print(f'HTML 文件中包含本地 JS 引用：{has_local_js}')
print(f'HTML 文件中包含本地 CSS 引用：{has_local_css}')

if not has_cdn and has_local_js and has_local_css:
    print('\n测试成功：自定义 Network 类正确使用了本地资源！')
else:
    print('\n测试失败：自定义 Network 类未正确使用本地资源。')

# 打开生成的 HTML 文件
print(f'\n是否打开生成的 HTML 文件？(y/n)')
choice = input().strip().lower()
if choice == 'y':
    webbrowser.open_new_tab(f'file://{temp_html}')
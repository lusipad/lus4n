#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试模板文件路径
用于诊断打包后找不到 template.html 的问题
"""

import os
import sys
import site
import tempfile

# 打印基本环境信息
print("\n===== 环境信息 =====")
print(f"Python 版本：{sys.version}")
print(f"运行路径：{os.path.abspath('.')}")
print(f"临时目录：{tempfile.gettempdir()}")

# 检查可能的模板文件位置
print("\n===== 检查模板文件位置 =====")

# 1. 检查当前目录下的静态资源
local_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lus4n', 'ui', 'static')
print(f"1. 当前目录静态资源：{local_static_dir}")
print(f"   - 目录存在：{os.path.exists(local_static_dir)}")
if os.path.exists(local_static_dir):
    print(f"   - template.html: {os.path.exists(os.path.join(local_static_dir, 'template.html'))}")
    print(f"   - fallback_template.html: {os.path.exists(os.path.join(local_static_dir, 'fallback_template.html'))}")
    print(f"   - vis.min.js: {os.path.exists(os.path.join(local_static_dir, 'vis.min.js'))}")
    print(f"   - vis.min.css: {os.path.exists(os.path.join(local_static_dir, 'vis.min.css'))}")

# 2. 检查 pyvis 包中的模板
pyvis_template_paths = []

# 尝试导入 pyvis 并获取其路径
try:
    import pyvis
    pyvis_dir = os.path.dirname(pyvis.__file__)
    pyvis_template_dir = os.path.join(pyvis_dir, 'templates')
    pyvis_template_paths.append(pyvis_template_dir)
    print(f"\n2. pyvis 包路径：{pyvis_dir}")
    print(f"   - 模板目录存在：{os.path.exists(pyvis_template_dir)}")
    if os.path.exists(pyvis_template_dir):
        print(f"   - template.html: {os.path.exists(os.path.join(pyvis_template_dir, 'template.html'))}")
except ImportError:
    print("\n2. 无法导入 pyvis 包")

# 3. 检查 site-packages 中的 pyvis
for site_path in site.getsitepackages():
    pyvis_site_dir = os.path.join(site_path, 'pyvis')
    if os.path.exists(pyvis_site_dir):
        pyvis_site_template_dir = os.path.join(pyvis_site_dir, 'templates')
        pyvis_template_paths.append(pyvis_site_template_dir)
        print(f"\n3. site-packages 中的 pyvis: {pyvis_site_dir}")
        print(f"   - 模板目录存在：{os.path.exists(pyvis_site_template_dir)}")
        if os.path.exists(pyvis_site_template_dir):
            print(f"   - template.html: {os.path.exists(os.path.join(pyvis_site_template_dir, 'template.html'))}")

# 4. 检查打包后可能的路径
if getattr(sys, 'frozen', False):
    # 运行在打包环境中
    print("\n4. 检测到打包环境")
    base_dir = os.path.dirname(sys.executable)
    possible_paths = [
        os.path.join(base_dir, 'pyvis', 'templates'),
        os.path.join(base_dir, 'lus4n', 'ui', 'static'),
        os.path.join(os.path.dirname(sys.executable), 'pyvis', 'templates'),
        os.path.join(os.path.dirname(sys.executable), 'lus4n', 'ui', 'static')
    ]
    
    for path in possible_paths:
        print(f"   - 检查路径：{path}")
        print(f"     - 目录存在：{os.path.exists(path)}")
        if os.path.exists(path):
            print(f"     - template.html: {os.path.exists(os.path.join(path, 'template.html'))}")
            print(f"     - fallback_template.html: {os.path.exists(os.path.join(path, 'fallback_template.html'))}")

# 5. 检查备份目录
backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backup_static')
print(f"\n5. 备份目录：{backup_dir}")
print(f"   - 目录存在：{os.path.exists(backup_dir)}")
if os.path.exists(backup_dir):
    print(f"   - template.html: {os.path.exists(os.path.join(backup_dir, 'template.html'))}")
    print(f"   - fallback_template.html: {os.path.exists(os.path.join(backup_dir, 'fallback_template.html'))}")

print("\n===== 测试完成 =====")
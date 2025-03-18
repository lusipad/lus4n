#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - 自定义网络图类
用于覆盖 pyvis 库中的默认行为，确保正确使用本地静态资源
"""

import os
import re
from pyvis.network import Network as PyvisNetwork

class CustomNetwork(PyvisNetwork):
    """
    自定义网络图类，继承自 pyvis.network.Network
    主要用于覆盖默认的 HTML 生成行为，确保使用本地静态资源
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_local_resources = True
    
    def show(self, name="", local=True):
        """
        覆盖原始 show 方法，确保使用本地资源
        
        参数:
        - name: 输出 HTML 文件的路径
        - local: 是否使用本地资源（默认为 True）
        """
        # 调用原始 show 方法生成 HTML 文件
        super().show(name)
        
        # 如果需要使用本地资源，修改生成的 HTML 文件
        if local and self.use_local_resources and name:
            self._replace_cdn_with_local(name)
    
    def _replace_cdn_with_local(self, html_path):
        """
        将 HTML 文件中的 CDN 引用替换为本地资源引用
        
        参数:
        - html_path: HTML 文件路径
        """
        try:
            # 读取 HTML 文件内容
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换 CDN 引用为本地资源引用
            # 替换 JavaScript 引用
            content = re.sub(
                r'<script[^>]*src=["\']https?://[^"\']*/vis[^"\']*.js["\'][^>]*></script>',
                '<script type="text/javascript" src="vis.min.js"></script>',
                content
            )
            
            # 替换 CSS 引用
            content = re.sub(
                r'<link[^>]*href=["\']https?://[^"\']*/vis[^"\']*.css["\'][^>]*>',
                '<link href="vis.min.css" rel="stylesheet" type="text/css" />',
                content
            )
            
            # 写回 HTML 文件
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return True
        except Exception as e:
            print(f"替换 CDN 引用失败：{e}")
            return False
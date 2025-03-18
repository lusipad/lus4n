#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - 图形可视化模块
用于处理调用图的可视化展示
"""

import os
import uuid
import shutil
import webbrowser
import tempfile
from pyvis.network import Network as PyvisNetwork
from .custom_network import CustomNetwork


class GraphVisualizer:
    """图形可视化类，负责将调用图渲染为可视化网页"""
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
    
    def create_network(self, height="800px", width="100%"):
        """创建一个新的网络图实例"""
        return CustomNetwork(notebook=True, height=height, width=width)
    
    def apply_layout(self, net, layout_option):
        """应用指定的布局设置到网络图"""
        if layout_option == "分层布局 (上到下)":
            net.set_options("""
            {
              "layout": {
                "hierarchical": {
                  "enabled": true,
                  "direction": "UD",
                  "sortMethod": "directed",
                  "nodeSpacing": 150,
                  "levelSeparation": 150
                }
              }
            }
            """)
        elif layout_option == "分层布局 (左到右)":
            net.set_options("""
            {
              "layout": {
                "hierarchical": {
                  "enabled": true,
                  "direction": "LR",
                  "sortMethod": "directed",
                  "nodeSpacing": 150,
                  "levelSeparation": 150
                }
              }
            }
            """)
        elif layout_option == "圆形布局":
            net.set_options("""
            {
              "layout": {
                "circular": {
                  "enabled": true
                }
              }
            }
            """)
        elif layout_option == "放射状布局":
            net.set_options("""
            {
              "layout": {
                "improvedLayout": true
              }
            }
            """)
        return net
    
    def _copy_static_files(self, target_dir):
        """
        复制静态资源文件到目标目录，用于离线环境
        """
        # 获取静态资源目录路径
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
        
        # 复制 vis.js 和 vis.css 文件到目标目录
        try:
            shutil.copy(os.path.join(static_dir, 'vis.min.js'), target_dir)
            shutil.copy(os.path.join(static_dir, 'vis.min.css'), target_dir)
            return True
        except Exception as e:
            print(f"复制静态资源文件失败：{e}")
            return False
            
    def _check_static_resources(self):
        """
        检查静态资源文件是否可用
        """
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
        vis_js_path = os.path.join(static_dir, 'vis.min.js')
        vis_css_path = os.path.join(static_dir, 'vis.min.css')
        
        return os.path.exists(vis_js_path) and os.path.exists(vis_css_path)
    
    def render_graph(self, graph, nodes, query_node=None, 
                    show_physics=True, size_by_importance=True, 
                    layout="力导向布局"):
        """
        渲染图形
        
        参数:
        - graph: networkx 图对象
        - nodes: 要显示的节点集合
        - query_node: 查询节点（如果有）
        - show_physics: 是否显示物理引擎效果
        - size_by_importance: 是否根据重要性调整节点大小
        - layout: 布局方式
        
        返回:
        - 生成的 HTML 文件路径
        - 渲染后的网络图对象
        """
        # 创建子图
        sg = graph.subgraph(nodes)
        
        # 生成可视化
        net = self.create_network()
        
        # 应用布局
        self.apply_layout(net, layout)
        
        # 设置物理引擎
        if not show_physics:
            # 使用 options 直接设置物理引擎状态，避免使用 toggle_physics 可能导致的错误
            physics_options = """
            {
              "physics": {
                "enabled": false
              }
            }
            """
            net.set_options(physics_options)
        
        # 添加查询节点
        if query_node and query_node in nodes:
            net.add_node(query_node, color="#FF6D3F", size=25, title=f"查询：{query_node}")
        
        # 添加其他节点
        for node in sg.nodes():
            if node == query_node:
                continue
                
            # 设置节点属性
            if size_by_importance:
                # 计算节点度数作为重要性
                importance = sg.in_degree(node) + sg.out_degree(node)
                size = min(10 + importance * 2, 30)  # 限制最大尺寸
            else:
                size = 15  # 默认大小
                
            # 设置节点颜色
            if "role" in graph.nodes[node] and graph.nodes[node]["role"] == "file":
                color = "#6BAED6"  # 蓝色表示文件
            else:
                # 函数节点根据入度 (被调用次数) 设置颜色深浅
                in_degree = sg.in_degree(node)
                if in_degree > 10:
                    color = "#2C7FB8"  # 深蓝色表示重要函数
                elif in_degree > 5:
                    color = "#7FCDBB"  # 中等蓝绿色
                else:
                    color = "#C7E9B4"  # 浅绿色
            
            net.add_node(node, size=size, color=color, title=f"{node} (被调用：{sg.in_degree(node)}次)")
        
        # 添加边
        for edge in sg.edges():
            net.add_edge(edge[0], edge[1], arrows={'to': {'enabled': True, 'type': 'arrow'}})
        
        # 创建临时目录用于存放 HTML 和静态资源
        temp_uuid = str(uuid.uuid4())
        temp_output_dir = os.path.join(self.temp_dir, f"lus4n_{temp_uuid}")
        os.makedirs(temp_output_dir, exist_ok=True)
        
        # 检查静态资源是否可用
        static_resources_available = self._check_static_resources()
        
        # 复制静态资源文件到临时目录
        copy_success = False
        if static_resources_available:
            copy_success = self._copy_static_files(temp_output_dir)
        
        # 获取模板路径
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'template.html')
        fallback_template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'fallback_template.html')
        
        # 保存到临时文件
        show_path = os.path.join(temp_output_dir, "network.html")
        
        # 根据静态资源可用性选择模板
        if static_resources_available and copy_success and os.path.exists(template_path):
            net.set_template(template_path)
        elif os.path.exists(fallback_template_path):
            # 使用备用模板（不依赖外部静态资源）
            net.set_template(fallback_template_path)
            
        net.show(show_path)
        
        return show_path, net
        
    def display_graph(self, show_path):
        """在浏览器中显示图形"""
        webbrowser.open_new_tab(f"file://{show_path}")
        return show_path

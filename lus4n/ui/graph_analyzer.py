#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - 图分析模块
用于分析调用图数据和查询函数关系
"""

import os
import networkx as nx
from joblib import load


class GraphAnalyzer:
    """图分析类，负责分析调用图数据"""
    
    def __init__(self):
        self.graph = None
        self.storage_path = None
        self.whole_call_graph = None
    
    def load_graph(self, storage_path):
        """从存储文件加载图数据"""
        if not os.path.exists(storage_path):
            raise FileNotFoundError(f"存储文件不存在: {storage_path}")
        
        self.storage_path = storage_path
        loaded_data = load(storage_path)
        
        # 检查加载的数据类型，确保返回有效的 networkx 图对象
        if isinstance(loaded_data, dict):
            # ScanThread保存的数据结构是一个包含三个键的字典
            if 'whole_call_network' in loaded_data:
                self.graph = loaded_data['whole_call_network']
                self.whole_call_graph = loaded_data.get('whole_call_graph', {})
            else:
                # 如果没有找到预期的键，尝试把整个字典作为图的数据
                self.graph = nx.DiGraph()
                self.whole_call_graph = loaded_data
                
                # 从字典构建图结构
                for file_path, file_data in loaded_data.items():
                    if isinstance(file_data, dict):
                        self.graph.add_node(file_path, role='file')
                        # 处理文件中的函数调用关系
                        self._build_graph_from_call_data(file_path, file_data)
        else:
            # 假设已经是 networkx 图对象
            self.graph = loaded_data
            
        return self.graph
    
    def _build_graph_from_call_data(self, file_path, call_data):
        """从调用数据构建图结构"""
        if not isinstance(call_data, dict):
            return
            
        package_name = os.path.basename(file_path).replace(".lua", "")
        
        for tmp_name, called_list in call_data.items():
            # 处理全局调用
            if tmp_name == "[G]":
                import xxhash
                default_main = f"{package_name}.main.{xxhash.xxh32(file_path).hexdigest()}"
                self.graph.add_edge(file_path, default_main, action='export')
                for called in called_list:
                    self.graph.add_edge(default_main, called, action="call")
                    
            # 处理导出函数
            elif tmp_name.startswith("[X]"):
                exported = tmp_name.replace("[X]", "")
                sub_names = exported.split('.')
                if len(sub_names) > 1:
                    father = sub_names[0]
                    left = exported[len(father):]
                    # 假设没有require数据，简单处理
                    _exported = f"{package_name}{left}"
                else:
                    _exported = exported
                self.graph.add_edge(file_path, _exported, action="export")
                for called in called_list:
                    self.graph.add_edge(_exported, called, action='call')
                    
            # 处理局部函数
            elif tmp_name.startswith("[L]"):
                defined = tmp_name.replace("[L]", "")
                self.graph.add_edge(file_path, defined, action="define")
                for called in called_list:
                    self.graph.add_edge(defined, called, action='call')
    
    def get_function_entries(self):
        """获取所有函数入口点（没有被其他函数调用的函数）"""
        if not self.graph:
            raise ValueError("请先加载图数据")
        
        # 找出没有入边的节点（排除文件节点）
        entries = []
        for node in self.graph.nodes():
            # 跳过文件节点
            if 'role' in self.graph.nodes[node] and self.graph.nodes[node]['role'] == 'file':
                continue
                
            # 检查是否有调用该函数的其他函数（入边）
            has_incoming_calls = False
            for _, _, data in self.graph.in_edges(node, data=True):
                if data.get('action') == 'call':
                    has_incoming_calls = True
                    break
                    
            if not has_incoming_calls:
                entries.append(node)
                
        return entries
    
    def get_function_ancestors(self, function_name):
        """获取函数的所有祖先节点（调用该函数的所有函数）"""
        if not self.graph:
            raise ValueError("请先加载图数据")
        
        if function_name not in self.graph.nodes:
            raise ValueError(f"函数不存在: {function_name}")
        
        # 获取所有祖先节点
        ancestors = nx.ancestors(self.graph, function_name)
        if function_name not in ancestors:
            ancestors.add(function_name)
            
        return ancestors
    
    def filter_nodes_by_type(self, nodes, show_files=True):
        """按类型筛选节点"""
        if not self.graph:
            raise ValueError("请先加载图数据")
        
        # 检查是否显示文件节点
        if not show_files:
            return {n for n in nodes if not (
                "role" in self.graph.nodes[n] and self.graph.nodes[n]["role"] == "file")}
        return nodes
    
    def filter_nodes_by_importance(self, nodes, max_nodes, important_nodes=None):
        """根据重要性筛选节点，保留最重要的节点"""
        if not self.graph:
            raise ValueError("请先加载图数据")
        
        if not important_nodes:
            important_nodes = set()
            
        if len(nodes) <= max_nodes:
            return nodes
            
        # 优先保留重要节点
        filtered_nodes = set(important_nodes)
        
        # 剩余节点按重要性（度数）排序
        other_nodes = nodes - filtered_nodes
        node_importance = {
            n: self.graph.in_degree(n) + self.graph.out_degree(n) 
            for n in other_nodes
        }
        sorted_nodes = sorted(
            other_nodes, 
            key=lambda n: node_importance.get(n, 0), 
            reverse=True
        )
        
        # 添加最重要的节点，直到达到最大节点数
        filtered_nodes.update(sorted_nodes[:max_nodes-len(filtered_nodes)])
        
        return filtered_nodes
    
    def separate_nodes_by_type(self, nodes):
        """将节点分为文件节点和函数节点"""
        if not self.graph:
            raise ValueError("请先加载图数据")
            
        file_nodes = []
        function_nodes = []
        
        for node in nodes:
            if "role" in self.graph.nodes[node] and self.graph.nodes[node]["role"] == "file":
                file_nodes.append(node)
            else:
                function_nodes.append(node)
                
        return function_nodes, file_nodes
    
    def get_all_function_entries(self):
        """获取所有函数入口点（被调用过的函数）及其被调用次数"""
        if not self.graph:
            raise ValueError("请先加载图数据")
            
        # 统计所有节点的入度（被调用次数）
        function_entries = {}
        
        for node in self.graph.nodes():
            # 跳过文件节点
            if "role" in self.graph.nodes[node] and self.graph.nodes[node]["role"] == "file":
                continue
            
            # 计算入度（被调用次数）
            in_degree = self.graph.in_degree(node)
            if in_degree > 0:  # 只统计被调用过的函数
                function_entries[node] = in_degree
        
        # 按被调用次数排序
        return sorted(function_entries.items(), key=lambda x: x[1], reverse=True)
        
    def get_all_nodes(self):
        """获取图中的所有节点"""
        if not self.graph:
            raise ValueError("请先加载图数据")
            
        return set(self.graph.nodes())

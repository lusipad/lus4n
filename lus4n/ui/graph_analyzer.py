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
    
    def load_graph(self, storage_path):
        """从存储文件加载图数据"""
        if not os.path.exists(storage_path):
            raise FileNotFoundError(f"存储文件不存在: {storage_path}")
        
        self.storage_path = storage_path
        self.graph = load(storage_path)
        return self.graph
    
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

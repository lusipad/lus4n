#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - 查询选项卡模块
"""

import os
import uuid
import webbrowser
import tempfile
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QLineEdit, QPushButton, QTextEdit, QFileDialog, 
    QComboBox, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QStackedWidget, QApplication
)
from PySide6.QtCore import Qt
from joblib import load
import networkx as nx
from pyvis.network import Network


class QueryTab(QWidget):
    """查询选项卡类"""
    
    def __init__(self, parent=None, status_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.status_callback = status_callback
        self.temp_dir = tempfile.gettempdir()
        
        self.initUI()
    
    def initUI(self):
        """初始化查询选项卡UI。"""
        layout = QVBoxLayout(self)
        
        # 存储文件选择区域
        query_storage_group = QGroupBox("存储文件")
        query_storage_layout = QHBoxLayout(query_storage_group)
        self.query_storage_input = QLineEdit()
        self.query_storage_input.setPlaceholderText("选择调用图数据存储文件路径")
        query_storage_browse_btn = QPushButton("浏览...")
        query_storage_browse_btn.clicked.connect(self.browse_query_storage)
        query_storage_layout.addWidget(self.query_storage_input)
        query_storage_layout.addWidget(query_storage_browse_btn)
        layout.addWidget(query_storage_group)
        
        # 函数查询区域
        function_group = QGroupBox("函数查询")
        function_layout = QHBoxLayout(function_group)
        self.function_input = QLineEdit()
        self.function_input.setPlaceholderText("输入要查询的函数名（例如：os.execute）")
        query_btn = QPushButton("查询")
        query_btn.setObjectName("primaryButton")
        query_btn.clicked.connect(self.query_function)
        
        # 添加显示所有函数入口按钮
        list_all_btn = QPushButton("显示所有函数入口")
        list_all_btn.clicked.connect(self.list_all_function_entries)
        
        function_layout.addWidget(self.function_input)
        function_layout.addWidget(query_btn)
        function_layout.addWidget(list_all_btn)
        layout.addWidget(function_group)
        
        # 最近查询记录
        recent_group = QGroupBox("最近查询")
        recent_layout = QVBoxLayout(recent_group)
        self.recent_combo = QComboBox()
        self.recent_combo.setEditable(False)
        self.recent_combo.currentTextChanged.connect(self.on_recent_selected)
        recent_layout.addWidget(self.recent_combo)
        layout.addWidget(recent_group)
        
        # 查询结果区域 - 使用堆叠部件来切换不同的结果视图
        self.result_stack = QStackedWidget()
        
        # 普通文本结果视图
        result_text_widget = QWidget()
        result_text_layout = QVBoxLayout(result_text_widget)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_text_layout.addWidget(self.result_text)
        
        # 表格结果视图（用于显示所有函数入口）
        result_table_widget = QWidget()
        result_table_layout = QVBoxLayout(result_table_widget)
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(2)
        self.result_table.setHorizontalHeaderLabels(["函数入口", "被调用次数"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.result_table.doubleClicked.connect(self.on_function_entry_clicked)
        result_table_layout.addWidget(self.result_table)
        
        # 添加视图到堆叠部件
        self.result_stack.addWidget(result_text_widget)
        self.result_stack.addWidget(result_table_widget)
        
        # 添加到布局
        result_group = QGroupBox("查询结果")
        result_layout = QVBoxLayout(result_group)
        result_layout.addWidget(self.result_stack)
        layout.addWidget(result_group)
    
    def browse_query_storage(self):
        """浏览并选择查询存储文件路径"""
        path, _ = QFileDialog.getOpenFileName(self, "选择存储文件路径", "", "Joblib Files (*.jb)")
        if path:
            self.query_storage_input.setText(path)
    
    def update_status(self, message):
        """更新状态栏消息"""
        if self.status_callback:
            self.status_callback(message)
    
    def on_recent_selected(self, text):
        """从最近查询中选择一个"""
        if text:
            self.function_input.setText(text)
    
    def add_recent_query(self, query):
        """添加一个查询到最近查询列表"""
        # 检查是否已存在
        found = self.recent_combo.findText(query)
        if found != -1:
            self.recent_combo.removeItem(found)
        
        # 添加到顶部
        self.recent_combo.insertItem(0, query)
        self.recent_combo.setCurrentIndex(0)
        
        # 限制最大数量为 10
        while self.recent_combo.count() > 10:
            self.recent_combo.removeItem(self.recent_combo.count() - 1)
        
        # 通知主窗口保存设置
        if hasattr(self.parent, 'save_settings'):
            self.parent.save_settings()
    
    def query_function(self):
        """查询函数调用关系"""
        storage = self.query_storage_input.text()
        if not storage or not os.path.exists(storage):
            QMessageBox.warning(self, "文件错误", "请选择有效的存储文件")
            return
        
        query = self.function_input.text()
        if not query:
            QMessageBox.warning(self, "查询错误", "请输入要查询的函数名")
            return
        
        try:
            self.update_status(f"正在查询 {query}...")
            self.result_text.clear()
            
            # 切换到文本视图
            self.result_stack.setCurrentIndex(0)
            
            # 加载图
            g = load(storage)
            
            if query in g.nodes:
                # 记录查询历史
                self.add_recent_query(query)
                
                # 查找所有祖先节点
                nodes = nx.ancestors(g, query)
                file_node_list = []
                func_node_list = []
                
                for node in nodes:
                    if "role" in g.nodes[node] and g.nodes[node]["role"] == "file":
                        file_node_list.append(node)
                    else:
                        func_node_list.append(node)
                
                if query not in nodes:
                    nodes.add(query)
                
                # 创建子图
                sg = g.subgraph(nodes)
                
                # 生成可视化
                net = Network(notebook=True)
                net.add_node(query)
                net.from_nx(sg)
                
                # 保存并显示
                show_path = os.path.join(self.temp_dir, f"{uuid.uuid4()}.html")
                net.show(show_path)
                
                # 结果信息
                self.result_text.append(f"查询函数：{query}")
                self.result_text.append(f"相关函数数量：{len(func_node_list)}")
                self.result_text.append(f"相关文件数量：{len(file_node_list)}")
                self.result_text.append("\n--- 相关函数 ---")
                for func in func_node_list:
                    self.result_text.append(func)
                
                self.result_text.append("\n--- 相关文件 ---")
                for file in file_node_list:
                    self.result_text.append(file)
                
                # 打开浏览器显示
                webbrowser.open_new_tab(f"file://{show_path}")
                self.update_status(f"已显示 {query} 的调用关系")
            else:
                self.result_text.append(f"未找到节点：{query}")
                self.update_status(f"未找到节点：{query}")
        
        except Exception as e:
            self.result_text.append(f"查询出错：{str(e)}")
            self.update_status("查询出错")
            QMessageBox.critical(self, "查询错误", f"查询过程中发生错误：{str(e)}")
    
    def get_recent_queries(self):
        """获取最近的查询列表"""
        return [self.recent_combo.itemText(i) for i in range(self.recent_combo.count())]
    
    def set_recent_queries(self, queries):
        """设置最近的查询列表"""
        self.recent_combo.clear()
        if queries:
            self.recent_combo.addItems(queries)
    
    def get_storage_path(self):
        """获取当前存储路径"""
        return self.query_storage_input.text()
    
    def set_storage_path(self, path):
        """设置存储路径"""
        self.query_storage_input.setText(path)
    
    def on_function_entry_clicked(self, index):
        """当用户双击函数入口时，自动查询该函数"""
        function_name = self.result_table.item(index.row(), 0).text()
        self.function_input.setText(function_name)
        self.query_function()
    
    def list_all_function_entries(self):
        """分析并显示所有函数入口，按被调用次数排序"""
        storage = self.query_storage_input.text()
        if not storage or not os.path.exists(storage):
            QMessageBox.warning(self, "文件错误", "请选择有效的存储文件")
            return
        
        try:
            self.update_status("正在分析所有函数入口...")
            
            # 加载图
            g = load(storage)
            
            # 统计所有节点的入度（被调用次数）
            function_entries = {}
            
            for node in g.nodes():
                # 跳过文件节点
                if "role" in g.nodes[node] and g.nodes[node]["role"] == "file":
                    continue
                
                # 计算入度（被调用次数）
                in_degree = g.in_degree(node)
                if in_degree > 0:  # 只统计被调用过的函数
                    function_entries[node] = in_degree
            
            # 按被调用次数排序
            sorted_entries = sorted(function_entries.items(), key=lambda x: x[1], reverse=True)
            
            # 显示到表格
            self.result_table.setRowCount(len(sorted_entries))
            for i, (func, count) in enumerate(sorted_entries):
                self.result_table.setItem(i, 0, QTableWidgetItem(func))
                self.result_table.setItem(i, 1, QTableWidgetItem(str(count)))
            
            # 切换到表格视图
            self.result_stack.setCurrentIndex(1)
            
            self.update_status(f"发现 {len(sorted_entries)} 个函数入口")
        
        except Exception as e:
            self.update_status("分析出错")
            QMessageBox.critical(self, "分析错误", f"分析函数入口时发生错误：{str(e)}")

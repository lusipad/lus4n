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
    QHeaderView, QSplitter, QStackedWidget, QApplication,
    QLabel, QSlider, QCheckBox, QRadioButton, QButtonGroup
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
        
        # 可视化设置区域
        visual_group = QGroupBox("可视化设置")
        visual_layout = QVBoxLayout(visual_group)
        
        # 布局选择
        layout_selection_layout = QHBoxLayout()
        layout_label = QLabel("布局方式:")
        layout_label.setStyleSheet("QLabel { color: black; }")
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["力导向布局", "分层布局(上到下)", "分层布局(左到右)", "圆形布局", "放射状布局"])
        layout_selection_layout.addWidget(layout_label)
        layout_selection_layout.addWidget(self.layout_combo)
        visual_layout.addLayout(layout_selection_layout)
        
        # 节点筛选
        filter_layout = QHBoxLayout()
        self.show_files_checkbox = QCheckBox("显示文件节点")
        self.show_files_checkbox.setChecked(True)
        self.show_files_checkbox.setStyleSheet("QCheckBox { color: black; }")
        self.max_nodes_label = QLabel("最大显示节点数:")
        self.max_nodes_label.setStyleSheet("QLabel { color: black; }")
        self.max_nodes_slider = QSlider(Qt.Horizontal)
        self.max_nodes_slider.setMinimum(10)
        self.max_nodes_slider.setMaximum(200)
        self.max_nodes_slider.setValue(100)
        self.max_nodes_slider.setTickPosition(QSlider.TicksBelow)
        self.max_nodes_slider.setTickInterval(10)
        self.max_nodes_value = QLabel("100")
        self.max_nodes_value.setStyleSheet("QLabel { color: black; }")
        self.max_nodes_slider.valueChanged.connect(lambda v: self.max_nodes_value.setText(str(v)))
        
        filter_layout.addWidget(self.show_files_checkbox)
        filter_layout.addWidget(self.max_nodes_label)
        filter_layout.addWidget(self.max_nodes_slider)
        filter_layout.addWidget(self.max_nodes_value)
        visual_layout.addLayout(filter_layout)
        
        # 高级选项
        advanced_layout = QHBoxLayout()
        self.physics_checkbox = QCheckBox("启用物理引擎")
        self.physics_checkbox.setChecked(True)
        self.physics_checkbox.setStyleSheet("QCheckBox { color: black; }")
        self.node_size_checkbox = QCheckBox("根据重要性调整节点大小")
        self.node_size_checkbox.setChecked(True)
        self.node_size_checkbox.setStyleSheet("QCheckBox { color: black; }")
        advanced_layout.addWidget(self.physics_checkbox)
        advanced_layout.addWidget(self.node_size_checkbox)
        visual_layout.addLayout(advanced_layout)
        
        layout.addWidget(visual_group)
        
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
                
                # 应用节点筛选
                filtered_nodes = set()
                
                # 检查是否显示文件节点
                if not self.show_files_checkbox.isChecked():
                    nodes = {n for n in nodes if not (
                        "role" in g.nodes[n] and g.nodes[n]["role"] == "file")}
                
                # 限制最大节点数
                max_nodes = self.max_nodes_slider.value()
                if len(nodes) > max_nodes:
                    # 优先保留查询节点和重要节点
                    important_nodes = {query}
                    
                    # 按节点的度数(重要性)排序并取前N个
                    other_nodes = nodes - important_nodes
                    node_importance = {
                        n: g.in_degree(n) + g.out_degree(n) 
                        for n in other_nodes
                    }
                    sorted_nodes = sorted(
                        other_nodes, 
                        key=lambda n: node_importance.get(n, 0), 
                        reverse=True
                    )
                    filtered_nodes = important_nodes | set(sorted_nodes[:max_nodes-len(important_nodes)])
                else:
                    filtered_nodes = nodes
                
                # 创建子图
                sg = g.subgraph(filtered_nodes)
                
                # 生成可视化
                net = Network(notebook=True, height="800px", width="100%")
                
                # 设置布局
                layout_option = self.layout_combo.currentText()
                if layout_option == "分层布局(上到下)":
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
                elif layout_option == "分层布局(左到右)":
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
                
                # 设置物理引擎
                if not self.physics_checkbox.isChecked():
                    net.toggle_physics(False)
                
                # 添加节点并调整大小
                net.add_node(query, color="#FF6D3F", size=25, title=f"查询: {query}")
                
                # 根据节点重要性调整大小
                if self.node_size_checkbox.isChecked():
                    for node in sg.nodes():
                        if node != query:
                            # 计算节点度数作为重要性
                            importance = sg.in_degree(node) + sg.out_degree(node)
                            size = min(10 + importance * 2, 30)  # 限制最大尺寸
                            
                            # 设置节点颜色
                            if "role" in g.nodes[node] and g.nodes[node]["role"] == "file":
                                color = "#6BAED6"  # 蓝色表示文件
                            else:
                                # 函数节点根据入度(被调用次数)设置颜色深浅
                                in_degree = sg.in_degree(node)
                                if in_degree > 10:
                                    color = "#2C7FB8"  # 深蓝色表示重要函数
                                elif in_degree > 5:
                                    color = "#7FCDBB"  # 中等蓝绿色
                                else:
                                    color = "#C7E9B4"  # 浅绿色
                            
                            net.add_node(node, size=size, color=color, title=f"{node} (被调用: {sg.in_degree(node)})")
                
                # 从networkx导入边
                for edge in sg.edges():
                    net.add_edge(edge[0], edge[1])
                
                # 保存并显示
                show_path = os.path.join(self.temp_dir, f"{uuid.uuid4()}.html")
                net.show(show_path)
                
                # 结果信息
                self.result_text.append(f"查询函数：{query}")
                self.result_text.append(f"相关函数数量：{len(func_node_list)}")
                self.result_text.append(f"相关文件数量：{len(file_node_list)}")
                self.result_text.append(f"显示节点数量：{len(filtered_nodes)}/{len(nodes)}")
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

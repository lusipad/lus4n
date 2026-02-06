#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - UI组件模块
包含可复用的UI组件
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGroupBox, QComboBox, QLineEdit, QSlider, QCheckBox,
    QSlider, QFileDialog, QCompleter
)
from PySide6.QtCore import Qt, QStringListModel


class StorageSelector:
    """存储文件选择器组件"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.storage_input = None
        self.group = self._create_ui()
    
    def _create_ui(self):
        """创建UI组件"""
        group = QGroupBox("存储文件")
        layout = QHBoxLayout(group)
        
        self.storage_input = QLineEdit()
        self.storage_input.setPlaceholderText("选择调用图数据存储文件路径")
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_storage)
        
        layout.addWidget(self.storage_input)
        layout.addWidget(browse_btn)
        
        return group
    
    def _browse_storage(self):
        """浏览并选择存储文件"""
        path, _ = QFileDialog.getOpenFileName(
            self.parent, "选择存储文件路径", "", "Joblib Files (*.jb)")
        if path:
            self.storage_input.setText(path)
    
    def get_storage_path(self):
        """获取当前存储文件路径"""
        return self.storage_input.text()
    
    def set_storage_path(self, path):
        """设置存储文件路径"""
        self.storage_input.setText(path)
    
    def get_widget(self):
        """获取组件Widget"""
        return self.group


class VisualizationSettings:
    """可视化设置组件"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.layout_combo = None
        self.show_files_checkbox = None
        self.max_nodes_slider = None
        self.max_nodes_value = None
        self.physics_checkbox = None
        self.node_size_checkbox = None
        self.group = self._create_ui()
    
    def _create_ui(self):
        """创建UI组件"""
        group = QGroupBox("可视化设置")
        main_layout = QVBoxLayout(group)
        
        # 布局选择
        layout_selection_layout = QHBoxLayout()
        layout_label = QLabel("布局方式:")
        layout_label.setStyleSheet("QLabel { color: black; }")
        
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["力导向布局", "分层布局(上到下)", "分层布局(左到右)", "圆形布局", "放射状布局"])
        
        layout_selection_layout.addWidget(layout_label)
        layout_selection_layout.addWidget(self.layout_combo)
        main_layout.addLayout(layout_selection_layout)
        
        # 节点筛选
        filter_layout = QHBoxLayout()
        
        self.show_files_checkbox = QCheckBox("显示文件节点")
        self.show_files_checkbox.setChecked(True)
        self.show_files_checkbox.setStyleSheet("QCheckBox { color: black; }")
        
        self.max_nodes_label = QLabel("最大显示节点数:")
        self.max_nodes_label.setStyleSheet("QLabel { color: black; }")
        
        self.max_nodes_slider = QSlider(Qt.Horizontal)
        self.max_nodes_slider.setMinimum(10)
        self.max_nodes_slider.setMaximum(1000)
        self.max_nodes_slider.setValue(100)
        self.max_nodes_slider.setTickPosition(QSlider.TicksBelow)
        self.max_nodes_slider.setTickInterval(50)
        
        self.max_nodes_value = QLabel("100")
        self.max_nodes_value.setStyleSheet("QLabel { color: black; }")
        self.max_nodes_slider.valueChanged.connect(
            lambda v: self.max_nodes_value.setText(str(v)))
        
        filter_layout.addWidget(self.show_files_checkbox)
        filter_layout.addWidget(self.max_nodes_label)
        filter_layout.addWidget(self.max_nodes_slider)
        filter_layout.addWidget(self.max_nodes_value)
        main_layout.addLayout(filter_layout)
        
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
        main_layout.addLayout(advanced_layout)
        
        return group
    
    def get_layout_option(self):
        """获取布局选项"""
        return self.layout_combo.currentText()
    
    def show_file_nodes(self):
        """是否显示文件节点"""
        return self.show_files_checkbox.isChecked()
    
    def get_max_nodes(self):
        """获取最大节点数"""
        return self.max_nodes_slider.value()
    
    def use_physics(self):
        """是否启用物理引擎"""
        return self.physics_checkbox.isChecked()
    
    def size_by_importance(self):
        """是否根据重要性调整节点大小"""
        return self.node_size_checkbox.isChecked()
    
    def get_widget(self):
        """获取组件Widget"""
        return self.group


class FunctionQueryInput:
    """函数查询输入组件"""
    
    def __init__(self, parent=None, on_query=None, on_list_all=None, on_show_all=None):
        self.parent = parent
        self.on_query = on_query
        self.on_list_all = on_list_all
        self.on_show_all = on_show_all
        self.function_input = None
        self.query_mode_combo = None
        self.group = self._create_ui()
    
    def _create_ui(self):
        """创建UI组件"""
        group = QGroupBox("函数查询")
        main_layout = QVBoxLayout(group)
        
        # 第一行:查询模式选择
        mode_layout = QHBoxLayout()
        mode_label = QLabel("查询模式:")
        mode_label.setStyleSheet("QLabel { color: black; }")
        
        self.query_mode_combo = QComboBox()
        self.query_mode_combo.addItems(["调用者(谁调用它)", "被调用者(它调用谁)", "双向关系"])
        self.query_mode_combo.setCurrentIndex(2)  # 默认双向关系
        
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.query_mode_combo, 1)
        main_layout.addLayout(mode_layout)
        
        # 第二行:函数输入和按钮
        input_layout = QHBoxLayout()
        
        self.function_input = QLineEdit()
        self.function_input.setPlaceholderText("输入要查询的函数名（例如：os.execute）")
        
        # 创建自动完成器
        self.completer = QCompleter([])
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.function_input.setCompleter(self.completer)
        
        query_btn = QPushButton("查询")
        query_btn.setObjectName("primaryButton")
        if self.on_query:
            query_btn.clicked.connect(self.on_query)
        
        list_all_btn = QPushButton("显示所有函数入口")
        if self.on_list_all:
            list_all_btn.clicked.connect(self.on_list_all)
        
        show_all_relations_btn = QPushButton("显示所有函数关系")
        if self.on_show_all:
            show_all_relations_btn.clicked.connect(self.on_show_all)
        
        input_layout.addWidget(self.function_input)
        input_layout.addWidget(query_btn)
        input_layout.addWidget(list_all_btn)
        input_layout.addWidget(show_all_relations_btn)
        
        main_layout.addLayout(input_layout)
        
        return group
    
    def get_function_name(self):
        """获取函数名输入"""
        return self.function_input.text()
    
    def set_function_name(self, name):
        """设置函数名输入"""
        self.function_input.setText(name)
    
    def get_query_mode(self):
        """获取查询模式 (0=调用者, 1=被调用者, 2=双向关系)"""
        return self.query_mode_combo.currentIndex()
    
    def update_completer_items(self, items):
        """更新自动完成器的项目列表"""
        self.completer.setModel(QStringListModel(items))
    
    def get_widget(self):
        """获取组件Widget"""
        return self.group

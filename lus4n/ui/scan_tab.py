#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - 扫描选项卡模块
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
    QLineEdit, QPushButton, QTextEdit, QMessageBox, QProgressBar,
    QFileDialog, QCheckBox
)
from PySide6.QtGui import QTextCursor
from lus4n.ui.scan_thread import ScanThread


class ScanTab(QWidget):
    """扫描选项卡类"""
    
    def __init__(self, parent=None, status_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.status_callback = status_callback
        self.scan_thread = None
        self.scanning = False
        self.progress_bar = None
        self.default_storage_path = None  # 将在外部设置
        
        self.initUI()
    
    def initUI(self):
        """初始化 UI 组件"""
        layout = QVBoxLayout(self)
        
        # 路径选择区域
        path_group = QGroupBox("代码路径")
        path_layout = QHBoxLayout(path_group)
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("选择要扫描的 Lua 代码路径")
        path_browse_btn = QPushButton("浏览...")
        path_browse_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(path_browse_btn)
        layout.addWidget(path_group)
        
        # 存储文件区域
        storage_group = QGroupBox("存储文件")
        storage_layout = QHBoxLayout(storage_group)
        self.storage_input = QLineEdit()
        self.storage_input.setPlaceholderText("选择调用图数据存储文件路径 (可选)")
        storage_browse_btn = QPushButton("浏览...")
        storage_browse_btn.clicked.connect(self.browse_storage)
        storage_layout.addWidget(self.storage_input)
        storage_layout.addWidget(storage_browse_btn)
        layout.addWidget(storage_group)
        
        # 文件后缀区域
        extensions_group = QGroupBox("文件后缀")
        extensions_layout = QVBoxLayout(extensions_group)
        extensions_help = QLabel("指定要扫描的文件后缀，多个后缀用逗号分隔")
        self.extensions_input = QLineEdit(".lua")
        self.extensions_input.setStyleSheet("color: #000000; background-color: #ffffff;")
        self.extensions_input.setPlaceholderText(".lua,.ncprog,.target")
        extensions_layout.addWidget(extensions_help)
        extensions_layout.addWidget(self.extensions_input)
        layout.addWidget(extensions_group)
        
        # 扫描选项区域
        options_group = QGroupBox("扫描选项")
        options_layout = QHBoxLayout(options_group)
        self.multiprocess_checkbox = QCheckBox("启用多进程并行扫描 (加速大型项目)")
        self.multiprocess_checkbox.setChecked(True)
        self.multiprocess_checkbox.setStyleSheet("QCheckBox { color: black; }")
        self.incremental_checkbox = QCheckBox("启用增量扫描 (只扫描修改的文件)")
        self.incremental_checkbox.setChecked(True)
        self.incremental_checkbox.setStyleSheet("QCheckBox { color: black; }")
        options_layout.addWidget(self.multiprocess_checkbox)
        options_layout.addWidget(self.incremental_checkbox)
        options_layout.addStretch()
        layout.addWidget(options_group)
        
        # 扫描按钮
        scan_btn = QPushButton("开始扫描")
        scan_btn.setMinimumHeight(40)
        scan_btn.setObjectName("primaryButton")
        scan_btn.clicked.connect(self.start_scan)
        layout.addWidget(scan_btn)
        
        # 日志区域
        log_group = QGroupBox("扫描日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("color: #333333;")  # 使用深灰色文本
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)
    
    def set_progress_bar(self, progress_bar):
        """设置进度条引用"""
        self.progress_bar = progress_bar
    
    def set_default_storage_path(self, path):
        """设置默认存储路径"""
        self.default_storage_path = path
        
    def browse_path(self):
        """浏览并选择 Lua 代码路径"""
        path = QFileDialog.getExistingDirectory(self, "选择 Lua 代码路径")
        if path:
            self.path_input.setText(path)
    
    def browse_storage(self):
        """浏览并选择存储文件路径"""
        path, _ = QFileDialog.getSaveFileName(self, "选择存储文件路径", "", "Joblib Files (*.jb)")
        if path:
            self.storage_input.setText(path)
    
    def log(self, message):
        """向日志区域添加消息"""
        self.log_text.append(message)
        self.log_text.moveCursor(QTextCursor.End)
        self.log_text.ensureCursorVisible()
    
    def update_status(self, message):
        """更新状态栏消息"""
        if self.status_callback:
            self.status_callback(message)
        
        # 如果是"扫描完成"状态，则隐藏进度条
        if message == "扫描完成" or message == "扫描出错" or message == "扫描已中止":
            if self.progress_bar:
                self.progress_bar.setVisible(False)
            self.scanning = False
    
    def start_scan(self):
        """开始扫描"""
        # 如果已经有一个扫描线程在运行，则返回
        if self.scanning:
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("扫描中")
            msgBox.setText("当前已有扫描任务正在进行")
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setStyleSheet("QLabel{min-width: 300px; color: black;}")
            msgBox.exec_()
            return

        path = self.path_input.text()
        if not path or not os.path.exists(path):
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("路径错误")
            msgBox.setText("请选择有效的 Lua 代码路径")
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.setStyleSheet("QLabel{min-width: 300px; color: black;}")
            msgBox.exec_()
            return
        
        storage = self.storage_input.text()
        if not storage:
            storage = self.default_storage_path
            self.storage_input.setText(storage)
        
        extensions = [ext.strip() for ext in self.extensions_input.text().split(",")]
        use_multiprocess = self.multiprocess_checkbox.isChecked()
        use_incremental = self.incremental_checkbox.isChecked()
        
        # 显示进度条 (初始为不确定模式,收到进度信号后切换为确定模式)
        if self.progress_bar:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 初始不确定进度模式,收集文件时使用
        self.update_status("正在扫描...")
        self.scanning = True
        
        # 清除日志
        self.log_text.clear()
        
        # 清除旧的信号连接
        if self.scan_thread:
            try:
                self.scan_thread.update_log.disconnect()
                self.scan_thread.update_status.disconnect()
                self.scan_thread.scan_finished.disconnect()
                self.scan_thread.scan_error.disconnect()
                del self.scan_thread
            except:
                pass  # 忽略断开连接时的错误
        
        # 创建并启动扫描线程
        self.scan_thread = ScanThread(path, storage, extensions, use_multiprocess, use_incremental)
        
        # 连接信号
        self.scan_thread.update_log.connect(self.log)
        self.scan_thread.update_status.connect(self.update_status)
        self.scan_thread.update_progress.connect(self.on_progress_update)
        self.scan_thread.scan_finished.connect(self.on_scan_finished)
        self.scan_thread.scan_error.connect(self.on_scan_error)
        
        # 启动线程
        self.scan_thread.start()
    
    def on_progress_update(self, current, total):
        """进度更新的回调处理"""
        if self.progress_bar:
            # 设置确定进度模式
            if self.progress_bar.maximum() == 0:
                self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
    
    def on_scan_finished(self, result):
        """扫描完成的回调处理"""
        d, g = result
        
        # 更新界面
        self.log(f"扫描完成！发现 {len(d)} 个文件，{len(g.nodes)} 个节点")
        
        # 如果有查询选项卡，更新查询存储路径
        if hasattr(self.parent, 'query_tab') and self.parent.query_tab:
            self.parent.query_tab.set_storage_path(self.storage_input.text())
        
        # 显示完成消息 - 使用自定义格式确保内容可见
        msgBox = QMessageBox(self)
        msgBox.setWindowTitle("扫描完成")
        msgBox.setText(f"扫描完成！\n\n发现 {len(d)} 个文件，{len(g.nodes)} 个节点\n\n结果已保存到：{self.storage_input.text()}")
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setStyleSheet("QLabel{min-width: 400px; color: black;}")
        msgBox.exec_()
        
        # 通知主窗口保存设置
        if hasattr(self.parent, 'save_settings'):
            self.parent.save_settings()
    
    def on_scan_error(self, error_msg):
        """扫描出错的回调处理"""
        # 记录错误
        self.log(f"扫描出错：{error_msg}")
        
        # 显示错误消息 - 使用自定义格式确保内容可见
        msgBox = QMessageBox(self)
        msgBox.setWindowTitle("扫描错误")
        msgBox.setText(f"扫描过程中发生错误：\n\n{str(error_msg)}")
        msgBox.setIcon(QMessageBox.Critical)
        msgBox.setStyleSheet("QLabel{min-width: 400px; color: black;}")
        msgBox.exec_()
    
    def get_path(self):
        """获取当前路径"""
        return self.path_input.text()
    
    def get_storage_path(self):
        """获取当前存储路径"""
        return self.storage_input.text()
    
    def set_path(self, path):
        """设置路径"""
        self.path_input.setText(path)
    
    def set_storage_path(self, path):
        """设置存储路径"""
        self.storage_input.setText(path)
    
    def stop_thread(self):
        """停止扫描线程"""
        if self.scan_thread and self.scanning:
            self.scan_thread.stop()
            self.scan_thread.terminate()
            self.scan_thread.wait()

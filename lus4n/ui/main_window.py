#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - 主窗口模块
"""

import os
import sys
import tempfile
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QStatusBar, QProgressBar, QMessageBox
)

from lus4n.ui.scan_tab import ScanTab
from lus4n.ui.query_tab import QueryTab


class Lus4nMainWindow(QMainWindow):
    """Lus4n GUI 主窗口类"""
    
    def __init__(self):
        super().__init__()
        # 初始化属性
        self.settings = QSettings("Lusipad", "Lus4n")
        self.temp_dir = tempfile.gettempdir()
        
        # 设置默认存储路径为程序所在目录
        self.default_storage_path = os.path.join(
            os.path.dirname(os.path.abspath(sys.argv[0])), 
            "lus4n_result.jb"
        )
        
        # 初始化 UI 和加载设置
        self.initUI()
        self.loadSettings()
    
    def initUI(self):
        """初始化用户界面"""
        # 设置窗口基本属性
        self.setWindowTitle("Lus4n - Lua 调用图生成工具")
        self.setMinimumSize(900, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建选项卡
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)  # 更现代的选项卡样式
        main_layout.addWidget(self.tabs)
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        
        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.statusBar.addPermanentWidget(self.progress_bar)
        
        # 添加扫描选项卡
        self.scan_tab = ScanTab(self, self.update_status)
        self.scan_tab.set_progress_bar(self.progress_bar)
        self.scan_tab.set_default_storage_path(self.default_storage_path)
        self.tabs.addTab(self.scan_tab, "扫描 Lua 代码")
        
        # 添加查询选项卡
        self.query_tab = QueryTab(self, self.update_status)
        self.tabs.addTab(self.query_tab, "查询调用关系")
    
    def loadSettings(self):
        """加载应用设置"""
        # 加载最近使用的路径
        last_path = self.settings.value("last_path", "")
        if last_path:
            self.scan_tab.set_path(last_path)
            
        last_storage = self.settings.value("last_storage", "")
        if last_storage and os.path.exists(last_storage):
            self.scan_tab.set_storage_path(last_storage)
            self.query_tab.set_storage_path(last_storage)
        else:
            # 如果没有上次存储的路径或文件不存在，则使用默认路径
            self.scan_tab.set_storage_path(self.default_storage_path)
            self.query_tab.set_storage_path(self.default_storage_path)
            
        # 加载最近的查询
        recent_queries = self.settings.value("recent_queries", [])
        if recent_queries:
            self.query_tab.set_recent_queries(recent_queries)
    
    def save_settings(self):
        """保存应用设置"""
        # 保存最近使用的路径
        self.settings.setValue("last_path", self.scan_tab.get_path())
        self.settings.setValue("last_storage", self.scan_tab.get_storage_path())
        
        # 保存最近的查询
        recent_queries = self.query_tab.get_recent_queries()
        self.settings.setValue("recent_queries", recent_queries)
    
    def update_status(self, message):
        """更新状态栏消息"""
        self.statusBar.showMessage(message)
    
    def closeEvent(self, event):
        """关闭窗口事件处理"""
        # 检查是否有扫描线程在运行
        if hasattr(self.scan_tab, 'scanning') and self.scan_tab.scanning:
            # 询问用户是否终止线程
            reply = QMessageBox.question(
                self, "确认退出", 
                "扫描任务正在进行中，确定要退出吗？", 
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 停止扫描
                self.scan_tab.stop_thread()
            else:
                event.ignore()
                return
        
        # 保存设置
        self.save_settings()
        event.accept()

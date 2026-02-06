#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - WebView 窗口模块
用于在 GUI 内嵌显示可视化 HTML
"""

import os
from PySide6.QtCore import QUrl, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QSizePolicy
)

# 尝试导入 QWebEngineView
WEBENGINE_AVAILABLE = False
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineSettings
    WEBENGINE_AVAILABLE = True
except ImportError:
    pass


class WebViewWindow(QWidget):
    """WebView 窗口类，在 GUI 内显示可视化 HTML"""
    
    def __init__(self, parent=None, html_path=None):
        super().__init__(parent)
        self.html_path = html_path
        self.webview = None
        
        self.init_ui()
        
        if html_path:
            self.load_html(html_path)
    
    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 检查 WebEngine 是否可用
        if not WEBENGINE_AVAILABLE:
            # 显示错误信息
            error_label = QLabel(
                "⚠️ 未安装 PySide6-WebEngine\n\n"
                "请运行以下命令安装:\n"
                "pip install PySide6-WebEngine\n\n"
                "安装后重启应用即可使用内嵌 WebView 功能"
            )
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("""
                QLabel {
                    background-color: #fff3cd;
                    border: 2px solid #ffc107;
                    border-radius: 5px;
                    padding: 20px;
                    color: #856404;
                    font-size: 14px;
                }
            """)
            layout.addWidget(error_label)
            return
        
        # 创建工具栏
        toolbar = QHBoxLayout()
        
        # 刷新按钮
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(self.refresh_btn)
        
        # 在浏览器中打开按钮
        self.open_browser_btn = QPushButton("🌐 在浏览器中打开")
        self.open_browser_btn.clicked.connect(self.open_in_browser)
        toolbar.addWidget(self.open_browser_btn)
        
        toolbar.addStretch()
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        toolbar.addWidget(self.status_label)
        
        layout.addLayout(toolbar)
        
        # 创建 WebView
        self.webview = QWebEngineView()
        self.webview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 设置 WebEngine 配置
        settings = self.webview.settings()
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        
        # 连接加载完成信号
        self.webview.loadFinished.connect(self.on_load_finished)
        
        layout.addWidget(self.webview)
    
    def load_html(self, html_path):
        """加载 HTML 文件"""
        if not WEBENGINE_AVAILABLE:
            return
        
        self.html_path = html_path
        
        if not os.path.exists(html_path):
            self.status_label.setText(f"错误: 文件不存在 - {html_path}")
            return
        
        # 转换为文件 URL
        file_url = QUrl.fromLocalFile(os.path.abspath(html_path))
        self.webview.setUrl(file_url)
        self.status_label.setText(f"加载中... {os.path.basename(html_path)}")
    
    def on_load_finished(self, success):
        """加载完成回调"""
        if success:
            self.status_label.setText(f"✓ 已加载: {os.path.basename(self.html_path) if self.html_path else ''}")
        else:
            self.status_label.setText("✗ 加载失败")
    
    def refresh(self):
        """刷新页面"""
        if WEBENGINE_AVAILABLE and self.webview:
            self.webview.reload()
            self.status_label.setText("刷新中...")
    
    def open_in_browser(self):
        """在外部浏览器中打开"""
        if self.html_path and os.path.exists(self.html_path):
            import webbrowser
            webbrowser.open_new_tab(f"file://{self.html_path}")
    
    @staticmethod
    def is_available():
        """检查 WebEngine 是否可用"""
        return WEBENGINE_AVAILABLE

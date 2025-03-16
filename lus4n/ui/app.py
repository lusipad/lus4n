#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - 应用入口模块
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from lus4n.ui.main_window import Lus4nMainWindow
from lus4n.ui.styles import get_application_style


def run_app():
    """运行Lus4n应用"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用 Fusion 风格，在所有平台上看起来都很现代
    
    # 设置应用字体
    font = QFont("Microsoft YaHei UI", 9)  # 使用微软雅黑
    app.setFont(font)
    
    # 设置样式表
    app.setStyleSheet(get_application_style())
    
    # 创建主窗口并显示
    window = Lus4nMainWindow()
    window.show()
    
    # 运行应用
    return app.exec()

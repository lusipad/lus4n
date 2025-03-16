#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - UI 样式定义模块
"""

def get_application_style():
    """
    返回整个应用的样式表
    """
    return """
        QMainWindow, QDialog {
            background-color: #FFFFFF;
        }
        QGroupBox {
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            margin-top: 1ex;
            font-weight: bold;
            background-color: #FFFFFF;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
            color: #333333;
        }
        QPushButton {
            background-color: #F0F0F0;
            color: #333333;
            border: none;
            border-radius: 4px;
            padding: 5px 10px;
            min-height: 24px;
        }
        QPushButton:hover {
            background-color: #E0E0E0;
        }
        QPushButton:pressed {
            background-color: #D0D0D0;
        }
        QPushButton#primaryButton {
            background-color: #FF6D3F;  /* 火绒橙色 */
            color: white;
            font-weight: bold;
        }
        QPushButton#primaryButton:hover {
            background-color: #FF5A2C;
        }
        QPushButton#primaryButton:pressed {
            background-color: #FF4719;
        }
        QLineEdit {
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            padding: 4px;
            background-color: white;
            color: #000000;
        }
        QLineEdit:focus {
            border: 1px solid #FF6D3F;
        }
        QTextEdit {
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            background-color: white;
            color: #000000;
        }
        QComboBox {
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            padding: 4px;
            background-color: white;
            color: #000000;
        }
        QComboBox:hover {
            border: 1px solid #b0b0b0;
        }
        QComboBox QAbstractItemView {
            border: 1px solid #d0d0d0;
            border-radius: 0px;
            background-color: white;
            color: #000000;
            selection-background-color: #FF6D3F;
            selection-color: white;
        }
        QTabWidget::pane {
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            top: -1px;
        }
        QTabBar::tab {
            background-color: #F0F0F0;
            border: 1px solid #d0d0d0;
            border-bottom-color: #d0d0d0;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            min-width: 8ex;
            padding: 8px 12px;
            color: #000000;
        }
        QTabBar::tab:selected {
            background-color: white;
            border-bottom-color: white;
        }
        QTabBar::tab:hover:!selected {
            background-color: #E0E0E0;
        }
        QStatusBar {
            background-color: #F5F5F5;
            color: #333333;
        }
        QProgressBar {
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            text-align: center;
            color: white;
        }
        QProgressBar::chunk {
            background-color: #FF6D3F;
            width: 10px;
        }
    """

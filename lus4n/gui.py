#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - Lua 调用图 GUI 界面
这是一个兼容性入口点，用于保持向后兼容性
实际实现已重构到 lus4n.ui 包中
"""

import sys
from lus4n.ui.app import run_app

# -----------------------------------------------------
# 主函数 - 应用入口
# -----------------------------------------------------
def main():
    """应用主入口函数"""
    sys.exit(run_app())

if __name__ == "__main__":
    main()

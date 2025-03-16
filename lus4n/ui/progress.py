#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - GUI进度展示模块
"""

import time


class GUIProgress:
    """提供 GUI 进度展示的替代 tqdm 类"""
    def __init__(self, iterable=None, total=None, desc="Progress", update_func=None):
        self.iterable = iterable
        self.total = total or (len(iterable) if iterable is not None else None)
        self.desc = desc
        self.update_func = update_func
        self.n = 0
        self.last_update_time = time.time()

    def __iter__(self):
        if self.iterable is None:
            return iter([])
        
        self.n = 0
        for item in self.iterable:
            yield item
            self.n += 1
            
            # 限制更新频率，避免过多的信号发送
            current_time = time.time()
            if current_time - self.last_update_time > 0.1:  # 每 0.1 秒更新一次
                if self.update_func:
                    progress_info = f"{self.desc}: {self.n}/{self.total}" if self.total else f"{self.desc}: {self.n}"
                    self.update_func(progress_info)
                self.last_update_time = current_time
        
        # 确保最后一次更新显示 100%
        if self.update_func:
            progress_info = f"{self.desc}: {self.n}/{self.total}" if self.total else f"{self.desc}: {self.n}"
            self.update_func(progress_info)

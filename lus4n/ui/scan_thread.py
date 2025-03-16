#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - 扫描线程模块
"""

import os
import networkx as nx
from PySide6.QtCore import QThread, Signal
from joblib import dump
from lus4n.graph import scan_one_file


class ScanThread(QThread):
    """后台扫描线程，避免 UI 冻结"""
    # 定义信号
    update_log = Signal(str)             # 更新日志的信号
    update_status = Signal(str)          # 更新状态栏的信号
    scan_finished = Signal(tuple)        # 扫描完成的信号，传递结果
    scan_error = Signal(str)             # 扫描错误的信号
    
    def __init__(self, path, storage, extensions):
        super().__init__()
        self.path = path
        self.storage = storage
        self.extensions = extensions
        self.stopped = False
    
    def run(self):
        """线程主函数，执行扫描操作"""
        try:
            # 更新状态
            self.update_status.emit("正在扫描...")
            
            # 向主线程发送日志信息
            self.update_log.emit(f"开始扫描路径：{self.path}")
            self.update_log.emit(f"文件后缀：{', '.join(self.extensions)}")
            self.update_log.emit(f"存储文件：{self.storage}")
            
            # 确保存储文件目录存在
            storage_dir = os.path.dirname(self.storage)
            if storage_dir and not os.path.exists(storage_dir):
                os.makedirs(storage_dir)
            
            # 收集文件阶段
            self.update_log.emit("正在收集要扫描的文件...")
            whole_call_graph = {}
            whole_call_network = nx.DiGraph()
            will_scan = []
            
            # 如果没有指定后缀，默认使用 .lua
            if not self.extensions:
                self.extensions = [".lua"]
                
            # 收集所有需要扫描的文件
            for path, dir_list, file_list in os.walk(self.path):
                for file_name in file_list:
                    # 检查是否被用户中止
                    if self.stopped:
                        self.update_log.emit("扫描已被用户中止")
                        self.update_status.emit("扫描已中止")
                        return
                        
                    file_path = os.path.join(path, file_name)
                    try:
                        with open(file_path, "rb") as f:
                            content = f.read(100)  # 只读取前 100 字节用于判断
                            # 检查文件是否有指定的后缀
                            has_valid_extension = any(file_path.endswith(ext) for ext in self.extensions)
                            
                            # 添加文件到扫描列表的条件：
                            # 1. 有效的后缀名且不是 Lua 字节码
                            # 2. 以 #!/usr/bin/lua 开头的任何文件
                            if has_valid_extension and not content.startswith(b"\x1bL"):
                                will_scan.append(file_path)
                            elif content.startswith(b"#!/usr/bin/lua"):
                                will_scan.append(file_path)
                    except PermissionError:
                        self.update_log.emit(f"警告：无权限访问文件 {file_path}")
                    except Exception as e:
                        self.update_log.emit(f"警告：处理文件 {file_path} 时出错 [{e}]")
            
            self.update_log.emit(f"找到 {len(will_scan)} 个可扫描的文件")
            
            # 扫描每个文件
            for i, file_path in enumerate(will_scan):
                # 检查是否被用户中止
                if self.stopped:
                    self.update_log.emit("扫描已被用户中止")
                    self.update_status.emit("扫描已中止")
                    return
                
                # 更新扫描进度
                if i % 10 == 0 or i == len(will_scan) - 1:  # 每 10 个文件更新一次或最后一个文件
                    progress_info = f"正在扫描：[{i+1}/{len(will_scan)}] {file_path}"
                    self.update_log.emit(progress_info)
                    self.update_status.emit(f"正在扫描... ({i+1}/{len(will_scan)})")
                
                # 扫描单个文件
                _, call_graph, require = scan_one_file(file_path, None, False)
                
                # 处理相对路径
                relative_file_path = file_path[len(self.path):]
                if not relative_file_path.startswith("/"):
                    relative_file_path = "/" + relative_file_path
                
                # 添加到全局图
                whole_call_graph[relative_file_path] = call_graph
                whole_call_network.add_node(relative_file_path, role='file')
                package_name = os.path.basename(file_path).replace(".lua", "")
                
                # 处理函数调用关系
                for tmp_name in call_graph.keys():
                    if tmp_name == "[G]":
                        import xxhash
                        default_main = f"{package_name}.main.{xxhash.xxh32(file_path).hexdigest()}"
                        for called in call_graph["[G]"]:
                            whole_call_network.add_edge(relative_file_path, default_main, action='export')
                            whole_call_network.add_edge(default_main, called, action="call")
                    if tmp_name.startswith("[X]"):
                        exported = tmp_name.replace("[X]", "")
                        sub_names = exported.split('.')
                        if len(sub_names) > 1:
                            father = sub_names[0]
                            left = exported[len(father):]
                            # TODO: 或许也可以用 M./_M.来筛选导出函数？
                            _exported = f"{package_name}{left}" if father not in require else exported
                        else:
                            _exported = exported
                        whole_call_network.add_edge(relative_file_path, _exported, action="export")
                        for called in call_graph[tmp_name]:
                            whole_call_network.add_edge(_exported, called, action='call')
                    if tmp_name.startswith("[L]"):
                        defined = tmp_name.replace("[L]", "")
                        whole_call_network.add_edge(relative_file_path, defined, action="define")
                        for called in call_graph[tmp_name]:
                            whole_call_network.add_edge(defined, called, action='call')
            
            # 保存结果阶段
            self.update_log.emit("所有文件扫描完成，正在保存结果...")
            dump(whole_call_network, self.storage)
            
            self.update_log.emit("调用图已保存到存储文件")
            self.update_log.emit("===扫描完成===")
            
            # 确保状态栏更新为扫描完成
            self.update_status.emit("扫描完成")
            
            # 发送完成信号
            self.scan_finished.emit((whole_call_graph, whole_call_network))
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.update_log.emit(f"扫描过程中出现错误:\n{error_details}")
            self.update_status.emit("扫描出错")
            self.scan_error.emit(str(e))
    
    def stop(self):
        """安全停止线程"""
        self.stopped = True

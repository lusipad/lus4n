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
            
            # 遍历目录，收集文件
            all_files = []  # 记录所有文件
            skipped_files = []  # 记录跳过的文件
            valid_extension_files = []  # 记录符合扩展名的文件
            
            for path, dir_list, file_list in os.walk(self.path):
                for file_name in file_list:
                    if self.stopped:
                        self.update_status.emit("扫描已中止")
                        return
                    
                    file_path = os.path.join(path, file_name)
                    all_files.append(file_path)
                    
                    # 1. 首先检查文件是否有指定的后缀，不符合的直接跳过
                    has_valid_extension = any(file_name.endswith(ext) for ext in self.extensions)
                    if not has_valid_extension:
                        _, ext = os.path.splitext(file_name)
                        skipped_files.append((file_path, f"不符合的文件后缀：{ext}"))
                        continue
                    
                    valid_extension_files.append(file_path)
                    
                    # 检查文件是否存在
                    if not os.path.exists(file_path):
                        skipped_files.append((file_path, "文件不存在"))
                        continue
                    
                    try:
                        # 检查文件是否可读取
                        try:
                            content = open(file_path, "rb").read()
                        except (PermissionError, IOError) as e:
                            skipped_files.append((file_path, f"文件读取错误：{str(e)}"))
                            continue
                        
                        # 2. 检查是否是 lua 字节码文件，不是字节码的就当作文本处理
                        if content.startswith(b"\x1bL"):
                            skipped_files.append((file_path, "Lua 字节码文件"))
                            continue
                            
                        # 直接进行编码检测，不再检查二进制特征
                        # 尝试检测编码
                        encodings_to_try = ['utf-8', 'GBK', 'GB2312', 'latin-1']
                        detected_encoding = None
                        decoded_content = None
                        
                        for encoding in encodings_to_try:
                            try:
                                decoded_content = content.decode(encoding)
                                detected_encoding = encoding
                                break
                            except UnicodeDecodeError:
                                continue
                        
                        if detected_encoding is None:
                            skipped_files.append((file_path, "无法解码的文件编码"))
                            continue
                            
                        # 添加文件到扫描列表的条件
                        # 对于用户指定后缀的文件，直接处理，不再检查是否有 Lua 特征
                        will_scan.append((file_path, detected_encoding))
                        if detected_encoding != 'utf-8':
                            self.update_log.emit(f"文件 {file_path} 使用 {detected_encoding} 编码")
                    except PermissionError:
                        skipped_files.append((file_path, "权限错误"))
                    except Exception as e:
                        skipped_files.append((file_path, f"未知错误：{str(e)}"))
            
            self.update_log.emit(f"扫描范围：共找到 {len(all_files)} 个文件")
            self.update_log.emit(f"符合后缀的文件：{len(valid_extension_files)} 个")
            self.update_log.emit(f"将处理 {len(will_scan)} 个文件")
            
            # 显示符合后缀的文件列表
            if valid_extension_files:
                self.update_log.emit("\n符合后缀的文件列表（前 100 个）：")
                for file_path in valid_extension_files[:100]:  # 限制显示数量
                    rel_path = os.path.relpath(file_path, self.path)
                    self.update_log.emit(f"- {rel_path}")
                
                if len(valid_extension_files) > 100:
                    self.update_log.emit(f"... 还有 {len(valid_extension_files) - 100} 个符合后缀的文件 (未显示)")
            
            # 处理收集到的文件
            self.update_log.emit("\n开始处理文件...")
            processed_files = {}  # 记录处理状态
            nodes_count = 0

            for i, (file_path, encoding) in enumerate(will_scan):
                if self.stopped:
                    self.update_status.emit("扫描已中止")
                    return
                
                # 更新状态
                progress = int((i + 1) / len(will_scan) * 100)
                self.update_status.emit(f"正在扫描... {progress}%")
                
                # 扫描单个文件
                rel_path = os.path.relpath(file_path, self.path)
                try:
                    # 使用检测到的编码解析文件
                    _, call_graph, require, status = scan_one_file(file_path, "json", False, encoding)
                    
                    # 记录处理状态
                    processed_files[rel_path] = status
                    
                    # 如果文件成功解析并且有调用关系，则添加到调用图中
                    if status == "成功" and call_graph:
                        # 将结果添加到整体调用图
                        relative_file_path = file_path[len(self.path):]
                        if not relative_file_path.startswith("/"):
                            relative_file_path = "/" + relative_file_path
                        whole_call_graph[relative_file_path] = call_graph
                        whole_call_network.add_node(relative_file_path, role='file')
                        package_name = os.path.basename(file_path).replace(".lua", "")
                        
                        # 处理调用关系
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
                except Exception as e:
                    self.update_log.emit(f"解析 {rel_path} 时出错：{str(e)}")
                    processed_files[rel_path] = f"解析错误：{str(e)}"
                
                # 每处理 20 个文件显示一次状态
                if (i + 1) % 20 == 0 or i == len(will_scan) - 1:
                    self.update_log.emit(f"已处理：{i + 1}/{len(will_scan)} 个文件")
            
            # 保存扫描结果
            self.update_log.emit("\n正在保存扫描结果...")
            data = {
                'whole_call_graph': whole_call_graph,
                'whole_call_network': whole_call_network,
                'file_status': processed_files
            }
            dump(data, self.storage)
            
            # 显示处理结果统计
            status_counts = {}
            for status in processed_files.values():
                status_counts[status] = status_counts.get(status, 0) + 1
            
            self.update_log.emit("\n扫描结果统计：")
            for status, count in status_counts.items():
                self.update_log.emit(f"- {status}：{count} 个文件")
            
            # 提供按键查看详细的处理状态
            self.update_log.emit("\n处理状态详情 (部分)：")
            # 只显示一部分处理状态，以免日志过长
            shown_files = list(processed_files.items())[:50]
            for rel_path, status in shown_files:
                self.update_log.emit(f"- {rel_path}:{status}")
            
            if len(processed_files) > 50:
                self.update_log.emit(f"... 还有 {len(processed_files) - 50} 个文件 (未显示)")
            
            self.update_log.emit("\n扫描完成")
            
            # 发送扫描完成信号
            self.scan_finished.emit((whole_call_graph, whole_call_network))
            self.update_status.emit("扫描完成")
            
        except Exception as e:
            self.update_log.emit(f"扫描出错：{str(e)}")
            self.scan_error.emit(str(e))
            self.update_status.emit("扫描出错")
    
    def stop(self):
        """安全停止线程"""
        self.stopped = True

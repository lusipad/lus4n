#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - 扫描线程模块
"""

import os
import networkx as nx
import multiprocessing
import xxhash
from PySide6.QtCore import QThread, Signal
from joblib import dump, load
from lus4n.graph import scan_one_file


def scan_file_wrapper(args):
    """包装函数,用于多进程调用 scan_one_file
    
    返回: (file_path, relative_path, call_graph, require, status, encoding)
    """
    file_path, encoding, base_path = args
    
    # 调用原始扫描函数
    _, call_graph, require, status = scan_one_file(file_path, "json", False, encoding)
    
    # 计算相对路径
    relative_file_path = file_path[len(base_path):]
    if not relative_file_path.startswith("/"):
        relative_file_path = "/" + relative_file_path
    
    return (file_path, relative_file_path, call_graph, require, status, encoding)


class ScanThread(QThread):
    """后台扫描线程，避免 UI 冻结"""
    # 定义信号
    update_log = Signal(str)             # 更新日志的信号
    update_status = Signal(str)          # 更新状态栏的信号
    update_progress = Signal(int, int)   # 更新进度的信号 (当前, 总数)
    scan_finished = Signal(tuple)        # 扫描完成的信号，传递结果
    scan_error = Signal(str)             # 扫描错误的信号
    
    def __init__(self, path, storage, extensions, use_multiprocess=True, use_incremental=True):
        super().__init__()
        self.path = path
        self.storage = storage
        self.extensions = extensions
        self.use_multiprocess = use_multiprocess
        self.use_incremental = use_incremental
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
            self.update_log.emit(f"多进程扫描：{'启用' if self.use_multiprocess else '禁用'}")
            self.update_log.emit(f"增量扫描：{'启用' if self.use_incremental else '禁用'}")
            
            # 确保存储文件目录存在
            storage_dir = os.path.dirname(self.storage)
            if storage_dir and not os.path.exists(storage_dir):
                os.makedirs(storage_dir, exist_ok=True)
            
            # 加载旧的哈希缓存 (用于增量扫描)
            old_file_hashes = {}
            old_call_graph = {}
            old_call_network = nx.DiGraph()
            
            if self.use_incremental and os.path.exists(self.storage):
                try:
                    self.update_log.emit("加载现有扫描数据用于增量扫描...")
                    loaded_data = load(self.storage)
                    if isinstance(loaded_data, dict):
                        old_file_hashes = loaded_data.get('file_hashes', {})
                        old_call_graph = loaded_data.get('whole_call_graph', {})
                        old_call_network = loaded_data.get('whole_call_network', nx.DiGraph())
                        self.update_log.emit(f"已加载 {len(old_file_hashes)} 个文件的哈希缓存")
                except Exception as e:
                    self.update_log.emit(f"加载缓存失败，将进行全量扫描: {str(e)}")
                    old_file_hashes = {}
            
            # 收集文件阶段
            self.update_log.emit("正在收集要扫描的文件...")
            whole_call_graph = old_call_graph.copy() if self.use_incremental else {}
            whole_call_network = old_call_network.copy() if self.use_incremental else nx.DiGraph()
            will_scan = []
            new_file_hashes = {}  # 新的哈希缓存
            skipped_by_incremental = 0  # 增量扫描跳过的文件数
            
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
                        
                        # 计算文件哈希用于增量扫描
                        file_hash = xxhash.xxh64(content).hexdigest()
                        file_mtime = os.path.getmtime(file_path)
                        relative_file_path = file_path[len(self.path):]
                        if not relative_file_path.startswith("/"):
                            relative_file_path = "/" + relative_file_path
                        
                        # 检查是否需要重新扫描
                        if self.use_incremental and relative_file_path in old_file_hashes:
                            old_hash, old_mtime = old_file_hashes[relative_file_path]
                            if old_hash == file_hash:
                                # 文件未修改,跳过扫描,复用旧数据
                                new_file_hashes[relative_file_path] = (file_hash, file_mtime)
                                skipped_by_incremental += 1
                                continue
                        
                        # 记录新哈希
                        new_file_hashes[relative_file_path] = (file_hash, file_mtime)
                        
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
            
            if self.use_incremental:
                self.update_log.emit(f"增量扫描：跳过 {skipped_by_incremental} 个未修改文件")
                self.update_log.emit(f"需要扫描：{len(will_scan)} 个新/修改文件")
            else:
                self.update_log.emit(f"将处理 {len(will_scan)} 个文件")
            
            # 发送进度信号:初始化进度
            total_files = len(will_scan)
            self.update_progress.emit(0, total_files)
            
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
            
            # 根据设置选择单进程或多进程
            if self.use_multiprocess and total_files > 5:  # 文件数少于5个时不值得用多进程
                self._scan_with_multiprocess(will_scan, whole_call_graph, whole_call_network, processed_files, total_files)
            else:
                self._scan_with_single_process(will_scan, whole_call_graph, whole_call_network, processed_files, total_files)
            
            # 保存扫描结果
            self.update_log.emit("\n正在保存扫描结果...")
            data = {
                'whole_call_graph': whole_call_graph,
                'whole_call_network': whole_call_network,
                'file_status': processed_files,
                'file_hashes': new_file_hashes  # 保存文件哈希用于下次增量扫描
            }
            dump(data, self.storage)
            
            # 显示处理结果统计
            status_counts = {}
            for status in processed_files.values():
                status_counts[status] = status_counts.get(status, 0) + 1
            
            self.update_log.emit("\n扫描结果统计：")
            if self.use_incremental:
                self.update_log.emit(f"- 增量扫描跳过：{skipped_by_incremental} 个文件")
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
    
    def _scan_with_single_process(self, will_scan, whole_call_graph, whole_call_network, processed_files, total_files):
        """单进程扫描"""
        self.update_log.emit(f"使用单进程模式扫描...")
        
        for i, (file_path, encoding) in enumerate(will_scan):
            if self.stopped:
                self.update_status.emit("扫描已中止")
                return
            
            # 更新进度信号 (每5个文件更新一次)
            if i % 5 == 0 or i == len(will_scan) - 1:
                self.update_progress.emit(i + 1, total_files)
            
            # 更新状态
            progress = int((i + 1) / total_files * 100)
            self.update_status.emit(f"正在扫描... {progress}% ({i + 1}/{total_files})")
            
            # 扫描并处理文件
            self._process_scan_result(
                file_path, encoding, self.path,
                whole_call_graph, whole_call_network, processed_files
            )
            
            # 每处理 20 个文件显示一次状态
            if (i + 1) % 20 == 0 or i == len(will_scan) - 1:
                self.update_log.emit(f"已处理：{i + 1}/{total_files} 个文件")
    
    def _scan_with_multiprocess(self, will_scan, whole_call_graph, whole_call_network, processed_files, total_files):
        """多进程扫描"""
        # 计算进程数
        cpu_count = multiprocessing.cpu_count()
        process_count = min(cpu_count, max(1, total_files // 10))
        self.update_log.emit(f"使用多进程模式扫描 (进程数: {process_count}, CPU核心数: {cpu_count})...")
        
        try:
            # 准备参数列表
            args_list = [(file_path, encoding, self.path) for file_path, encoding in will_scan]
            
            # 创建进程池
            with multiprocessing.Pool(processes=process_count) as pool:
                # 使用 imap_unordered 进行异步处理
                completed = 0
                for result in pool.imap_unordered(scan_file_wrapper, args_list, chunksize=max(1, total_files // (process_count * 4))):
                    if self.stopped:
                        pool.terminate()
                        self.update_status.emit("扫描已中止")
                        return
                    
                    # 解包结果
                    file_path, relative_file_path, call_graph, require, status, encoding = result
                    
                    # 处理结果
                    rel_path = os.path.relpath(file_path, self.path)
                    processed_files[rel_path] = status
                    
                    if status == "成功" and call_graph:
                        self._add_to_call_network(
                            relative_file_path, call_graph, require, file_path,
                            whole_call_graph, whole_call_network
                        )
                    
                    # 更新进度
                    completed += 1
                    if completed % 5 == 0 or completed == total_files:
                        self.update_progress.emit(completed, total_files)
                    
                    progress = int(completed / total_files * 100)
                    self.update_status.emit(f"正在扫描... {progress}% ({completed}/{total_files})")
                    
                    if completed % 20 == 0 or completed == total_files:
                        self.update_log.emit(f"已处理：{completed}/{total_files} 个文件")
                
        except Exception as e:
            self.update_log.emit(f"多进程扫描出错，切换到单进程模式: {str(e)}")
            # 回退到单进程模式
            self._scan_with_single_process(will_scan, whole_call_graph, whole_call_network, processed_files, total_files)
    
    def _process_scan_result(self, file_path, encoding, base_path, whole_call_graph, whole_call_network, processed_files):
        """处理单个文件的扫描结果 (单进程使用)"""
        rel_path = os.path.relpath(file_path, base_path)
        try:
            # 使用检测到的编码解析文件
            _, call_graph, require, status = scan_one_file(file_path, "json", False, encoding)
            
            # 记录处理状态
            processed_files[rel_path] = status
            
            # 如果文件成功解析并且有调用关系，则添加到调用图中
            if status == "成功" and call_graph:
                relative_file_path = file_path[len(base_path):]
                if not relative_file_path.startswith("/"):
                    relative_file_path = "/" + relative_file_path
                
                self._add_to_call_network(
                    relative_file_path, call_graph, require, file_path,
                    whole_call_graph, whole_call_network
                )
        except Exception as e:
            self.update_log.emit(f"解析 {rel_path} 时出错：{str(e)}")
            processed_files[rel_path] = f"解析错误：{str(e)}"
    
    def _add_to_call_network(self, relative_file_path, call_graph, require, file_path, whole_call_graph, whole_call_network):
        """将调用关系添加到网络图中"""
        import xxhash
        
        whole_call_graph[relative_file_path] = call_graph
        whole_call_network.add_node(relative_file_path, role='file')
        package_name = os.path.basename(file_path).replace(".lua", "")
        
        # 处理调用关系
        for tmp_name in call_graph.keys():
            if tmp_name == "[G]":
                default_main = f"{package_name}.main.{xxhash.xxh32(file_path.encode()).hexdigest()}"
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


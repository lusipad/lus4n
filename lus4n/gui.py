#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - Lua 调用图 GUI 界面
"""

import os
import sys
import uuid
import tempfile
import webbrowser
import networkx as nx
import time
from PySide6.QtCore import Qt, QSettings, QThread, Signal, QTimer, QEventLoop
from PySide6.QtGui import QIcon, QFont, QAction, QPixmap, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QFileDialog, QGroupBox, 
    QStatusBar, QTextEdit, QCheckBox, QComboBox, QMessageBox,
    QTabWidget, QSplitter, QFrame, QProgressBar
)
from joblib import dump, load
from pyvis.network import Network
from lus4n.graph import scan_path, scan_one_file


# -----------------------------------------------------
# 自定义进度条类 - 用于 GUI 中展示进度
# -----------------------------------------------------
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


# -----------------------------------------------------
# 扫描线程类 - 在后台执行扫描操作
# -----------------------------------------------------
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
            d = whole_call_graph
            g = whole_call_network
            self.scan_finished.emit((d, g))
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.update_log.emit(f"扫描过程中出现错误:\n{error_details}")
            self.update_status.emit("扫描出错")
            self.scan_error.emit(str(e))
    
    def stop(self):
        """安全停止线程"""
        self.stopped = True


# -----------------------------------------------------
# 主 GUI 应用类
# -----------------------------------------------------
class Lus4nGUI(QMainWindow):
    """Lus4n GUI 主类"""
    def __init__(self):
        super().__init__()
        # 初始化属性
        self.settings = QSettings("Lusipad", "Lus4n")
        self.temp_dir = tempfile.gettempdir()
        self.scan_thread = None
        self.scanning = False
        
        # 设置默认存储路径为程序所在目录
        self.default_storage_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "lus4n_result.jb")
        
        # 初始化 UI 和加载设置
        self.initUI()
        self.loadSettings()
        
    # ---- UI 初始化 ----
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
        tabs = QTabWidget()
        tabs.setDocumentMode(True)  # 更现代的选项卡样式
        main_layout.addWidget(tabs)
        
        # === 扫描选项卡 ===
        scan_tab = QWidget()
        tabs.addTab(scan_tab, "扫描 Lua 代码")
        scan_layout = QVBoxLayout(scan_tab)
        
        # 路径选择区域
        path_group = QGroupBox("代码路径")
        path_layout = QHBoxLayout(path_group)
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("选择要扫描的 Lua 代码路径")
        path_browse_btn = QPushButton("浏览...")
        path_browse_btn.clicked.connect(self.browse_path)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(path_browse_btn)
        scan_layout.addWidget(path_group)
        
        # 存储文件区域
        storage_group = QGroupBox("存储文件")
        storage_layout = QHBoxLayout(storage_group)
        self.storage_input = QLineEdit()
        self.storage_input.setPlaceholderText("选择调用图数据存储文件路径 (可选)")
        storage_browse_btn = QPushButton("浏览...")
        storage_browse_btn.clicked.connect(self.browse_storage)
        storage_layout.addWidget(self.storage_input)
        storage_layout.addWidget(storage_browse_btn)
        scan_layout.addWidget(storage_group)
        
        # 文件后缀区域
        extensions_group = QGroupBox("文件后缀")
        extensions_layout = QVBoxLayout(extensions_group)
        extensions_help = QLabel("指定要扫描的文件后缀，多个后缀用逗号分隔")
        self.extensions_input = QLineEdit(".lua")
        extensions_layout.addWidget(extensions_help)
        extensions_layout.addWidget(self.extensions_input)
        scan_layout.addWidget(extensions_group)
        
        # 扫描按钮
        scan_btn = QPushButton("开始扫描")
        scan_btn.setMinimumHeight(40)
        scan_btn.setObjectName("primaryButton")
        scan_btn.clicked.connect(self.start_scan)
        scan_layout.addWidget(scan_btn)
        
        # 日志区域
        log_group = QGroupBox("扫描日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("color: #333333;")  # 使用深灰色文本
        log_layout.addWidget(self.log_text)
        scan_layout.addWidget(log_group)
        
        # === 查询选项卡 ===
        query_tab = QWidget()
        tabs.addTab(query_tab, "查询调用关系")
        query_layout = QVBoxLayout(query_tab)
        
        # 存储文件选择区域
        query_storage_group = QGroupBox("存储文件")
        query_storage_layout = QHBoxLayout(query_storage_group)
        self.query_storage_input = QLineEdit()
        self.query_storage_input.setPlaceholderText("选择调用图数据存储文件路径")
        query_storage_browse_btn = QPushButton("浏览...")
        query_storage_browse_btn.clicked.connect(self.browse_query_storage)
        query_storage_layout.addWidget(self.query_storage_input)
        query_storage_layout.addWidget(query_storage_browse_btn)
        query_layout.addWidget(query_storage_group)
        
        # 函数查询区域
        function_group = QGroupBox("函数查询")
        function_layout = QHBoxLayout(function_group)
        self.function_input = QLineEdit()
        self.function_input.setPlaceholderText("输入要查询的函数名（例如：os.execute）")
        query_btn = QPushButton("查询")
        query_btn.setObjectName("primaryButton")
        query_btn.clicked.connect(self.query_function)
        function_layout.addWidget(self.function_input)
        function_layout.addWidget(query_btn)
        query_layout.addWidget(function_group)
        
        # 最近查询记录
        recent_group = QGroupBox("最近查询")
        recent_layout = QVBoxLayout(recent_group)
        self.recent_combo = QComboBox()
        self.recent_combo.setEditable(False)
        self.recent_combo.currentTextChanged.connect(self.on_recent_selected)
        recent_layout.addWidget(self.recent_combo)
        query_layout.addWidget(recent_group)
        
        # 查询结果区域
        result_group = QGroupBox("查询结果")
        result_layout = QVBoxLayout(result_group)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)
        query_layout.addWidget(result_group)
        
        # 状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.statusBar.addPermanentWidget(self.progress_bar)
    
    # ---- 设置管理 ----
    def loadSettings(self):
        """加载应用设置"""
        # 加载最近使用的路径
        last_path = self.settings.value("last_path", "")
        if last_path:
            self.path_input.setText(last_path)
            
        last_storage = self.settings.value("last_storage", "")
        if last_storage and os.path.exists(last_storage):
            self.storage_input.setText(last_storage)
            self.query_storage_input.setText(last_storage)
        else:
            # 如果没有上次存储的路径或文件不存在，则使用默认路径
            self.storage_input.setText(self.default_storage_path)
            self.query_storage_input.setText(self.default_storage_path)
            
        # 加载最近的查询
        recent_queries = self.settings.value("recent_queries", [])
        if recent_queries:
            self.recent_combo.addItems(recent_queries)
    
    def saveSettings(self):
        """保存应用设置"""
        # 保存最近使用的路径
        self.settings.setValue("last_path", self.path_input.text())
        self.settings.setValue("last_storage", self.storage_input.text())
        
        # 保存最近的查询
        recent_queries = [self.recent_combo.itemText(i) for i in range(self.recent_combo.count())]
        self.settings.setValue("recent_queries", recent_queries)
    
    # ---- UI 操作处理 ----
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
    
    def browse_query_storage(self):
        """浏览并选择查询存储文件路径"""
        path, _ = QFileDialog.getOpenFileName(self, "选择存储文件路径", "", "Joblib Files (*.jb)")
        if path:
            self.query_storage_input.setText(path)
    
    def log(self, message):
        """向日志区域添加消息"""
        self.log_text.append(message)
        self.log_text.moveCursor(self.log_text.textCursor().End)
        self.log_text.ensureCursorVisible()
        
        # 立即处理界面更新
        QApplication.processEvents()
        
    def update_status(self, message):
        """更新状态栏消息"""
        self.statusBar.showMessage(message)
        
        # 如果是"扫描完成"状态，则隐藏进度条
        if message == "扫描完成" or message == "扫描出错" or message == "扫描已中止":
            self.progress_bar.setVisible(False)
            self.scanning = False
            # 强制重绘
            self.repaint()
            # 再次处理事件以确保状态更新
            QApplication.processEvents()
    
    # ---- 扫描相关方法 ----
    def start_scan(self):
        """开始扫描操作"""
        # 如果已经有一个扫描线程在运行，则返回
        if self.scanning:
            QMessageBox.information(self, "正在扫描", "已经有一个扫描任务正在进行中")
            return

        path = self.path_input.text()
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "路径错误", "请选择有效的 Lua 代码路径")
            return
        
        storage = self.storage_input.text()
        if not storage:
            storage = self.default_storage_path
            self.storage_input.setText(storage)
        
        extensions = [ext.strip() for ext in self.extensions_input.text().split(",")]
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # 不确定进度模式
        self.statusBar.showMessage("正在扫描...")
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
        self.scan_thread = ScanThread(path, storage, extensions)
        
        # 连接信号
        self.scan_thread.update_log.connect(self.log)
        self.scan_thread.update_status.connect(self.update_status)
        self.scan_thread.scan_finished.connect(self.on_scan_finished)
        self.scan_thread.scan_error.connect(self.on_scan_error)
        
        # 启动线程
        self.scan_thread.start()
    
    def on_scan_finished(self, result):
        """扫描完成的回调处理"""
        d, g = result
        
        # 更新界面
        self.log(f"扫描完成！发现 {len(d)} 个文件，{len(g.nodes)} 个节点")
        self.query_storage_input.setText(self.storage_input.text())
        
        # 显示完成消息
        QMessageBox.information(self, "扫描完成", f"扫描完成！\n发现 {len(d)} 个文件，{len(g.nodes)} 个节点\n结果已保存到：{self.storage_input.text()}")
        
        # 保存设置
        self.saveSettings()
    
    def on_scan_error(self, error_msg):
        """扫描出错的回调处理"""
        # 记录错误
        self.log(f"扫描出错：{error_msg}")
        
        # 显示错误消息
        QMessageBox.critical(self, "扫描错误", f"扫描过程中发生错误：{error_msg}")
    
    # ---- 查询相关方法 ----
    def on_recent_selected(self, text):
        """从最近查询中选择一个"""
        if text:
            self.function_input.setText(text)
    
    def add_recent_query(self, query):
        """添加一个查询到最近查询列表"""
        # 检查是否已存在
        found = self.recent_combo.findText(query)
        if found != -1:
            self.recent_combo.removeItem(found)
        
        # 添加到顶部
        self.recent_combo.insertItem(0, query)
        self.recent_combo.setCurrentIndex(0)
        
        # 限制最大数量为 10
        while self.recent_combo.count() > 10:
            self.recent_combo.removeItem(self.recent_combo.count() - 1)
        
        # 保存设置
        self.saveSettings()
    
    def query_function(self):
        """查询函数调用关系"""
        storage = self.query_storage_input.text()
        if not storage or not os.path.exists(storage):
            QMessageBox.warning(self, "文件错误", "请选择有效的存储文件")
            return
        
        query = self.function_input.text()
        if not query:
            QMessageBox.warning(self, "查询错误", "请输入要查询的函数名")
            return
        
        try:
            self.statusBar.showMessage(f"正在查询 {query}...")
            self.result_text.clear()
            
            # 加载图
            g = load(storage)
            
            if query in g.nodes:
                # 记录查询历史
                self.add_recent_query(query)
                
                # 查找所有祖先节点
                nodes = nx.ancestors(g, query)
                file_node_list = []
                func_node_list = []
                
                for node in nodes:
                    if "role" in g.nodes[node] and g.nodes[node]["role"] == "file":
                        file_node_list.append(node)
                    else:
                        func_node_list.append(node)
                
                if query not in nodes:
                    nodes.add(query)
                
                # 创建子图
                sg = g.subgraph(nodes)
                
                # 生成可视化
                net = Network(notebook=True)
                net.add_node(query)
                net.from_nx(sg)
                
                # 保存并显示
                show_path = os.path.join(self.temp_dir, f"{uuid.uuid4()}.html")
                net.show(show_path)
                
                # 结果信息
                self.result_text.append(f"查询函数：{query}")
                self.result_text.append(f"相关函数数量：{len(func_node_list)}")
                self.result_text.append(f"相关文件数量：{len(file_node_list)}")
                self.result_text.append("\n--- 相关函数 ---")
                for func in func_node_list:
                    self.result_text.append(func)
                
                self.result_text.append("\n--- 相关文件 ---")
                for file in file_node_list:
                    self.result_text.append(file)
                
                # 打开浏览器显示
                webbrowser.open_new_tab(f"file://{show_path}")
                self.statusBar.showMessage(f"已显示 {query} 的调用关系")
            else:
                self.result_text.append(f"未找到节点：{query}")
                self.statusBar.showMessage(f"未找到节点：{query}")
        
        except Exception as e:
            self.result_text.append(f"查询出错：{str(e)}")
            self.statusBar.showMessage("查询出错")
            QMessageBox.critical(self, "查询错误", f"查询过程中发生错误：{str(e)}")
    
    # ---- 窗口事件处理 ----
    def closeEvent(self, event):
        """关闭窗口事件处理"""
        # 检查是否有扫描线程在运行
        if self.scanning:
            # 询问用户是否终止线程
            reply = QMessageBox.question(self, "确认退出", 
                                         "扫描任务正在进行中，确定要退出吗？", 
                                         QMessageBox.Yes | QMessageBox.No, 
                                         QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # 停止扫描
                if self.scan_thread:
                    self.scan_thread.stop()
                    self.scan_thread.terminate()
                    self.scan_thread.wait()
            else:
                event.ignore()
                return
        
        # 保存设置
        self.saveSettings()
        event.accept()


# -----------------------------------------------------
# 主函数 - 应用入口
# -----------------------------------------------------
def main():
    """应用主入口函数"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用 Fusion 风格，在所有平台上看起来都很现代
    
    # 设置应用字体
    font = QFont("Microsoft YaHei UI", 9)  # 使用微软雅黑
    app.setFont(font)
    
    # 设置样式表使界面更现代美观，参考火绒应用商店的风格
    app.setStyleSheet("""
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
    """)
    
    window = Lus4nGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lus4n - 查询选项卡模块
用于查询函数调用关系并可视化显示
"""

import os
import tempfile
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser,
    QMessageBox, QSplitter, QGroupBox, QLabel, QLineEdit, QPushButton
)
from PySide6.QtCore import Qt

from lus4n.ui.graph_analyzer import GraphAnalyzer
from lus4n.ui.graph_visualizer import GraphVisualizer
from lus4n.ui.webview_window import WebViewWindow
from lus4n.ui.ui_components import (
    StorageSelector,
    VisualizationSettings,
    FunctionQueryInput,
)


class QueryTab(QWidget):
    """查询选项卡类，负责查询函数调用关系并可视化显示"""
    
    def __init__(self, parent=None, status_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.status_callback = status_callback
        self.temp_dir = tempfile.gettempdir()
        
        # 初始化分析器和可视化器
        self.analyzer = GraphAnalyzer()
        self.visualizer = GraphVisualizer()
        
        # 初始化 WebView 窗口
        self.webview_window = None
        
        # 设置数据
        self.settings = QSettings("Lusipad", "Lus4n")
        self.last_html_path = None
        
        # 初始化 UI
        self.init_ui()
        
        # 加载上次使用的存储路径
        last_storage = self.settings.value("last_storage_path", "")
        if last_storage and os.path.exists(last_storage):
            self.storage_selector.set_storage_path(last_storage)
            
    def init_ui(self):
        """初始化查询选项卡 UI"""
        main_layout = QVBoxLayout(self)
        
        # 创建存储选择器
        self.storage_selector = StorageSelector(self)
        main_layout.addWidget(self.storage_selector.get_widget())
        
        # 创建查询输入组件
        self.function_query = FunctionQueryInput(
            self,
            on_query=self.query_function,
            on_list_all=self.list_all_function_entries,
            on_show_all=self.show_all_function_relations
        )
        main_layout.addWidget(self.function_query.get_widget())
        
        # 创建可视化设置组件
        self.vis_settings = VisualizationSettings(self)
        main_layout.addWidget(self.vis_settings.get_widget())
        
        # 创建路径分析组件
        path_group = QGroupBox("调用路径分析")
        path_layout = QHBoxLayout(path_group)
        
        path_layout.addWidget(QLabel("起始函数:"))
        self.source_function_input = QLineEdit()
        self.source_function_input.setPlaceholderText("例如: main")
        path_layout.addWidget(self.source_function_input)
        
        path_layout.addWidget(QLabel("目标函数:"))
        self.target_function_input = QLineEdit()
        self.target_function_input.setPlaceholderText("例如: os.execute")
        path_layout.addWidget(self.target_function_input)
        
        analyze_path_btn = QPushButton("分析路径")
        analyze_path_btn.clicked.connect(self.analyze_call_path)
        path_layout.addWidget(analyze_path_btn)
        
        analyze_hotspot_btn = QPushButton("热点函数分析")
        analyze_hotspot_btn.clicked.connect(self.analyze_hotspot_functions)
        path_layout.addWidget(analyze_hotspot_btn)
        
        main_layout.addWidget(path_group)
        
        # 创建分割窗口
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)
        
        # 创建结果显示区域
        self.result_browser = QTextBrowser()
        # 设置为不自动打开链接，而是触发 anchorClicked 信号
        self.result_browser.setOpenLinks(False)
        self.result_browser.anchorClicked.connect(self._handle_anchor_clicked)
        self.result_browser.setStyleSheet("QTextBrowser { background-color: #f8f9fa; }")
        
        splitter.addWidget(self.result_browser)
        
        # 创建 WebView 显示区域 (如果可用)
        if WebViewWindow.is_available():
            self.webview_window = WebViewWindow(self)
            splitter.addWidget(self.webview_window)
            splitter.setSizes([200, 600])  # 给 WebView 更多空间
        else:
            splitter.setSizes([400, 200])
        
        main_layout.addWidget(splitter)
    
    def _update_status(self, message):
        """更新状态栏消息"""
        if self.status_callback:
            self.status_callback(message)
    
    def _save_settings(self):
        """保存设置"""
        # 保存存储路径
        storage_path = self.storage_selector.get_storage_path()
        if storage_path:
            self.settings.setValue("last_storage_path", storage_path)
        
    def set_storage_path(self, path):
        """设置存储文件路径
        
        这个方法被主窗口调用，用于设置存储文件路径
        """
        if hasattr(self, 'storage_selector'):
            self.storage_selector.set_storage_path(path)
    
    def set_recent_queries(self, queries):
        """设置最近查询列表
        
        这个方法被主窗口调用，用于设置最近查询列表
        """
        if hasattr(self, 'function_query') and queries:
            self.function_query.update_completer_items(queries)
    
    def get_recent_queries(self):
        """获取最近查询列表
        
        这个方法被主窗口调用，用于获取最近查询列表
        """
        # 由于使用自动完成，不再需要单独获取最近查询
        return []
    
    def query_function(self):
        """查询函数调用关系"""
        function_name = self.function_query.get_function_name().strip()
        storage_path = self.storage_selector.get_storage_path()
        query_mode = self.function_query.get_query_mode()  # 0=调用者, 1=被调用者, 2=双向
        
        if not function_name:
            QMessageBox.warning(self, "请输入函数名", "请输入函数名！")
            return
            
        if not storage_path or not os.path.exists(storage_path):
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("存储路径错误")
            msgBox.setText("请指定一个有效的存储路径")
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.setStyleSheet("QLabel{min-width: 300px; color: black;}")
            msgBox.exec_()
            return
        
        try:
            mode_text = ["调用者", "被调用者", "双向关系"][query_mode]
            self._update_status(f"正在查询函数：{function_name} ({mode_text})...")
            
            # 加载图数据
            graph = self.analyzer.load_graph(storage_path)
            
            # 检查函数是否存在
            if function_name not in graph.nodes:
                self.result_browser.setHtml(
                    f"<h3>函数不存在</h3>"
                    f"<p>函数 '{function_name}' 在扫描的代码中不存在。请检查函数名是否正确或是否已扫描代码。</p>"
                )
                return
            
            # 根据查询模式获取相关节点
            if query_mode == 0:  # 调用者(祖先)
                filtered_nodes_set = self.analyzer.get_function_ancestors(function_name)
                ancestors_set = filtered_nodes_set - {function_name}
                descendants_set = set()
            elif query_mode == 1:  # 被调用者(后代)
                filtered_nodes_set = self.analyzer.get_function_descendants(function_name)
                ancestors_set = set()
                descendants_set = filtered_nodes_set - {function_name}
            else:  # 双向关系
                filtered_nodes_set, ancestors_set, descendants_set = self.analyzer.get_function_bidirectional(function_name)
            
            # 根据设置筛选节点
            show_files = self.vis_settings.show_file_nodes()
            filtered_nodes = self.analyzer.filter_nodes_by_type(filtered_nodes_set, show_files)
            
            # 根据最大节点数筛选
            max_nodes = self.vis_settings.get_max_nodes()
            filtered_nodes = self.analyzer.filter_nodes_by_importance(
                filtered_nodes, max_nodes, {function_name}
            )
            
            # 渲染可视化
            layout = self.vis_settings.get_layout_option()
            show_physics = self.vis_settings.use_physics()
            size_by_importance = self.vis_settings.size_by_importance()
            
            self._update_status("正在生成可视化...")
            
            html_path, net = self.visualizer.render_graph(
                graph, filtered_nodes, 
                query_node=function_name,
                show_physics=show_physics, 
                size_by_importance=size_by_importance,
                layout=layout,
                ancestors=ancestors_set,
                descendants=descendants_set
            )
            
            # 分离函数节点和文件节点
            function_nodes, file_nodes = self.analyzer.separate_nodes_by_type(filtered_nodes)
            
            # 显示结果
            result_html = f"""
            <h3>函数：{function_name} ({mode_text})</h3>
            <p>显示与 <b>{function_name}</b> 相关的调用关系。</p>
            <ul>
                <li>查询模式：{mode_text}</li>
                <li>函数数量：{len(function_nodes)}</li>
                <li>文件数量：{len(file_nodes)}</li>
                <li>总节点数：{len(filtered_nodes)}</li>
                <li>关系边数：{net.num_edges}</li>
            """
            
            if query_mode == 2:  # 双向关系时显示统计
                result_html += f"""
                <li>调用者数量：{len(ancestors_set)}</li>
                <li>被调用者数量：{len(descendants_set)}</li>
            """
            
            result_html += """
            </ul>
            <p><a href='file://{html_path}' target='_blank'>在浏览器中打开可视化</a></p>
            """
            
            self.result_browser.setHtml(result_html)
            
            # 在 WebView 中显示 (如果可用),否则在浏览器中打开
            if self.webview_window:
                self.webview_window.load_html(html_path)
            else:
                self.visualizer.display_graph(html_path)
            
            self.last_html_path = html_path
            
            self._update_status("查询完成")
            
        except Exception as e:
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("查询错误")
            msgBox.setText(f"查询函数 '{function_name}' 时发生错误：\n\n{str(e)}")
            msgBox.setIcon(QMessageBox.Critical)
            msgBox.setStyleSheet("QLabel{min-width: 400px; color: black;}")
            msgBox.exec_()
            self._update_status("查询失败")
    
    def list_all_function_entries(self):
        """列出所有函数入口点"""
        storage_path = self.storage_selector.get_storage_path()
        
        if not storage_path or not os.path.exists(storage_path):
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("存储路径错误")
            msgBox.setText("请指定一个有效的存储路径")
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.setStyleSheet("QLabel{min-width: 300px; color: black;}")
            msgBox.exec_()
            return
        
        try:
            self._update_status("正在加载并分析函数入口点...")
            
            # 加载图数据
            self.analyzer.load_graph(storage_path)
            
            # 获取函数入口点及调用次数和文件路径
            entries = self.analyzer.get_all_function_entries()
            
            if not entries:
                self.result_browser.setHtml(
                    "<h3>未找到函数</h3>"
                    "<p>在扫描的代码中没有找到任何函数。</p>"
                    "<p>这可能是因为：</p>"
                    "<ul>"
                    "<li>代码中没有定义任何函数</li>"
                    "<li>解析过程中出现了问题</li>"
                    "</ul>"
                )
                self._update_status("未找到函数")
                return
            
            # entries 已经是按调用次数降序排序的列表，不需要再次排序
            sorted_entries = entries
            
            # 生成 HTML 表格显示结果
            html = f"""
            <h3>函数列表</h3>
            <p>共找到 {len(sorted_entries)} 个函数，按被调用次数降序排列：</p>
            <style>
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    font-family: Arial, sans-serif;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                tr:hover {{
                    background-color: #e9e9e9;
                }}
                a {{
                    color: #0066cc;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
            </style>
            <table>
                <tr>
                    <th>函数名</th>
                    <th>被调用次数</th>
                    <th>所在文件</th>
                </tr>
            """
            
            for func_name, call_count in sorted_entries:
                # 获取函数所在的文件
                file_path = "未知"
                try:
                    for source, _, data in self.analyzer.graph.in_edges(func_name, data=True):
                        if data.get('action') in ['export', 'define']:
                            file_path = source
                            break
                except Exception:
                    # 如果获取文件路径时出错，使用默认值
                    pass
                
                # 提取文件名（不显示完整路径）
                try:
                    file_name = os.path.basename(file_path) if file_path and isinstance(file_path, str) else "未知"
                except Exception:
                    file_name = "未知"
                
                html += f"""
                <tr>
                    <td><a href="function:{func_name}">{func_name}</a></td>
                    <td>{call_count}</td>
                    <td>{file_name}</td>
                </tr>
                """
            
            html += """
            </table>
            <p>点击函数名可以查看该函数的调用关系。</p>
            """
            
            self.result_browser.setHtml(html)
            self._update_status(f"显示了 {len(sorted_entries)} 个函数")
            
        except Exception as e:
            self.result_browser.setHtml(
                f"<h3>列出错误</h3>"
                f"<p>列出函数时发生错误：{str(e)}</p>"
            )
            self._update_status("列出失败")
            
    def _handle_anchor_clicked(self, url):
        """处理链接点击事件"""
        scheme = url.scheme()
        if scheme == "function":
            function_name = url.toString().replace("function:", "")
            self.function_query.set_function_name(function_name)
            # 自动触发查询
            self.query_function()
            
    def show_all_function_relations(self):
        """显示所有函数关系"""
        storage_path = self.storage_selector.get_storage_path()
        
        if not storage_path or not os.path.exists(storage_path):
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("存储路径错误")
            msgBox.setText("请指定一个有效的存储路径")
            msgBox.setIcon(QMessageBox.Warning)
            msgBox.setStyleSheet("QLabel{min-width: 300px; color: black;}")
            msgBox.exec_()
            return
        
        try:
            self._update_status("正在分析所有函数关系...")
            
            # 加载图数据
            graph = self.analyzer.load_graph(storage_path)
            
            # 获取所有节点
            all_nodes = self.analyzer.get_all_nodes()
            
            # 根据设置筛选节点
            show_files = self.vis_settings.show_file_nodes()
            filtered_nodes = self.analyzer.filter_nodes_by_type(all_nodes, show_files)
            
            # 根据最大节点数筛选
            max_nodes = self.vis_settings.get_max_nodes()
            filtered_nodes = self.analyzer.filter_nodes_by_importance(
                filtered_nodes, max_nodes
            )
            
            # 渲染可视化
            layout = self.vis_settings.get_layout_option()
            show_physics = self.vis_settings.use_physics()
            size_by_importance = self.vis_settings.size_by_importance()
            
            self._update_status("正在生成可视化...")
            
            html_path, net = self.visualizer.render_graph(
                graph, filtered_nodes, 
                show_physics=show_physics, 
                size_by_importance=size_by_importance,
                layout=layout
            )
            
            # 分离函数节点和文件节点
            function_nodes, file_nodes = self.analyzer.separate_nodes_by_type(filtered_nodes)
            
            # 显示结果
            result_html = f"""
            <h3>所有函数关系</h3>
            <p>显示代码中所有函数的调用关系。</p>
            <ul>
                <li>函数数量：{len(function_nodes)}</li>
                <li>文件数量：{len(file_nodes)}</li>
                <li>总节点数：{len(filtered_nodes)}</li>
                <li>关系边数：{net.num_edges}</li>
            </ul>
            <p><a href='file://{html_path}' target='_blank'>在浏览器中打开可视化</a></p>
            <p>说明：节点大小和颜色深浅表示函数的重要性（被调用次数）。</p>
            """
            
            self.result_browser.setHtml(result_html)
            
            # 在 WebView 中显示 (如果可用),否则在浏览器中打开
            if self.webview_window:
                self.webview_window.load_html(html_path)
            else:
                self.visualizer.display_graph(html_path)
            
            self.last_html_path = html_path
            
            self._update_status("显示完成")
            
        except Exception as e:
            self.result_browser.setHtml(
                f"<h3>显示错误</h3>"
                f"<p>显示所有函数关系时发生错误：{str(e)}</p>"
            )
            self._update_status("显示失败")
    
    def analyze_call_path(self):
        """分析调用路径"""
        source = self.source_function_input.text().strip()
        target = self.target_function_input.text().strip()
        storage_path = self.storage_selector.get_storage_path()
        
        if not source or not target:
            QMessageBox.warning(self, "输入错误", "请输入起始函数和目标函数！")
            return
        
        if not storage_path or not os.path.exists(storage_path):
            QMessageBox.warning(self, "存储路径错误", "请指定一个有效的存储路径")
            return
        
        try:
            self._update_status(f"正在分析从 {source} 到 {target} 的路径...")
            
            # 加载图数据
            self.analyzer.load_graph(storage_path)
            
            # 查找所有路径
            paths = self.analyzer.find_call_paths(source, target, max_depth=10, max_paths=100)
            
            if not paths:
                self.result_browser.setHtml(
                    f"<h3>未找到路径</h3>"
                    f"<p>从 <b>{source}</b> 到 <b>{target}</b> 不存在调用路径。</p>"
                    f"<p>可能的原因：</p>"
                    f"<ul><li>两个函数之间没有直接或间接的调用关系</li>"
                    f"<li>路径深度超过了限制(当前限制为10层)</li></ul>"
                )
                self._update_status("未找到路径")
                return
            
            # 查找最短路径
            shortest_path = self.analyzer.find_shortest_call_path(source, target)
            
            # 显示结果
            html = f"""
            <h3>调用路径分析</h3>
            <p>从 <b>{source}</b> 到 <b>{target}</b> 找到 {len(paths)} 条路径</p>
            
            <h4>最短路径 (长度: {len(shortest_path) - 1})</h4>
            <p style='font-family: monospace; background: #f0f0f0; padding: 10px;'>
            {' → '.join(shortest_path)}
            </p>
            
            <h4>所有路径</h4>
            <ol>
            """
            
            for i, path in enumerate(paths[:50], 1):  # 只显示前50条
                path_str = ' → '.join(path)
                html += f"<li style='margin: 5px 0;'><code>{path_str}</code></li>"
            
            if len(paths) > 50:
                html += f"<li>... 还有 {len(paths) - 50} 条路径未显示</li>"
            
            html += "</ol>"
            
            self.result_browser.setHtml(html)
            self._update_status("路径分析完成")
            
        except ValueError as e:
            self.result_browser.setHtml(
                f"<h3>分析错误</h3>"
                f"<p>{str(e)}</p>"
            )
            self._update_status("分析失败")
        except Exception as e:
            self.result_browser.setHtml(
                f"<h3>分析错误</h3>"
                f"<p>分析路径时发生错误：{str(e)}</p>"
            )
            self._update_status("分析失败")
    
    def analyze_hotspot_functions(self):
        """分析热点函数"""
        storage_path = self.storage_selector.get_storage_path()
        
        if not storage_path or not os.path.exists(storage_path):
            QMessageBox.warning(self, "存储路径错误", "请指定一个有效的存储路径")
            return
        
        try:
            self._update_status("正在分析热点函数...")
            
            # 加载图数据
            self.analyzer.load_graph(storage_path)
            
            # 获取热点函数
            hotspots = self.analyzer.get_hotspot_functions(top_n=50)
            
            if not hotspots:
                self.result_browser.setHtml(
                    "<h3>未找到热点函数</h3>"
                    "<p>在扫描的代码中没有找到任何被调用的函数。</p>"
                )
                self._update_status("未找到热点函数")
                return
            
            # 显示结果
            html = f"""
            <h3>热点函数分析</h3>
            <p>找到 {len(hotspots)} 个热点函数（按被调用次数降序排列）</p>
            <style>
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    font-family: Arial, sans-serif;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                    font-weight: bold;
                }}
                tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                tr:hover {{
                    background-color: #e9e9e9;
                }}
                a {{
                    color: #0066cc;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                .hot {{ background-color: #ffebee; }}
                .warm {{ background-color: #fff9c4; }}
            </style>
            <table>
                <tr>
                    <th>排名</th>
                    <th>函数名</th>
                    <th>被调用次数</th>
                    <th>调用其他函数次数</th>
                </tr>
            """
            
            for i, (func_name, in_degree, out_degree) in enumerate(hotspots, 1):
                row_class = "hot" if in_degree > 10 else ("warm" if in_degree > 5 else "")
                html += f"""
                <tr class='{row_class}'>
                    <td>{i}</td>
                    <td><a href="function:{func_name}">{func_name}</a></td>
                    <td>{in_degree}</td>
                    <td>{out_degree}</td>
                </tr>
                """
            
            html += """
            </table>
            <p>说明：点击函数名可以查看该函数的调用关系图。</p>
            <p>颜色说明：<span style='background:#ffebee;padding:3px;'>红色=高频(>10次)</span> 
            <span style='background:#fff9c4;padding:3px;'>黄色=中频(>5次)</span></p>
            """
            
            self.result_browser.setHtml(html)
            self._update_status("热点分析完成")
            
        except Exception as e:
            self.result_browser.setHtml(
                f"<h3>分析错误</h3>"
                f"<p>分析热点函数时发生错误：{str(e)}</p>"
            )
            self._update_status("分析失败")

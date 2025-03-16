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
    QMessageBox, QSplitter
)
from PySide6.QtCore import Qt

from lus4n.ui.graph_analyzer import GraphAnalyzer
from lus4n.ui.graph_visualizer import GraphVisualizer
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
        
        # 创建分割窗口
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)
        
        # 创建结果显示区域
        self.result_browser = QTextBrowser()
        self.result_browser.setOpenExternalLinks(True)
        self.result_browser.setStyleSheet("QTextBrowser { background-color: #f8f9fa; }")
        
        splitter.addWidget(self.result_browser)
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
            self._update_status(f"正在查询函数：{function_name}...")
            
            # 加载图数据
            graph = self.analyzer.load_graph(storage_path)
            
            # 检查函数是否存在
            if function_name not in graph.nodes:
                self.result_browser.setHtml(
                    f"<h3>函数不存在</h3>"
                    f"<p>函数 '{function_name}' 在扫描的代码中不存在。请检查函数名是否正确或是否已扫描代码。</p>"
                )
                return
            
            # 获取所有调用该函数的节点（祖先节点）
            ancestors = self.analyzer.get_function_ancestors(function_name)
            
            # 根据设置筛选节点
            show_files = self.vis_settings.show_file_nodes()
            filtered_nodes = self.analyzer.filter_nodes_by_type(ancestors, show_files)
            
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
                layout=layout
            )
            
            # 分离函数节点和文件节点
            function_nodes, file_nodes = self.analyzer.separate_nodes_by_type(filtered_nodes)
            
            # 显示结果
            result_html = f"""
            <h3>函数：{function_name}</h3>
            <p>显示与 <b>{function_name}</b> 相关的调用关系。</p>
            <ul>
                <li>函数数量：{len(function_nodes)}</li>
                <li>文件数量：{len(file_nodes)}</li>
                <li>总节点数：{len(filtered_nodes)}</li>
                <li>关系边数：{net.num_edges}</li>
            </ul>
            <p><a href='file://{html_path}' target='_blank'>在浏览器中打开可视化</a></p>
            """
            
            self.result_browser.setHtml(result_html)
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
            
            # 获取函数入口点
            entries = self.analyzer.get_function_entries()
            
            if not entries:
                self.result_browser.setHtml(
                    "<h3>未找到函数入口点</h3>"
                    "<p>在扫描的代码中没有找到任何函数入口点。</p>"
                    "<p>这可能是因为：</p>"
                    "<ul>"
                    "<li>代码中没有定义任何函数</li>"
                    "<li>所有函数都被其他函数调用（没有顶层入口）</li>"
                    "<li>解析过程中出现了问题</li>"
                    "</ul>"
                )
                self._update_status("未找到函数入口点")
                return
            
            # 按名称排序
            entries.sort()
            
            # 生成HTML显示结果
            html = f"""
            <h3>函数入口点列表</h3>
            <p>共找到 {len(entries)} 个函数入口点（未被其他函数调用的函数）：</p>
            <ul>
            """
            
            for entry in entries:
                html += f"<li><a href='function:{entry}'>{entry}</a></li>"
            
            html += """
            </ul>
            <p>点击函数名可以查看该函数的调用关系。</p>
            """
            
            self.result_browser.setHtml(html)
            self._update_status(f"显示了 {len(entries)} 个函数入口点")
            
        except Exception as e:
            self.result_browser.setHtml(
                f"<h3>列出错误</h3>"
                f"<p>列出函数入口点时发生错误：{str(e)}</p>"
            )
            self._update_status("列出失败")
    
    def _handle_anchor_clicked(self, url):
        """处理链接点击事件"""
        scheme = url.scheme()
        if scheme == "function":
            function_name = url.path()
            self.function_query.set_function_name(function_name)
            # 可选：自动触发查询
            # self.query_function()
            
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
            self.visualizer.display_graph(html_path)
            self.last_html_path = html_path
            
            self._update_status("显示完成")
            
        except Exception as e:
            self.result_browser.setHtml(
                f"<h3>显示错误</h3>"
                f"<p>显示所有函数关系时发生错误：{str(e)}</p>"
            )
            self._update_status("显示失败")

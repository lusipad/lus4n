import os
import json
import xxhash
import networkx as nx

from tqdm import tqdm
from loguru import logger
from luaparser import ast
from luaparser.astnodes import *
from luaparser.utils.visitor import *
from luaparser.printers import PythonStyleVisitor
from luaparser.ast import SyntaxException


def scan_one_file(file_path: str, _format="json", _debug=False, encoding=None):
    if not os.path.exists(file_path):
        logger.warning(f"文件不存在：{file_path}")
        return file_path, {}, [], "文件不存在"
    
    # 尝试不同的编码方式
    encodings = [encoding] if encoding else ['utf-8', 'gb2312', 'gbk', 'latin-1']
    source = None
    
    try:
        # 首先尝试二进制方式读取
        with open(file_path, "rb") as f:
            raw_data = f.read()
            
        # 处理 BOM（字节顺序标记）
        if raw_data.startswith(b'\xef\xbb\xbf'):  # UTF-8-BOM
            raw_data = raw_data[3:]
            
        # 只检查是否为 Lua 字节码，不是字节码就当作文本处理
        if raw_data.startswith(b"\x1bL"):
            logger.warning(f"[Lua 字节码文件] 跳过文件：{os.path.basename(file_path)}")
            return file_path, {}, [], "Lua 字节码文件"
            
        # 直接进行编码检测，不再检查二进制特征
        for encoding in encodings:
            try:
                source = raw_data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，使用 latin-1 作为后备（它不会失败，但可能显示乱码）
        if source is None:
            source = raw_data.decode('latin-1')
            logger.warning(f"[无法解码] 跳过文件：{os.path.basename(file_path)}")
            return file_path, {}, [], "编码解析失败"
            
        # 禁用输出中不必要的打印，避免编码错误
        import sys
        import io
        original_stdout = sys.stdout
        sys.stdout = io.StringIO()  # 捕获输出，避免打印到控制台
        
        try:
            tree = ast.parse(source)
        except SyntaxException:
            logger.warning(f"[语法错误] 跳过文件：{os.path.basename(file_path)}")
            return file_path, {}, [], "语法错误"
        except Exception as e:
            logger.error(f"[解析错误] 跳过文件：{os.path.basename(file_path)} - {str(e)}")
            return file_path, {}, [], "解析错误"
        finally:
            sys.stdout = original_stdout  # 恢复正常输出
            
    except IOError as e:
        logger.error(f"[IO 错误] 跳过文件：{os.path.basename(file_path)} - {str(e)}")
        return file_path, {}, [], "IO 错误"
    except Exception as e:
        logger.error(f"[未知错误] 跳过文件：{os.path.basename(file_path)} - {str(e)}")
        return file_path, {}, [], "未知错误"
    
    try:    
        _visitor = Lus4nVisitor(4, source)
        _visitor.visit(tree)
        call_graph, require = _visitor.output(_format=_format)
        return file_path, call_graph, require, "成功"
    except Exception as e:
        logger.error(f"[分析错误] 跳过文件：{os.path.basename(file_path)} - {str(e)}")
        return file_path, {}, [], "分析错误"


def scan_path(dirt_path: str, _format, _debug=False, extensions=None):
    whole_call_graph = {}
    whole_call_network = nx.DiGraph()
    will_scan = []
    
    # 如果没有指定后缀，默认使用 .lua
    if extensions is None:
        extensions = [".lua"]
        
    for path, dir_list, file_list in os.walk(dirt_path):
        for file_name in file_list:
            file_path = os.path.join(path, file_name)
            
            # 1. 首先检查文件是否有指定的后缀，不符合的直接跳过
            has_valid_extension = any(file_path.endswith(ext) for ext in extensions)
            if not has_valid_extension:
                continue
                
            try:
                # 检查文件是否可读取
                try:
                    content = open(file_path, "rb").read()
                except (PermissionError, IOError) as e:
                    logger.warning(f"读取文件错误：{file_path} [{str(e)}]")
                    continue
                
                # 只检查是否为 Lua 字节码，不是字节码就当作文本处理
                if content.startswith(b"\x1bL"):
                    logger.warning(f"跳过 Lua 字节码文件：{file_path}")
                    continue
                    
                # 直接进行编码检测，不再检查二进制特征
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
                    logger.warning(f"无法解码的文件编码：{file_path}")
                    continue
                    
                # 添加文件到扫描列表的条件
                # 对于用户指定后缀的文件，直接处理，不再检查是否有 Lua 特征
                will_scan.append(file_path)
                if detected_encoding != 'utf-8' and _debug:
                    logger.info(f"文件 {file_path} 使用 {detected_encoding} 编码")
            except PermissionError:
                logger.warning(f"权限错误：{file_path}")
            except Exception as e:
                logger.warning(f"未知错误：{file_path} [{e}]")
            
    for file_path in tqdm(will_scan):
        _, call_graph, require, status = scan_one_file(file_path, _format, _debug)
        relative_file_path = file_path[len(dirt_path):]
        if not relative_file_path.startswith("/"):
            relative_file_path = "/" + relative_file_path
        whole_call_graph[relative_file_path] = call_graph
        whole_call_network.add_node(relative_file_path, role='file')
        package_name = os.path.basename(file_path).replace(".lua", "")
        for tmp_name in call_graph.keys():
            if tmp_name == "[G]":
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
    return whole_call_graph, whole_call_network


class Lus4nVisitor(PythonStyleVisitor):

    def __init__(self, indent, source):
        super().__init__(indent)
        self.source = source
        self.lines = [line.strip() for line in self.source.split('\n')]
        self.stack_for_function = []
        self.call_graph = {}
        self.require = []

    @visitor(str)
    def visit(self, node):
        return repr(node)

    @visitor(float)
    def visit(self, node):
        return str(node)

    @visitor(int)
    def visit(self, node):
        return str(node)

    @visitor(Enum)
    def visit(self, node):
        return str(node.name)

    def indent_str(self, newLine=True):
        res = " " * self.currentIndent
        if newLine:
            res = "\n" + res
        return res

    def indent(self):
        self.currentIndent += self.indentValue

    def dedent(self):
        self.currentIndent -= self.indentValue

    @staticmethod
    def pretty_count(node, is_list=False):
        res = ""
        if isinstance(node, list):
            item_count = len(node)
            res += "[] " + str(item_count) + " "
            if item_count > 1:
                res += "items"
            else:
                res += "item"
        elif isinstance(node, Node):
            if is_list:
                return "{} 1 key"
            key_count = len(
                [attr for attr in node.__dict__.keys() if not attr.startswith("_")]
            )
            res += "{} " + str(key_count) + " "
            if key_count > 1:
                res += "keys"
            else:
                res += "key"
        else:
            res += "[unknow]"
        return res

    @visitor(list)
    def visit(self, obj):
        res = ""
        k = 0
        for itemValue in obj:
            res += (
                    self.indent_str() + str(k) + ": " + self.pretty_count(itemValue, True)
            )
            self.indent()
            res += self.indent_str(False) + self.visit(itemValue)
            self.dedent()
            k += 1
        return res

    @visitor(Node)
    def visit(self, node):
        res = self.indent_str() + node.display_name + ": " + self.pretty_count(node)

        self.indent()

        # comments
        comments = node.comments
        if comments:
            res += self.indent_str() + "comments" + ": " + self.pretty_count(comments)
            k = 0
            self.indent()
            for c in comments:
                res += self.indent_str() + str(k) + ": " + self.visit(c.s)
                k += 1
            self.dedent()

        if isinstance(node, Function) or isinstance(node, LocalFunction):
            name = []
            func_name = self.walk_func_name(node.name, name)
            if isinstance(node, Function):
                self.stack_for_function.append(f"[X]{'.'.join(func_name)}")
            elif isinstance(node, LocalFunction):
                self.stack_for_function.append(f"[L]{'.'.join(func_name)}")

        for attr, attrValue in node.__dict__.items():

            if isinstance(node, Call):
                if len(self.stack_for_function) > 0:
                    from_where = self.stack_for_function[-1]
                else:
                    from_where = "[G]"
                if from_where not in self.call_graph.keys():
                    self.call_graph[from_where] = []
                if isinstance(node.func, Index):
                    try:
                        called_func_name = self.source[node.func.start_char: node.func.stop_char + 1]
                        self.call_graph[from_where].append(called_func_name)
                    except TypeError as e:
                        logger.warning(f"Oops, TypeError {e}")
                    # logger.debug(f"Index: {from_where} -> {self.source[node.func.start_char: node.func.stop_char + 1]}")
                elif isinstance(node.func, Name):
                    self.call_graph[from_where].append(node.func.id)
                    if node.func.id == "require" and len(node.args) > 0 and hasattr(node.args[0], "s"):
                        self.require.append(node.args[0].s)
                    # logger.debug(f"Name: {from_where} -> {node.func.id}")

            if not attr.startswith(("_", "comments")):
                if isinstance(attrValue, Node) or isinstance(attrValue, list):
                    res += (
                            self.indent_str() + attr + ": " + self.pretty_count(attrValue)
                    )
                    self.indent()
                    res += self.visit(attrValue)
                    self.dedent()
                else:
                    if attrValue is not None:
                        res += self.indent_str() + attr + ": " + self.visit(attrValue)

        if isinstance(node, Function) or isinstance(node, LocalFunction):
            self.stack_for_function.pop()

        self.dedent()
        return res

    def output(self, _format="json"):
        for from_where in self.call_graph.keys():
            self.call_graph[from_where] = list(set(self.call_graph[from_where]))
        if _format == "json":
            logger.success(json.dumps(self.call_graph, indent=4))
        return self.call_graph, self.require

    def walk_func_name(self, node: Node, name: list):
        if isinstance(node, Name):
            name.append(node.id)
            return name
        elif isinstance(node, Index):
            name = self.walk_func_name(node.value, name)
            name.append(node.idx.id)
            return name

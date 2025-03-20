import os
import uuid
import shutil
import argparse
import tempfile
import webbrowser
import networkx as nx

from joblib import dump, load
from lus4n.ui.custom_network import CustomNetwork

from lus4n.graph import scan_path


parser = argparse.ArgumentParser(description="Lus4n: lua call graph generation")
parser.add_argument('-p', '--path', type=str)
parser.add_argument('-s', '--storage', type=str)
parser.add_argument('-q', '--query', type=str)
parser.add_argument('-e', '--extensions', type=str, default=".lua", help="要扫描的文件后缀，多个后缀以逗号分隔，例如 '.lua,.luac'")
parser.add_argument('-g', '--gui', action='store_true', help="以图形界面模式启动")
args = parser.parse_args()
temp_dir = tempfile.gettempdir()
if args.path:
    assert os.path.exists(args.path)
    if args.storage:
        assert os.path.exists(os.path.dirname(args.storage))
        storage = args.storage
    else:
        storage = os.path.join(temp_dir, str(uuid.uuid4())) + '.jb'
elif args.query:
    assert args.storage and os.path.exists(args.storage)
    storage = args.storage
else:
    temp_dir = tempfile.gettempdir()
    storage = os.path.join(temp_dir, str(uuid.uuid4())) + '.jb'


def cli_main():
    if args.path:
        extensions = [ext.strip() for ext in args.extensions.split(",")]
        d, g = scan_path(args.path, None, False, extensions)
        dump(g, storage)
    elif args.query:
        g: nx.DiGraph = load(args.storage)
        if args.query in g.nodes:
            nodes: set = nx.ancestors(g, args.query)
            file_node_list = []
            func_node_list = []
            for node in nodes:
                if "role" in g.nodes[node] and g.nodes[node]["role"] == "file":
                    file_node_list.append(node)
                else:
                    func_node_list.append(node)
            if args.query not in nodes:
                nodes.add(args.query)
            sg = g.subgraph(nodes)
            
            # 创建临时目录用于存放 HTML 和静态资源
            temp_uuid = str(uuid.uuid4())
            temp_output_dir = os.path.join(temp_dir, f"lus4n_{temp_uuid}")
            os.makedirs(temp_output_dir, exist_ok=True)
            
            # 复制静态资源文件到临时目录
            static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui', 'static')
            try:
                shutil.copy(os.path.join(static_dir, 'vis.min.js'), temp_output_dir)
                shutil.copy(os.path.join(static_dir, 'vis.min.css'), temp_output_dir)
                
                # 获取自定义模板路径
                template_path = os.path.join(static_dir, 'template.html')
                fallback_template_path = os.path.join(static_dir, 'fallback_template.html')
                
                # 创建网络图
                net = CustomNetwork(notebook=True)
                net.add_node(args.query)
                net.from_nx(sg)
                
                # 选择模板
                if os.path.exists(template_path):
                    net.set_template(template_path)
                elif os.path.exists(fallback_template_path):
                    net.set_template(fallback_template_path)
                else:
                    # 使用内联模板作为最后的备用方案
                    print("警告：找不到模板文件，使用内联模板")
                    inline_template = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Lus4n Network</title>
<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet" type="text/css" />
<style type="text/css">
    #mynetwork {
        width: 100%;
        height: 800px;
        border: 1px solid lightgray;
    }
</style>
</head>
<body>
<div id="mynetwork"></div>
</body>
</html>
                    """
                    # 创建临时模板文件
                    temp_template_path = os.path.join(temp_output_dir, "temp_template.html")
                    with open(temp_template_path, "w", encoding="utf-8") as f:
                        f.write(inline_template)
                    net.set_template(temp_template_path)
                
                show_path = os.path.join(temp_output_dir, "network.html")
                net.show(show_path)
                webbrowser.open_new_tab(f"file://{show_path}")
            except Exception as e:
                print(f"复制静态资源文件失败：{e}")
                # 回退到原始方法
                net = CustomNetwork(notebook=True)
                net.add_node(args.query)
                net.from_nx(sg)
                show_path = os.path.join(temp_dir, f"{uuid.uuid4()}.html")
                net.show(show_path)
                webbrowser.open_new_tab(f"file://{show_path}")
        else:
            print(f"no such node {args.query}")


def main():
    # 如果指定了 GUI 模式或没有提供任何参数，启动 GUI
    if args.gui or (not args.path and not args.query):
        try:
            from lus4n.gui import main as gui_main
            gui_main()
        except ImportError as e:
            print(f"无法启动图形界面：{e}")
            print("请确保已安装 PySide6。可以使用命令 'pip install PySide6' 安装。")
    else:
        # 否则使用命令行模式
        cli_main()


if __name__ == "__main__":
    main()

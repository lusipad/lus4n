import os
import uuid
import argparse
import tempfile
import webbrowser
import networkx as nx

from joblib import dump, load
from pyvis.network import Network

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
            net = Network(notebook=True)
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

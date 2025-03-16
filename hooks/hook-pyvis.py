# PyInstaller hook for pyvis
import os
import sys
import site

# Make sure all submodules are included
hiddenimports = [
    'pyvis.network',
    'pyvis.options',
    'pyvis.physics',
    'pyvis.node',
    'pyvis.edge',
]

# 硬编码包含模板文件 - 更加可靠
templates_files = []
static_files = []

# 尝试多个可能的位置查找pyvis包
possible_paths = []

# 1. 检查标准site-packages路径
for site_path in site.getsitepackages():
    possible_paths.append(os.path.join(site_path, 'pyvis'))

# 2. 检查用户特定site-packages路径
if hasattr(site, 'getusersitepackages'):
    user_site = site.getusersitepackages()
    possible_paths.append(os.path.join(user_site, 'pyvis'))

# 3. 检查PYTHONPATH中的每个路径
for path in sys.path:
    possible_paths.append(os.path.join(path, 'pyvis'))

# 4. 尝试直接导入pyvis来找到它
try:
    import pyvis
    possible_paths.append(os.path.dirname(pyvis.__file__))
except ImportError:
    pass

# 寻找包含模板的有效路径
for path in possible_paths:
    templates_dir = os.path.join(path, 'templates')
    static_dir = os.path.join(path, 'static')
    
    if os.path.exists(templates_dir):
        templates_files.append((templates_dir, 'pyvis/templates'))
    if os.path.exists(static_dir):
        static_files.append((static_dir, 'pyvis/static'))

# 直接打包模板文件
if not templates_files:
    templates_html = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pyvis_templates')
    if not os.path.exists(templates_html):
        os.makedirs(templates_html)
    with open(os.path.join(templates_html, 'template.html'), 'w') as f:
        f.write("""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Network</title>
<script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.20.0/vis.min.js"></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.20.0/vis.min.css" rel="stylesheet" type="text/css" />
</head>
<body>
<div id="mynetwork"></div>
</body>
</html>
        """)
    templates_files = [(templates_html, 'pyvis/templates')]

# 合并找到的所有数据文件
datas = templates_files + static_files

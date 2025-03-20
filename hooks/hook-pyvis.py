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

# 尝试多个可能的位置查找 pyvis 包
possible_paths = []

# 1. 检查标准 site-packages 路径
for site_path in site.getsitepackages():
    possible_paths.append(os.path.join(site_path, 'pyvis'))

# 2. 检查用户特定 site-packages 路径
if hasattr(site, 'getusersitepackages'):
    user_site = site.getusersitepackages()
    possible_paths.append(os.path.join(user_site, 'pyvis'))

# 3. 检查 PYTHONPATH 中的每个路径
for path in sys.path:
    possible_paths.append(os.path.join(path, 'pyvis'))

# 4. 尝试直接导入 pyvis 来找到它
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

# 添加 lus4n 自己的静态资源文件
lus4n_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lus4n', 'ui', 'static')
if os.path.exists(lus4n_static_dir):
    # 添加 lus4n 的静态资源文件到 datas
    lus4n_static_files = [(lus4n_static_dir, 'lus4n/ui/static')]
    # 确保这些文件被包含在打包中
    templates_files.extend(lus4n_static_files)
    
    # 创建备份文件，确保即使原始文件丢失也能使用
    backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backup_static')
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        
    # 复制模板文件到备份目录
    template_path = os.path.join(lus4n_static_dir, 'template.html')
    fallback_template_path = os.path.join(lus4n_static_dir, 'fallback_template.html')
    vis_js_path = os.path.join(lus4n_static_dir, 'vis.min.js')
    vis_css_path = os.path.join(lus4n_static_dir, 'vis.min.css')
    
    # 明确添加模板文件到 PyInstaller 的 datas 列表
    if os.path.exists(template_path):
        templates_files.append((template_path, 'pyvis/templates'))
        # 同时添加到 lus4n 目录结构中，确保两个位置都能找到
        templates_files.append((template_path, 'lus4n/ui/static'))
    if os.path.exists(fallback_template_path):
        templates_files.append((fallback_template_path, 'pyvis/templates'))
        # 同时添加到 lus4n 目录结构中，确保两个位置都能找到
        templates_files.append((fallback_template_path, 'lus4n/ui/static'))
    if os.path.exists(vis_js_path):
        static_files.append((vis_js_path, 'pyvis/static'))
        # 同时添加到 lus4n 目录结构中，确保两个位置都能找到
        static_files.append((vis_js_path, 'lus4n/ui/static'))
    if os.path.exists(vis_css_path):
        static_files.append((vis_css_path, 'pyvis/static'))
        # 同时添加到 lus4n 目录结构中，确保两个位置都能找到
        static_files.append((vis_css_path, 'lus4n/ui/static'))

# 合并找到的所有数据文件
datas = templates_files + static_files

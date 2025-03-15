# lus4n

**Author: C0ss4ck**

## 项目简介

lus4n 是一个基于 AST (抽象语法树) 分析的 Lua 代码调用图生成工具。它可以扫描 Lua 代码文件，构建函数调用关系图，并支持查询和可视化特定函数的调用关系。

## 安装方法

### 前提条件

- Python 3.6 或更高版本
- pip 包管理工具

### 安装步骤

1. 克隆仓库到本地

```
git clone https://github.com/lusipad/lus4n.git
```

2. 进入项目目录

```
cd lus4n
```

3. 安装依赖包和 lus4n 工具

在 PowerShell 中执行:

```powershell
pip install -e .
```

## 使用方法

lus4n 支持以下功能：

### 1. 扫描 Lua 代码并生成调用图

```powershell
lus4n -p <Lua代码路径> -s <存储文件路径> [-e <文件后缀>]
```

参数说明:
- `-p, --path`: 指定要扫描的 Lua 代码路径（必需）
- `-s, --storage`: 指定生成的调用图数据存储文件路径（可选，如果不指定则存储在临时目录）
- `-e, --extensions`: 指定要扫描的文件后缀，多个后缀用逗号分隔（可选，默认为 ".lua"）

示例:

```powershell
# 使用默认后缀 .lua 进行扫描
lus4n -p ./rootfs/ -s ./result.jb

# 扫描 .lua 和 .luac 后缀的文件
lus4n -p ./rootfs/ -s ./result.jb -e ".lua,.luac"

# 扫描所有 .lc 后缀的文件
lus4n -p ./rootfs/ -s ./result.jb -e ".lc"
```

### 2. 查询特定函数的调用关系

```powershell
lus4n -s <存储文件路径> -q <查询函数名>
```

参数说明:
- `-s, --storage`: 指定之前生成的调用图数据存储文件路径（必需）
- `-q, --query`: 指定要查询的函数名（必需）

示例:

```powershell
lus4n -s ./result.jb -q os.execute
```

执行查询后，lus4n 将自动打开浏览器显示调用图的可视化结果。

## 输出结果说明

查询后生成的调用图中：
- 不同节点代表不同的函数
- 边表示函数间的调用关系
- 可以直接在浏览器中交互，拖动、缩放调用图

## 常见问题

### 找不到特定函数

如果查询时显示 `no such node xxx`，表示该函数在扫描的代码中未被找到。请检查：
1. 函数名是否输入正确
2. 该函数是否在扫描的代码路径中
3. 调用图存储文件是否正确

### 临时文件位置

如果未指定存储文件路径，lus4n 将使用系统临时目录存储生成的调用图数据和可视化 HTML 文件。
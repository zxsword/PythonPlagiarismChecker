@echo off
rem 这个脚本用于启动 Python 代码相似度检查工具。
rem 它会直接使用 python 命令执行 main.py 文件。

echo 正在启动 Python 代码相似度检查工具...

rem 使用 python 运行主程序。
rem '%~dp0' 是一个特殊的变量，代表这个 .bat 文件所在的目录，
rem 这样可以确保无论从哪里运行这个脚本，都能正确找到 main.py。
python "%~dp0main.py"

echo 程序已关闭。

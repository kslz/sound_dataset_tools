# -*- coding: utf-8 -*-
"""
    @Time : 2022/12/30 9:27
    @Author : 李子
    @Url : https://github.com/kslz
"""

# import这个模块可以让你正常的用命令行调用example里的py文件，不然会报找不到utils包
import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
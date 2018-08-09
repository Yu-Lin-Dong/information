#导入蓝图Blueprint
from flask import Blueprint
#创建蓝图对象,第一个参数是用来调用函数的
index_blue = Blueprint("index",__name__)
#导入views要放在最后
from . import views
from flask import Blueprint
# url_prefix设置前缀
passport_blue = Blueprint("passport",__name__,url_prefix="/passport")
from . import views
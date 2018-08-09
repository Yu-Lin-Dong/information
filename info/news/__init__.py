from flask import Blueprint

news_blue = Blueprint("news",__name__,url_prefix = "/news")

from info.news import views
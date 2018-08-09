import redis
from flask import Flask
from flask import g
from flask import render_template
from flask.ext.wtf.csrf import generate_csrf
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

from config import config_map

# 打包
import logging
from logging.handlers import RotatingFileHandler

# 设置日志的记录等级
logging.basicConfig(level=logging.DEBUG) # 调试debug级
# 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024*1024*100, backupCount=10)
# 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
# 为刚创建的日志记录器设置日志记录格式
file_log_handler.setFormatter(formatter)
# 为全局的日志工具对象（flask app使用的）添加日志记录器
logging.getLogger().addHandler(file_log_handler)




db = SQLAlchemy()
redis_store = None  # type:redis.StrictRedis
def create_app(config_name):
    #初始化flask对象
    app = Flask(__name__)
    #根据字典的key,获取到字典的value
    config_class = config_map.get(config_name)

    #将配置文件添加到flask对象中
    app.config.from_object(config_class)

    db.init_app(app)
    # 初始化数据库对象
    # db = SQLAlchemy(app)
    # 创建redis(存储验证码,存储短信验证码和图片验证码) 第一个参数ip 第二个参数端口,第三个参数表示解码,在redis里面进行操作,用来取数据的时候,byte,string
    global redis_store
    redis_store = redis.StrictRedis(host=config_class.REDIS_HOST,port=config_class.REDIS_PORT,decode_responses=True)
    # 导入session:目的用来进行持久化操作,不需要每次都让用户进行登陆,我们需要把session存储到redis当中
    Session(app)
    # 开启CSRF保护,把整个flask对象丢进去,需要添加一个SECRET_KEY秘钥
    CSRFProtect(app)

    @app.after_request
    def after_request(response):
        # 调用函数生成 csrf_token
        csrf_token = generate_csrf()
        # 通过cookie将值传递给前端
        response.set_cookie("csrf_token", csrf_token)
        return response
    # 添加自定义过滤器
    from info.utils.common import do_index_class
    app.add_template_filter(do_index_class,"indexClass")

    from info.utils.common import user_login_data
    @app.errorhandler(404)
    @user_login_data
    def error_404_handler(error):
        user = g.user
        data = {
            "user_info":user.to_dict() if user else None
        }
        return render_template("news/404.html",data=data)

    # 注册首页的蓝图
    from info.index import index_blue
    app.register_blueprint(index_blue)
    # 登陆注册的蓝图
    from info.passport import passport_blue
    app.register_blueprint(passport_blue)
    # 新闻详情的蓝图
    from info.news import news_blue
    app.register_blueprint(news_blue)
    # 个人中心的蓝图
    from info.user import profile_blue
    app.register_blueprint(profile_blue)
    # 后台管理系统蓝图
    from info.admin import admin_blue
    app.register_blueprint(admin_blue)


    return app



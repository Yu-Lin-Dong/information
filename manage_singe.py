from flask import Flask
from flask_sqlalchemy import SQLAlchemy
# 导入redis
import redis
# 导入session
from flask_session import Session
# 导CSRF包
from flask_wtf import CSRFProtect

"""
flask_migrate作用:
1 通过命令的方式创建表
2 修改表的结构
"""
from flask_script import Manager
from flask_migrate import Migrate,MigrateCommand

#初始化flask对象
app = Flask(__name__)
#设置配置文件
class Config(object):
    #开启调试模式
    DEBUG = True
    #设置秘钥
    SECRET_KEY = "wwssaaddbaba"
    # 设置数据库uri
    SQLALCHEMY_DATABASE_URI = "mysql://root:mysql@127.0.0.1:3306/information15"
    #禁止发送消息
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379

    # 配置redis
    #设置session的存储数据类型
    SESSION_TYPE = "redis"
    #创建一个session-redis,用来存储session
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST,port=REDIS_PORT)
    #使用session的签名
    SESSION_USE_SIGNER =True
    # 设置session的有效期,单位是秒,86400表示一天有效,也可以不用设置,不设置默认一个月
    PERMANENT_SESSION_LIFETIME = 86400

#将配置文件添加到flask对象中
app.config.from_object(Config)
# 初始化数据库对象
db = SQLAlchemy(app)
# 创建redis(存储验证码,存储短信验证码和图片验证码) 第一个参数ip 第二个参数端口,第三个参数表示解码,在redis里面进行操作,用来取数据的时候,byte,string
redis_store = redis.StrictRedis(host=Config.REDIS_HOST,port=Config.REDIS_PORT,decode_responses=True)
# 导入session:目的用来进行持久化操作,不需要每次都让用户进行登陆,我们需要把session存储到redis当中
Session(app)
# 开启CSRF保护,把整个flask对象丢进去,需要添加一个SECRET_KEY秘钥
CSRFProtect(app)
# 把flask对象交给manage来管理
manager = Manager(app)
# 创建表 第一个参数是Flask的对象，第二个参数是Sqlalchemy数据库对象
Migrate(app,db)
# 添加一个迁移命令
manager.add_command("mysql",MigrateCommand)
@app.route("/")
def index():
    return "index"
if __name__ == '__main__':
    manager.run()
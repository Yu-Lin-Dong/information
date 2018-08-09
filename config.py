import redis
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

#在做项目期间,我们使用的是测试模式
class DevelopmentConfig(Config):
    DEBUG = True

#项目正式上线,我们使用的是上线模式
class ProductionConfig(Config):
    DEBUG = False

config_map = {
    "develop" : DevelopmentConfig,
    "production": ProductionConfig
}






"""
flask_migrate作用:
1 通过命令的方式创建表
2 修改表的结构
"""
from flask_script import Manager
from flask_migrate import Migrate,MigrateCommand
from info import create_app ,db
from info import models
from info.models import User

"""
manager.py的作用是入口函数
"""
app = create_app("develop")

# 把flask对象交给manage来管理
manager = Manager(app)
# 创建表 第一个参数是Flask的对象，第二个参数是Sqlalchemy数据库对象
Migrate(app,db)
# 添加一个迁移命令
manager.add_command("mysql",MigrateCommand)

# 创建管理员对象
# 创建管理员  --manager的作用: 是在终端使用命令, option的作用:装饰的之后,可以传递参数
@manager.option('-n','--name',dest='name')
@manager.option('-p','--password',dest='password')
def create_super_admin(name,password):
    # 创建用户对象,添加属性
    user = User()
    user.mobile = name
    user.nick_name = name
    user.password = password
    user.is_admin = True   #True表示为管理员

    # 保存到数据库
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        app.logger.error(e)
        db.session.rollback()


if __name__ == '__main__':
    manager.run()
from info.models import User
from . import passport_blue
from flask import request,make_response,jsonify
from info.utils.captcha.captcha import captcha
from info import redis_store
from info.utils.response_code import RET
import re,random
from info.libs.yuntongxun.sms import CCP
from datetime import datetime
from info import constants, db
from flask import current_app
from flask import session
# 导入生成 csrf_token 值的函数
from flask_wtf.csrf import generate_csrf

# 图片验证
@passport_blue.route("/image_code")
def image_code():
    print("前端请求的url地址 = " + request.url)
    # 获取到前端传递过来的随机的一个验证码
    code_id = request.args.get("code_id")
    print(code_id)
    # name:表示图片验证码的名字
    # text:表示图片验证码的内容
    # image:表示是图片
    # 生成图片验证码
    name,text,image = captcha.generate_captcha()
    print("图片验证码的内容 =" + text)
    # 我们需要把图片验证码存到redis的数据库当中
    # image_code_xxxx
    # 第一个参数表示key,第二个参数表示图片验证码的内容,第三个参数表示过期时间
    redis_store.set("image_code_"+code_id,text,300)
    # 获取到redis里面的值是byte
    # make_response:表示响应体对象,这个对象的参数表示图片的验证码
    resp = make_response(image)
    # 告诉系统,我们当前需要展示的是图片
    resp.headers['Content-Type']='image/jpg'
    return resp

# 短信验证码
@passport_blue.route("/sms_code",methods=["GET","POST"])
def sms_code():
    """
        1. 接收参数并判断是否有值
        2. 校验手机号是正确
        3. 通过传入的图片编码去redis中查询真实的图片验证码内容
        4. 进行验证码内容的比对
        5. 生成发送短信的内容并发送短信
        6. redis中保存短信验证码内容
        7. 返回发送成功的响应
        """
    # 获取到前端传递过来的json数据
    #获取用户手机号码
    mobile = request.json.get("mobile")
    # 获取用户输入的图片验证码内容
    image_code = request.json.get("image_code")
    # 表示图片验证码的id
    image_code_id = request.json.get("image_code_id")
    # 校验前端传递过来的参数是否有值
    if not all([mobile,image_code,image_code_id]):
        return jsonify(errno=RET.PARAMERR,errmsg="请输入参数")
    # 校验用户传递过来的手机号是否正确
    if not re.match("1[356789]\d{9}",mobile):
        return jsonify(errno=RET.PARAMERR,errmsg="请输入正确的手机号码")
    # 获取到redis里面的图片验证码
    real_image_code = redis_store.get("image_code_"+image_code_id)
    #判断redis是否过期
    if not real_image_code:
        return jsonify(errno=RET.NODATA,errmsg="图片验证码已过期")
    # 不为空说明redis没有过期,判断用户输入的验证码是否正确,lower()转换成小写在进行判断
    if image_code.lower() != real_image_code.lower():
        return jsonify(errno=RET.PARAMERR,errmsg="请输入正确的图片验证码" )
    # 通过随机数生成一个6位的验证码,"%06d"如果不够6位,通过0补齐
    random_sms_code="%06d"%random.randint(0,999999)
    # 在服务器的redis里面存储短信验证码,用来给用户进行校验操作
    # 第一个参数表示key ,第二个参数表示随机数,第三个参数表示过期时间,SMS_CODE_REDIS_EXPIRES常量300秒
    redis_store.set("sms_code_" + mobile, random_sms_code,1440)
    # redis_store.set("sms_code_" + mobile, random_sms_code, constants.SMS_CODE_REDIS_EXPIRES)
    #打印验证码
    print("短信验证码的内容 = " + random_sms_code)
    # 发送短信
    # statuCode = CCP().send_template_sms(mobile,[random_sms_code,1440],1)
    # if statuCode != 0:
    #     return jsonify(errno=RET.THIRDERR,errmsg = "短信发送失败")
    return jsonify(errno=RET.OK,errmsg="发送短信成功")

# 注册
@passport_blue.route("/register",methods = ["GET","POST"])
def register():
    """
        1. 获取参数和判断是否有值
        2. 从redis中获取指定手机号对应的短信验证码的
        3. 校验验证码
        4. 初始化 user 模型，并设置数据并添加到数据库
        5. 保存当前用户的状态
        6. 返回注册的结果
        """
    # 获取用户输入的手机号
    mobile = request.json.get("mobile")
    # 获取用户输入的短信验证码
    smscode = request.json.get("smscode")
    # 获取用户输入的密码
    password = request.json.get("password")
    # 获取到redis服务器里面存储的短信验证码
    real_sms_code = redis_store.get("sms_code_"+mobile)
    # 判断redis服务器里存储的短信验证码是否过期
    if not real_sms_code:
        return jsonify(errno=RET.NODATA,errmsg="验证码已过期")
    # 判断用户输入的短信验证码和redis服务器里面的短信验证码是否一致
    if smscode != real_sms_code:
        return jsonify(errno=RET.PARAMERR,errmsg='请输入正确的验证码')
    # 创建一个用户对象用来注册用户
    user = User()
    user.mobile = mobile
    user.password = password
    user.nick_name = mobile   #昵称
    #获取当前的时间,用来注册
    user.last_login = datetime.now()
    # 往数据库进行持久化操作
    db.session.add(user)
    db.session.commit()
    return jsonify(errno=RET.OK,errmsg="注册成功")


# @passport_blue.after_request
# def after_request(response):
#     # 调用函数生成 csrf_token
#     csrf_token = generate_csrf()
#     #通过cookie将值传递给前端
#     response.set_cookie("csrf_token",csrf_token)
#     return response

# 用户登陆
@passport_blue.route("/login",methods=["GET","POST"])
def login():
    """
       1. 获取参数和判断是否有值
       2. 从数据库查询出指定的用户
       3. 校验密码
       4. 保存用户登录状态
       5. 返回结果
       """
    #获取前端发送过来的手机号
    mobile = request.json.get("mobile")
    #获取前端发送过来的密码
    password = request.json.get("password")
    # 判断是否有值
    if not all ([mobile,password]):
        # 参数错误
        return jsonify(errno=RET.PARAMERR,errmsg="请输入手机号或密码")
    # 通过手机号查询数据库中是否有知道用户
    try:
        # 通过query操作数据,filter过滤器,模糊查询,first返回查询到的第一个数据
        user = User.query.filter(User.mobile ==mobile).first()
    except Exception as e:
        # 把错误信息存储到log日志里面
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据错误")
    # 判断是否有这个用户
    if not user:
        return jsonify(errno=RET.NODATA,errmsg="请注册账号")
    # 通过系统的源码帮我们检查用户的密码是否正确
    if not user.check_password(password):
        return jsonify(errno=RET.PWDERR,errmsg="请输入正确的密码")
    # 对用户进行状态保持,跟网易新闻一样,session进行实现,保持用户信息到session里面
    session["user_id"]=user.id
    session["nick_name"]=user.nick_name
    session["mobile"]=user.mobile
    #更新最后登陆的时间
    user.last_login = datetime.now()
    #把数据提交到数据库
    db.session.commit()
    return jsonify(errno = RET.OK,errmsg="登陆成功")
# 退出功能
@passport_blue.route("/logout",methods=["POST"])
def logout():
    """
    清楚session中的对应登陆之后保存的信息
    """
    session.pop('user_id',None)
    session.pop('nick_name',None)
    session.pop('mobile',None)
    session.pop("is_admin",None)
    # 返回结果
    return jsonify(errno=RET.OK,errmsg="OK")
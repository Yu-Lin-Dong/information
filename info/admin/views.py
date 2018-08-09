from flask import g, jsonify
from flask import render_template
from flask import request
from flask import current_app
from flask import session
from flask import redirect
from flask import url_for
import time
from datetime import datetime, timedelta

from info import constants, db
from info.admin import admin_blue
from info.models import User, News, Category
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET


@admin_blue.route("/index")
@user_login_data
def admin_index():
    user = g.user
    return render_template("admin/index.html",user=user.to_dict())

@admin_blue.route("/login",methods=['GET','POST'])
def admin_login():
    if request.method == "GET":
        return render_template("admin/login.html")

    username = request.form.get("username")
    password = request.form.get("password")
    if not all([username,password]):
        return render_template("admin/login.html",errmsg="参数错误")

    try:
        user = User.query.filter(User.mobile == username).first()
    except Exception as e:
        current_app.logger.error(e)
        return render_template("admin/login.html",errmsg="数据查询失败")

    #判断是否有这个用户
    if not user:
        return render_template("admin/login.html",errmsg="用户不存在")
    # 判断密码
    # check_password()检查是否有这个密码
    if not user.check_password(password):
        return render_template("admin/login.html",errmsg="密码错误")
    # 判断是否是管理员
    if not user.is_admin:
        return render_template("admin/login.html",errmsg="用户权限错误")

    # 把数据存到session中
    session["user_id"] = user.id
    session["nick_name"] = user.nick_name
    session["mobile"] = user.mobile
    session["is_admin"] = user.is_admin

    #如果登陆成功,需要调到主页面
    return redirect(url_for("admin.admin_index"))


# 用户统计
@admin_blue.route("/user_count")
def user_count():
    # 总人数
    total_count = 0
    # 每月新增人数
    mon_count = 0
    # 每天新增加的人数
    day_count = 0
    # 获取到总人数
    # User.is_admin == False把管理员过滤掉

    total_count = User.query.filter(User.is_admin == False).count()
    # 当前时间
    # t = time.localtime()
    # # 本月开始时间
    # # t.tm_year:年  t.tm_mon:月
    # mon_begin = "%d-%02d-01"%(t.tm_year,t.tm_mon)
    # # datetime.strftime()方法根据指定的格式把一个时间字符串解析为时间元组
    # # 自动返回 00:00:00  零点零分零秒
    # # 2018-08-01 00:00:00
    # mon_begin_date = datetime.strptime(mon_begin,'%Y-%m-%d')
    # # 获取到本月的人数
    # #User.create_time>=mon_begin_date: 创建时间大于等于本月开始的时间
    # mon_count = User.query.filter(User.is_admin == False,User.create_time>=mon_begin_date).count()

    # t = time.localtime()
    # day_begin = "%d-%02d-%02d" % (t.tm_year, t.tm_mon,t.tm_mday)
    # day_begin_date = datetime.strptime(day_begin, '%Y-%m-%d')
    # # 获取到今天的人数
    # day_count = User.query.filter(User.is_admin == False, User.create_time >= day_begin_date).count()

    t = time.localtime()
    today_begin = "%d-%02d-%02d"%(t.tm_year,t.tm_mon,t.tm_mday)
    today_begin_date = datetime.strptime(today_begin, '%Y-%m-%d')

    # now_date = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
    # 活跃用户
    active_count = []
    # 时间列表
    active_time = []  #TODO
    for i in range(0,30):
        #获取今天的时间
        begin_date = today_begin_date - timedelta(days = i)
        #获取到结束时间
        end_data = today_begin_date - timedelta(days=(i - 1))
        #获取到今天的人数
        count = User.query.filter(User.is_admin==False,User.create_time>=begin_date,User.create_time<end_data).count()
        active_count.append(count)
        active_time.append(begin_date.strftime('%Y-%m-%d'))

    active_count.reverse()
    active_time.reverse()

    data = {
        "total_count":total_count,
        "mon_count":mon_count,
        "day_count":day_count,
        "active_date":active_time,
        "active_count":active_count
    }
    return render_template("admin/user_count.html",data=data)

# 用户列表
@admin_blue.route("/user_list")
def user_list():
    # 获取参数
    page = request.args.get('p',1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    # 设置变量默认值
    users = []
    current_page = 1
    total_page = 1

    #查询数据
    # try:
    # last_login:最后一次登录时间   获取用户(不是管理员)按登录时间排序,分页(当前页数,每页显示条数,不报错)
    paginate = User.query.filter(User.is_admin == False).order_by(User.last_login.desc()).paginate(page,constants.ADMIN_USER_PAGE_MAX_COUNT,False)
    # 获取当前页面需要展示的数据
    users = paginate.items
    # 当前页面
    current_page = paginate.page
    # 总页数
    total_page = paginate.pages
    # except Exception as e:
    #     current_app.logger.error(e)

    #将模型列表转成字典
    users_list = []
    for user in users:
        users_list.append(user.to_admin_dict())

    data = {
        "users":users_list,
        "current_page":current_page,
        "total_page":total_page
    }

    return render_template("admin/user_list.html",data=data)

# 新闻审核页面
@admin_blue.route('/news_review')
def news_review():
    page = request.args.get("p",1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    news_list = []
    current_page = []
    total_page = []

    try:
        paginate = News.query.filter(News.status != 0).order_by(News.create_time.desc()).paginate(page,constants.ADMIN_NEWS_PAGE_MAX_COUNT,False)
        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_review_dict())

    data = {
        "news_list":news_dict_list,
        "current_page":current_page,
        "total_page":total_page
    }

    return render_template("admin/news_review.html",data = data)

# 新闻审核详情
@admin_blue.route("/news_review_detail",methods=["GET","POST"])
def news_review_detail():
    if request.method == "GET":
        #获取新闻id
        news_id = request.args.get("news_id")
        #通过新闻id获取到新闻
        news = News.query.get(news_id)
        data = {
            "news":news.to_dict()
        }
        return render_template("admin/news_review_detail1.html",data=data)

    # action表示动作,如果accept:表示通过,如果是reject表示拒绝
    action = request.json.get("action")
    news_id = request.json.get("news_id")

    news = News.query.get(news_id)
    # 如果是acction就通过,把新闻状态设置为0
    if action == "accept":
        news.status = 0
    else:
        #拒绝的原因
        reason = request.json.get("reason")
        # 如果审核不通过,必须要有拒绝的原因
        if not reason:
            return jsonify(errno=RET.PARAMERR,errmsg="参数错误")
        # 状态设置为-1,表示不通过
        news.status = -1
        news.reason = reason

    db.session.commit()
    return jsonify(errno=RET.OK,errmsg="OK")

# 新闻版式编辑
@admin_blue.route("/news_edit")
def news_edit():
    page = request.args.get("p", 1)
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    """
       新闻编辑:
       1 查询所有的新闻,按照新闻的创建时间进行排序,order_by(News.create_time.desc())
       2 分页查询
    """
    paginate = News.query.order_by(News.create_time.desc()).paginate(page,10,False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    user_list = []
    for item in items:
        user_list.append(item.to_review_dict())

    data = {
        "news_list": user_list,
        "current_page": current_page,
        "total_page": total_page
    }

    return render_template("admin/news_edit.html",data=data)

# 新闻版式编辑详情
@admin_blue.route("/news_edit_detail",methods = ["GET","POST"])
def news_edit_detail():
    if request.method == "GET":
        news_id = request.args.get("news_id")
        news = News.query.get(news_id)
        categorys = Category.query.all()
        category_list = []
        for category in categorys:
            category_list.append(category.to_dict())
        # 去除第一条"最新"
        category_list.pop(0)
        data = {
            "news":news.to_dict(),
            "categories":category_list
        }
        return render_template("admin/news_edit_detail.html",data=data)

    news_id = request.form.get("news_id")
    title = request.form.get("title")
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image")
    category_id = request.form.get("category_id")
    # 判断传递过来的数据是否有值
    if not all([news_id,title,digest,content,index_image,category_id]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数有误")
    # 根据新闻id获取id
    news = None
    try:
        news =News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    # 如果没有这条新闻
    if not news:
        return jsonify(errno=RET.NODATA,errmsg="未查询到新闻数据")
    # 把图片存储到七牛云
    try:
        index_image = index_image.read()
        key = storage(index_image)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg="第三方系统错误")

    # 保存到数据库
    news.title = title
    news.digest = digest
    news.content = content
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.category_id = category_id
    db.session.commit()
    return jsonify(errno = RET.OK,errmsg="ok")


# 新闻分类
@admin_blue.route("/news_type")
def news_type():
    categorys = Category.query.all()
    category_list = []
    for category in categorys:
        category_list.append(category.to_dict())

    category_list.pop(0)
    return render_template("admin/news_type.html",data={"categories": category_list})

# 增加和修改新闻分类
@admin_blue.route("/add_category",methods = ["GET","POST"])
def add_category():
    # 获取到分类id
    cid = request.json.get("id")
    # 新闻分类的名字
    name = request.json.get("name")
    # 如果有id说明是修改标题
    # 如果没有id就说明是添加标题
    if cid:
       category = Category.query.get(cid)
       category.name = name
    else:

        category = Category()
        category.name = name
        db.session.add(category)

    db.session.commit()
    return jsonify(errno=RET.OK, errmsg="保存数据成功")





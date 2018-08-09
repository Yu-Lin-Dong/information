from flask import abort
from flask import current_app
from flask import g
from flask import render_template
from flask import request
from flask import jsonify
from flask import session
from flask import redirect

from info import constants
from info.models import Category, News, User
from info.utils.image_storage import storage

from info import db
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import profile_blue

@profile_blue.route("/info")
@user_login_data
def get_user_info():
    """
    获取用户信息
    1. 获取到当前登录的用户模型
    2. 返回模型中指定内容
    """
    user = g.user
    # 如果当前没有用户，就重定向至首页
    if not user:
        return redirect("/")
    data = {
        "user_info":user.to_dict() if user else None
    }
    return render_template("news/user.html", data = data)



@profile_blue.route("/base_info",methods=["GET","POST"])
@user_login_data
def base_info():
    """
    用户基本信息
    1. 获取用户登录信息
    2. 获取到传入参数
    3. 更新并保存数据
    4. 返回结果
    """
    # 获取当前用户的登录信息
    user = g.user
    if request.method == "GET":
        return render_template("news/user_base_info.html", data={"user_info":user.to_dict()})

    # 获取前端传入的参数
    # 昵称
    nick_name = request.json.get("nick_name")
    # 签名
    signature = request.json.get("signature")
    # 性别 MAN / WOMEN
    gender = request.json.get("gender")

    # 检查参数是否传递过来
    if not all([nick_name,signature,gender]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数有误")
    # 如果性别不在MAN / WOMEN中，就返回传错
    if gender not in(["MAN","WOMEN"]):
        return jsonify(eerrno=RET.PARAMERR,errmsg="参数有误")

    # 更新并保存数据
    user.nick_name = nick_name
    user.gender =gender
    user.signature = signature
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.errer(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg="保存数据失败")

    # 将 session 中保存的数据进行实时更新
    session["nick_name"] = nick_name

    # 返回成功的响应
    return jsonify(errno=RET.OK,errmsg="更新成功")

#修改头像
@profile_blue.route("/pic_info",methods=["GET","POST"])
@user_login_data
def pic_info():
    user = g.user
    # 没有点保存之前都是走GET请求
    if request.method == "GET":
        data = {
            "user_info":user.to_dict() if user else None
        }
        return render_template("news/user_pic_info.html",data = data )

    # 获取到用户传递过来图片的url地址
    avatar_url = request.files.get("avatar").read()
    # 在传递到七牛之后,七牛会返回一个key,返回的目的是帮助我们取访问图片
    key = storage(avatar_url)
    print(key)
    user.avatar_url = key
    db.session.commit()
    data = {
        "avatar_url":constants.QINIU_DOMIN_PREFIX + key
    }
    return jsonify(errno=RET.OK,errmsg="头像设置成功",data = data)

# 修改密码
@profile_blue.route("/pass_info",methods=["GET","POST"])
@user_login_data
def pass_info():
    user = g.user
    if request.method == 'GET':
        data = {
            "user_info":user.to_dict()
        }
        return render_template("news/user_pass_info.html")
    """
    实现步骤：
    如果需要修改密码：
    １　：在修改密码的时候，需要判断当前用户是否已经登陆，就必须判断之前的旧密码是否正确
    ２：　如果之前的旧密码没有问题，才可以修改新的密码
    """
    old_password = request.json.get("old_password")
    new_password = request.json.get("new_password")
    #如果用户输入的密码和当前密码不一样，那么就直接return跳出去
    if not user.check_password(old_password):
        return jsonify(errno=RET.PWDERR,errmsg="密码错误")
    # 否则就是正确的密码,直接修改密码
    user.password = new_password
    # 提交
    db.session.commit()
    return jsonify(errno=RET.OK,errmsg="密码修改成功")

# 新闻收藏
@profile_blue.route("/collection")
@user_login_data
def collection():
    user = g.user
    page = request.args.get("p",1)

    try:
        page = int(page)
    except Exception as e:
        page = 1

    """
       我的收藏是展示当前登陆用户收藏的新闻
       1 判断当前登陆用户
    """
    paginate = user.collection_news.paginate(page,2,False)
    items = paginate.items
    current_page = paginate.page
    total_page = paginate.pages

    collection_list = []
    for collection in items:
        collection_list.append(collection.to_review_dict())
    data = {
        "collection":collection_list,
        "current_page":current_page,
        "total_page":total_page
    }

    return render_template("news/user_collection.html",data=data)

# 发布新闻
@profile_blue.route("/news_release",methods=["GET","POST"])
@user_login_data
def news_release():
    user = g.user
    if request.method == "GET":
        categorys = Category.query.all()
        # 定义列表保存分类数据
        category_list = []
        for category in categorys:
            # 把分类数据添加到列表中
            category_list.append(category.to_dict())
        #移除最新分类,删除第0个元素
        category_list.pop(0)
        data = {
            "categories":category_list
        }
        return render_template("news/user_news_release.html",data=data)

    # POST 提交，执行发布新闻操作
    #获取要提交的数据
    # 新闻标题
    title = request.form.get("title")
    source = "个人发布"
    # 新闻分类id
    category_id = request.form.get("category_id")
    # 新闻摘要
    digest = request.form.get("digest")
    #索引图片
    index_image = request.files.get("index_image").read()
    #新闻内容
    content =request.form.get("content")
    # 判断数据是否有值
    if not all([title,source,category_id,digest,index_image,content]):
        return jsonify(errno=RET.PARAMERR,errmsg="参数有误")

    #将标题图片上传到七牛
    try:
        key = storage(index_image)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR,errmsg="上传图片失败")

    #初始化新闻模型,并设置相关数据
    news = News()
    news.title = title
    news .digest = digest
    news.source = source
    news.content = content
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    news.category_id = category_id
    news.user_id = g.user.id
    # 审核状态,0:代审核 1:审核通过 -1:审核不通过
    news.status = 1

    # 保存到数据库
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.sessioh.rollback()
        return jsonify(errno=RET.DBERR,errmsg="保存数据失败")

    # 返回结果
    return jsonify(errno=RET.OK,errmsg="发布成功,待审核")

# 新闻列表
@profile_blue.route("/news_list")
@user_login_data
def news_list():
    user = g.user
    page =request.args.get("p",1)
    try:
        page = int(page)
    except Exception as e:
        page = 1

    user = g.user
    news_li = []
    current_page =1
    total_page = 1
    try:
        paginate = News.query.filter(News.user_id == user.id).paginate(page,constants.USER_COLLECTION_MAX_NEWS,False)
        # 获取当前页数据
        news_li = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_li = []
    for news_item in news_li:
        news_dict_li.append(news_item.to_review_dict())
    data = {
        "news_list":news_dict_li,
        "total_page":total_page,
        "current_page":current_page
    }
    return render_template("news/user_news_list.html",data=data)

# 我的关注
@profile_blue.route("/follow")
@user_login_data
def follow():
    user = g.user
    page = request.args.get("p", 1)

    try:
        page = int(page)
    except Exception as e:
        page = 1

    items = []
    current_page = 1
    total_page = 1
    try:
        paginate = user.followers.paginate(page,constants.USER_FOLLOWED_MAX_COUNT,False)
        # 获取当前页数据
        items = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    other_list = []
    for item in items:
        other_list.append(item.to_dict())

    data = {
        "users":other_list,
        "current_page":current_page,
        "total_page":total_page
    }
    return render_template("news/user_follow.html",data=data)

# 其他用户页面
@profile_blue.route("/other_info")
@user_login_data
def other_info():
    user = g.user
    # 获取到其他用户的id
    user_id = request.args.get("id")
    if not user_id:
        abort(404)

    # 查询用户模型
    other = None
    try:
        other = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
    if not other:
        abort(404)

    # 判断当前登录用户是否关注过该用户
    is_followed = False
    if g.user:
        if other.followers.filter(User.id == user.id).count() > 0:
            is_followed = True

    # 组织数据，并返回
    data = {
        "user_info": user.to_dict(),
        "other_info": other.to_dict(),
        "is_followed": is_followed
    }
    return render_template('news/other.html', data=data)

# 显示其他用户的新闻列表
@profile_blue.route('/other_news_list')
def other_news_list():
    # 获取页数
    p = request.args.get("p", 1)
    user_id = request.args.get("user_id")
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if not all([p, user_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    if not user:
        return jsonify(errno=RET.NODATA, errmsg="用户不存在")

    try:
        paginate = News.query.filter(News.user_id == user.id).paginate(p, constants.OTHER_NEWS_PAGE_MAX_COUNT, False)
        # 获取当前页数据
        news_li = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据查询错误")

    news_dict_li = []

    for news_item in news_li:
        news_dict_li.append(news_item.to_review_dict())
    data = {
        "news_list": news_dict_li,
        "total_page": total_page,
        "current_page": current_page}
    return jsonify(errno=RET.OK, errmsg="OK", data=data)

from . import index_blue
from flask import render_template,current_app

from flask import session
from info.models import User
# 导入News表
from info.models import News
# 导入常量文件
from info import constants
# 导入新闻分类表
from info.models import Category
"""
current_app:代理对象,代理的是app对象
@index_blue.route = @app.route()
"""
@index_blue.route("/favicon.ico")
def favicon():
    # 发送图标到浏览器
    return current_app.send_static_file('news/favicon.ico')

# 右上角登陆状态
@index_blue.route("/")
def index():
    """
    判断当前的用户是否登陆成功
    """
    # 因为在登陆的时候,我们把数据存储到session里面,所以从session里面获取到当前登陆的用户
    user_id = session.get("user_id")
    user = None
    # 需要判断当前用户是否登陆
    if user_id:
        # 通过user_id查询是否有当前这个用户
        user = User.query.get(user_id)
    """
    获取到右边的热门点击新闻
    获取了十条热门新闻
    """
    news_list = None
    try:
        # order_by:根据指定条件对原查询结果进行排序，返回一个新查询
        # limit	使用指定的值限定原查询返回的结果
        # constants:常量表.CLICK_RANK_MAX_NEWS:常量10 表示点击排行展示的最多新闻数据
        news_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
        print(news_list)
    except Exception as e:
        # 把错误信息存储到log日志里面
        current_app.logger.error(e)
    click_news_list = []
    for news in news_list if news_list else []:
        click_news_list.append(news.to_basic_dict())

    """获取到上面的新闻分类标题"""
    # categorgs = Category.query.all()
    # category_list = []
    # for category in categorgs:
    #     category_list.append(category.to_dict())

    categorys = None
    try:
        categorys = Category.query.all()
    except Exception as e:
        current_app.logger.error(e)
    category_list = []
    for category in categorys:
        category_list.append(category.to_dict())


    data = {
        "user_info": user.to_dict() if user else None,
        "click_news_list": click_news_list,
        "categories":category_list
    }
    return render_template("news/index.html",data=data)

from flask import  request
from flask import jsonify
from info.utils.response_code import RET
@index_blue.route("/news_list")
def newslist():
    #分类id
    cid = request.args.get("cid",1)
    # 页数 获取到前端页面传递过来的数据,表示第几个页面,第二个参数表示默认值是从第1页开始
    page = request.args.get("page",1)
    # 每个页面有多少条数据,默认是十条数据
    per_page = request.args.get("per_page",10)

    try:
        # 前端传递过来的数据是字符串类型,需要转成int类型
        cid =int(cid)
        page = int(page)
        per_page = int(per_page)
    #强制转换
    except Exception as e:
        page = 1
        cid = 1
        per_page = 10

    filter = [News.status==0]
    # if cid == 1:
    #     #     # News.create_time:新闻的发布时间,获取到所有的新闻数据
    #     #     # paginate:表示分页
    #     paginate = News.query.order_by(News.create_time.desc()).paginate(page,per_page,False)
    # else:
    #     paginate = News.query.filter(News.category_id == cid).order_by(News.create_time.desc()).paginate(page,per_page,True)
    if cid != 1:
        filter.append(News.category_id == cid)
    paginate = News.query.filter(*filter).order_by(News.create_time.desc()).paginate(page, per_page, False)

    # 获取到当前页面需要展示的数据
    items = paginate.items
    # 表示当前页面
    current_page = paginate.page
    # 表示总页数
    total_page = paginate.pages

    news_list =[]
    for item in items:
        news_list.append(item.to_dict())
    data = {
        "current_page":current_page,
        "total_page":total_page,
        "news_dict_li":news_list
    }
    return jsonify(errno =RET.OK,errmsg ="ok",data =data)

from flask import current_app
from flask import g
from flask import request
from flask import jsonify
from info.utils.response_code import RET

from info import constants, db
from info.models import News, Comment, CommentLike, User
from info.news import news_blue
from flask import render_template

from info.utils.common import user_login_data

#新闻详情页
@news_blue.route("/<int:news_id>")
@user_login_data
def new_detail(news_id):
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

    """
    详情页右上角用户登陆
    """
    # 获取用户登陆
    user = g.user
    """"""
    #获取新闻详情的数据
    news = News.query.get(news_id)

    """
       新闻收藏
           1:进入到新闻详情页之后，如果用户已收藏该新闻，则显示已收藏， is_collected = true
           2:点击则为取消收藏，反之点击收藏该新闻 is_collected = false
           3:如果要收藏新闻，那么收藏的动作是用户的行为，所以收藏这个地方用户必须user要登陆有值
           4:因为我们需要收藏的是新闻，新闻必须也要存在,所以news必须有值
           5:要收藏的新闻必须在我收藏的列表当中，这样就可以把is_collected　= true
       """
    is_collected = False
    if user:
        #  collection_news:当前用户收藏的所有新闻
        # 判断当前的这条新闻是否在我收藏的新闻列表当中, 如果在说明当前新闻已经被收藏, 如果新闻被收藏, 那么我们就可以is_collected = True
        if news in user.collection_news:
            is_collected = True

    """
        查询新闻评论的列表:
        1 首先获取新闻评论,那么需要根据新闻id进行查询出来所有的新闻
        2 根据评论的时间,进行倒叙
    """

    comments = Comment.query.filter(Comment.news_id == news.id).order_by(Comment.create_time.desc()).all()
    comment_list = []
    comment_likes = []
    comment_likes_ids = []

    if user:
        #获取所有的点赞的评论
        comment_likes = CommentLike.query.filter(CommentLike.user_id ==user.id).all()
        #通过列表推导式取出所有的点赞id
        comment_likes_ids = [comment_like.comment_id for comment_like in comment_likes]

    for comment in comments:
        # 取出评论的字典
        comment_dict = comment.to_dict()
        # 因为第一次进来,肯定所有的评论都没有点赞,所以默认值是false
        comment_dict["is_like"] = False
        # 如果当前的评论id在所有的点赞id里面，就说明该评论id就是点赞id
        if comment.id in comment_likes_ids:
            # 就置为True
            comment_dict["is_like"] = True
        # 把评论添加到评论列表
        comment_list.append(comment_dict)

    """
          关注:
          1 第一次进来肯定没有关注任何人,所以默认值是false
          2 必须登陆,判断user是否有值
          3 必须有作者,因为如果是爬虫爬过来的数据,那么就没有新闻作者
          4 如果当前新闻有作者,并且在我关注的人的列表当中,就说明我是新闻作者的粉丝,所以设置ture
          """
    # 当前登陆的用户是否关注当前新闻的作者
    is_followed = False
    if user:
        if news.user in user.followed:
            is_followed = True

    data = {
        "user_info":user.to_dict() if user else None,
        "news":news.to_dict(),
        "click_news_list": click_news_list,
        "is_collected":is_collected,
        "comments":comment_list,
        "is_followed":is_followed
    }
    return render_template("news/detail.html",data=data)

"""
新闻收藏
"""
@news_blue.route("/news_collect",methods=["GET","POST"])
@user_login_data
def news_collect():
    user = g.user
    #  因为需要收藏新闻,所以需要把新闻id传递过来,不然我不清楚要收藏哪条新闻
    news_id = request.json.get("news_id")
    # 用户传递过来的两个值：'collect', 'cancel_collect'，告诉我们是收藏还是取消
    action = request.json.get("action")
    #通过前段传递过来的id获取对应的新闻
    news = News.query.get(news_id)
    # 如果没有这条新闻，给用户一个提示
    if not news:
        return jsonify(errno=RET.NODATA,ermsg="没有这条新闻")
    # 因为收藏新闻是用户行为,所以必须得判断当前用户是否已经登陆,只有登陆才可以收藏新闻
    if not user:
        # SESSIONERR： 用户未登录
        return jsonify(errno=RET.SESSIONERR,errmsg="请登陆用户")
    # collect:表示收藏,判断如果用户传送过来的是collect就表示收藏
    if action == "collect":
        # 添加收藏
        user.collection_news.append(news)
    else:
        # 取消收藏
        user.collection_news.remove(news)
    # 提交
    db.session.commit()
    return jsonify(errno=RET.OK,errmsg="收藏成功")

"""
新闻评论
"""
@news_blue.route("/news_comment",methods=["GET","POST"])
@user_login_data
def news_comment():
    #新闻id
    news_id = request.json.get("news_id")
    #评论内容
    comment_str = request.json.get("comment")
    #回复的评论id
    parent_id = request.json.get("parent_id")
    # 根据用户传过来的新闻id从数据库中获取这条新闻
    news = News.query.get(news_id)

    # 新闻评论是一个用户行为,所以需要用户必须登陆,判断user必须有值
    user =g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR,errmsg="请登陆账号")
    # 新闻评论实际上就是把评论的内容提交到数据库
    comment = Comment()
    comment.user_id = user.id
    comment.news_id = news.id
    comment.content = comment_str
    # 因为不可能所有的评论都有父评论,所以在赋值的时候,需要判断
    if parent_id:
        comment.parent_id = parent_id
    # 评论是第一次进行提交,所以需要进行add操作,保存到数据库
    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        # 把错误信息保存到日志
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='保存评论数据失败')
    return jsonify(errno=RET.OK,errmsg="评论成功",data=comment.to_dict())


"""
评论点赞
"""
@news_blue.route("/comment_like",methods=["GET","POST"])
@user_login_data
def comment_like():
    """
   对新闻的评论进行点赞：
   1:点赞的行为都是人为操作，所以必须用户登陆
   2:点赞的行为是针对当前的评论，有评论才需要点赞，如果没有评论就不需要点赞，所以需要先把评论查询出来
   3:查询点赞评论，在查询点赞评论的时候，需要根据当前的评论id和用户id进行查询
   4:查询出来点缀着的评论之后，需要进行判断，当前这条评论是否有值,如果没有值才可以进行点赞，
     """
    # 评论id
    comment_id = request.json.get("comment_id")
    # 新闻id
    news_id =request.json.get("new_id")
    # add(点赞)，remove(取消点赞),通过用户传递的值确定执行什么操作
    action = request.json.get("action")

    # 判断用户是否登陆
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR,errmsg="请登陆账号")
    # 点赞的所有操作是基于评论，根据评论id查询出来评论
    comment = Comment.query.get(comment_id)

    # 如果用户传递的是add就执行点赞操作
    if action == "add":
        # 查询点赞信息
        comment_like = CommentLike.query.filter(CommentLike.comment_id==comment_id,CommentLike.user_id==user.id).first()
        # 判断查询出来的点赞是否有值,只有当点赞没有值的时候,才能进行点赞
        if not comment_like:
            comment_like = CommentLike()
            comment_like.comment_id = comment_id
            comment_like.user_id = user.id
            db.session.add(comment_like)
            comment.like_count +=1  #like_count:点赞条数
    # 否则用户传递的就是remove，就执行取消点赞
    else:
        comment_like = CommentLike.query.filter(CommentLike.comment_id==comment_id,CommentLike.user_id==user.id)
        # 判断查询出来的点赞是否有值,当点赞有值，就删除点赞
        if comment_like:
            db.session.delete(comment_like)
            comment.like_count -= 1
    #加了个错误拦截，如果出错就提交，如果出错就保存到错误日志，并执行回滚操作
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR,errmsg="操作失败")
    return jsonify(errno=RET.OK,errmsg="点赞成功")


# 关注与取消关注
@news_blue.route("/followed_user",methods=["GET","POST"])
@user_login_data
def followed_user():
    if not g.user:
        return jsonify(errno=RET.SESSIONERR,errmsg="用户未登陆")

    user_id = request.json.get("user_id")
    # action  指定两个值：'follow', 'unfollow'
    action = request.json.get("action")

    if not all([user_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if action not in ("follow", "unfollow"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 查询到关注的用户信息
    target_user = User.query.get(user_id)
    if not target_user:
        return jsonify(errno=RET.NODATA, errmsg="未查询到用户数据")

    # 根据不同操作做不同逻辑

    if action == "follow":
        if target_user.followers.filter(User.id == g.user.id).count() > 0:
            return jsonify(errno=RET.DATAEXIST, errmsg="当前已关注")
        target_user.followers.append(g.user)
    else:
        if target_user.followers.filter(User.id == g.user.id).count() > 0:
            target_user.followers.remove(g.user)

    # 保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据保存错误")

    return jsonify(errno=RET.OK, errmsg="操作成功")


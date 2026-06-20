"""
路由蓝图初始化 - MVC中的Controller层
Blueprint registration for all routes
"""
from flask import Flask


def register_blueprints(app: Flask):
    """
    注册所有路由蓝图

    Args:
        app: Flask 应用实例
    """
    # 引入各业务模块的蓝图
    from routes.blog import blog_bp
    from routes.category import category_bp
    from routes.upload import upload_bp
    from routes.auth import auth_bp
    from routes.comment import comment_bp
    from routes.post_io import post_io_bp

    # 注册蓝图
    app.register_blueprint(blog_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(comment_bp)
    app.register_blueprint(post_io_bp)

    # 后续如有其它模块（如 api_bp 等），在此继续注册

"""
Flask 应用入口 - 使用工厂模式创建应用实例
Application entry point using the application factory pattern.
"""
import markdown

from flask import Flask
from flask_migrate import Migrate

from config import get_config
from models import db
from routes import register_blueprints


# 创建 Flask-Migrate 实例
migrate = Migrate()


def create_app(config_object=None) -> Flask:
    """
    Flask 应用工厂函数

    Args:
        config_object: 配置类，默认为根据环境变量选择的配置

    Returns:
        Flask 应用实例
    """
    app = Flask(__name__)

    # 1. 加载配置
    app.config.from_object(config_object or get_config())

    # 2. 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)

    # 3. 注册自定义 Jinja2 过滤器
    @app.template_filter('markdown')
    def render_markdown(text):
        """将 Markdown 文本转换为 HTML"""
        return markdown.markdown(
            text,
            extensions=['fenced_code', 'tables', 'toc']
        )

    # 4. 注册蓝图
    register_blueprints(app)

    # 5. 首次运行时自动建表（生产环境建议使用 Flask-Migrate 管理迁移）
    with app.app_context():
        db.create_all()

    return app


# 仅在直接运行本文件时启动开发服务器
if __name__ == '__main__':
    application = create_app()
    application.run(
        host='127.0.0.1',
        port=5000,
        debug=application.config.get('DEBUG', False),
    )
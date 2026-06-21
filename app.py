"""
Flask 应用入口 - 使用工厂模式创建应用实例
Application entry point using the application factory pattern.
"""
import markdown

from flask import Flask, session
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_login import LoginManager

from config import get_config
from models import db, User
from routes import register_blueprints

# CSRF 保护
csrf = CSRFProtect()


# 创建 Flask-Migrate 实例
migrate = Migrate()


# Flask-Login 实例
login_manager = LoginManager()
login_manager.login_view = 'auth.login'              # 未登录时跳转的视图函数端点
login_manager.login_message = '请先登录后再访问该页面'
login_manager.login_message_category = 'warning'
login_manager.session_protection = 'strong'


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
    csrf.init_app(app)
    login_manager.init_app(app)

    # 2.1 CSRF 默认对所有 POST 表单生效；如需豁免特定蓝图/端点可在下方追加
    # 例: csrf.exempt(api_bp)  -- 不在此处全局设置，避免误暴露

    # 3. 全局上下文处理器 - 提供 csrf_token 到所有模板
    @app.context_processor
    def inject_globals():
        from flask_wtf.csrf import generate_csrf
        from datetime import datetime as _dt
        return dict(csrf_token=generate_csrf, now=_dt.utcnow())

    # 4. 注册自定义 Jinja2 过滤器
    @app.template_filter('markdown')
    def render_markdown(text):
        """将 Markdown 文本转换为 HTML（带 Pygments 代码高亮）"""
        return markdown.markdown(
            text or '',
            extensions=[
                'fenced_code',
                'tables',
                'toc',
                'codehilite',
                'sane_lists',
            ],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'guess_lang': False,
                    'use_pygments': True,
                },
            },
            output_format='html5',
        )

    # 4.5 注册 uploads/ 目录的静态访问（用于头像 / 上传文件）
    import os
    from flask import send_from_directory
    uploads_root = os.path.join(app.root_path, 'uploads')

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(uploads_root, filename)

    # 5. 注册蓝图
    register_blueprints(app)

    # 6. 首次运行时自动建表（生产环境建议使用 Flask-Migrate 管理迁移）
    with app.app_context():
        db.create_all()
        _ensure_default_admin()

    return app


# ---------------------------------------------------------------------------
# Flask-Login 用户加载回调
# ---------------------------------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    """根据 session 中的 user_id 加载用户对象，供 Flask-Login 使用"""
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def _ensure_default_admin() -> None:
    """若库内无任何 admin 账号，则自动创建一个默认管理员

    账号信息从环境变量读取，未设置时使用默认值（仅用于首次启动）。
    生产环境请通过 .env 或环境变量显式覆盖。
    """
    import os
    if User.query.filter_by(role=User.ROLE_ADMIN).first():
        return

    default_username = os.environ.get('ADMIN_USERNAME', 'admin')
    default_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    default_password = os.environ.get('ADMIN_PASSWORD', 'admin123456')

    # 已存在同名用户则跳过创建（避免冲突）
    if User.query.filter(
        (User.username == default_username) | (User.email == default_email)
    ).first():
        return

    admin = User(
        username=default_username,
        email=default_email,
        role=User.ROLE_ADMIN,
        bio='系统默认管理员（首次启动自动创建）',
    )
    admin.set_password(default_password)
    db.session.add(admin)
    db.session.commit()
    # 仅在控制台输出提示，不通过 flash 暴露给普通用户
    print(f'[init] 已创建默认管理员: {default_username} / {default_password} (请尽快修改密码)')


# 仅在直接运行本文件时启动开发服务器
if __name__ == '__main__':
    application = create_app()
    application.run(
        host='127.0.0.1',
        port=5000,
        debug=application.config.get('DEBUG', False),
    )
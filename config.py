"""
Flask应用配置模块
Configuration module for Flask application
"""
import os
from pathlib import Path

# 加载 .env 文件中的环境变量（可选依赖）
try:
    from dotenv import load_dotenv
    # 加载项目根目录下的 .env 文件
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # 如果未安装 python-dotenv，则直接使用系统环境变量
    pass

# 项目根目录（config.py 所在目录）
basedir = Path(__file__).parent.resolve()


class Config:
    """基础配置类"""

    # Flask 密钥（用于 session、CSRF 等）
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-please-change-in-production'

    # SQLAlchemy 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or 'sqlite:///blog.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # 调试模式
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1' or os.environ.get('FLASK_ENV') == 'development'

    # Flask-Migrate 配置
    SQLALCHEMY_MIGRATE_REPO = os.environ.get('SQLALCHEMY_MIGRATE_REPO')

    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    ALLOWED_EXTENSIONS = {'md', 'txt'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# 根据环境变量选择配置类
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': Config,
}


def get_config():
    """根据环境变量返回对应的配置类"""
    env = os.environ.get('FLASK_ENV', 'default')
    return config_map.get(env, Config)
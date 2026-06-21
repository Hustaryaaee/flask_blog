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

    # ---- AI 对话（OpenAI / Anthropic 兼容协议）----
    AI_ENABLED = os.environ.get('AI_ENABLED', 'false').lower() in ('1', 'true', 'yes')
    AI_API_KEY = os.environ.get('AI_API_KEY', '').strip()
    AI_BASE_URL = os.environ.get('AI_BASE_URL', 'https://api.openai.com/v1').strip()
    AI_MODEL = os.environ.get('AI_MODEL', 'gpt-3.5-turbo').strip()
    AI_SYSTEM_PROMPT = os.environ.get(
        'AI_SYSTEM_PROMPT',
        '你是一个友善的博客助手，擅长阅读文章、回答问题、总结要点、翻译与改写。',
    ).strip()
    AI_MAX_TOKENS = int(os.environ.get('AI_MAX_TOKENS', '800'))
    AI_TEMPERATURE = float(os.environ.get('AI_TEMPERATURE', '0.7'))
    AI_TIMEOUT = int(os.environ.get('AI_TIMEOUT', '30'))  # 秒
    # 协议类型：openai（默认）/ anthropic
    # 自动按 URL 推断：含 '/anthropic' 或 'anthropic.' → anthropic
    _proto = os.environ.get('AI_PROTOCOL', '').strip().lower()
    if _proto in ('openai', 'anthropic'):
        AI_PROTOCOL = _proto
    else:
        AI_PROTOCOL = 'anthropic' if 'anthropic' in AI_BASE_URL.lower() else 'openai'
    # 兜底：未配置 API key 时，给一个演示回复（"AI 演示模式"）
    AI_DEMO_MODE = not AI_API_KEY


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
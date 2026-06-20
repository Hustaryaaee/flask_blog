"""
数据模型模块 - MVC中的Model层
Database models for the blog application
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy 实例（在 app.py 中通过 init_app 初始化）
db = SQLAlchemy()


class Post(db.Model):
    """
    博客文章模型
    Blog Post Model

    字段说明:
        id:         主键，自增整数
        title:      文章标题，最大 200 字符
        content:    文章正文，TEXT 类型
        slug:       URL 友好的别名，全局唯一
        created_at: 创建时间
        updated_at: 最后更新时间
    """
    __tablename__ = 'posts'

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
        comment='主键ID'
    )

    title = db.Column(
        db.String(200),
        nullable=False,
        index=True,
        comment='文章标题'
    )

    content = db.Column(
        db.Text,
        nullable=False,
        comment='文章正文'
    )

    slug = db.Column(
        db.String(200),
        unique=True,
        nullable=False,
        index=True,
        comment='URL slug'
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment='创建时间'
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment='更新时间'
    )

    def __repr__(self):
        return f'<Post id={self.id} title={self.title!r}>'

    def to_dict(self):
        """将模型序列化为字典，便于 API 返回"""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'slug': self.slug,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
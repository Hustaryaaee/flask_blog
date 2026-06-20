"""
数据模型模块 - MVC中的Model层
Database models for the blog application
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy 实例（在 app.py 中通过 init_app 初始化）
db = SQLAlchemy()


# ---------------------------------------------------------------------------
# 关联表 (多对多)：文章 <-> 标签
# ---------------------------------------------------------------------------
post_tags = db.Table(
    'post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)


# ---------------------------------------------------------------------------
# 文章分类
# ---------------------------------------------------------------------------
class Category(db.Model):
    """
    文章分类
    Blog Category Model

    字段说明:
        id:          主键
        name:        分类名称（唯一）
        slug:        URL 友好的别名（唯一）
        description: 分类描述
        created_at:  创建时间
    """
    __tablename__ = 'categories'

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
        comment='主键ID'
    )

    name = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True,
        comment='分类名称'
    )

    slug = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True,
        comment='URL slug'
    )

    description = db.Column(
        db.String(200),
        nullable=True,
        comment='分类描述'
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment='创建时间'
    )

    # 关联：一对多 -> 文章
    posts = db.relationship(
        'Post',
        backref=db.backref('category', lazy=True),
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<Category id={self.id} name={self.name!r}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'post_count': self.posts.count() if self.posts is not None else 0,
        }


# ---------------------------------------------------------------------------
# 文章标签
# ---------------------------------------------------------------------------
class Tag(db.Model):
    """
    文章标签
    Blog Tag Model

    字段说明:
        id:         主键
        name:       标签名（唯一）
        slug:       URL 友好的别名（唯一）
        created_at: 创建时间
    """
    __tablename__ = 'tags'

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
        comment='主键ID'
    )

    name = db.Column(
        db.String(30),
        unique=True,
        nullable=False,
        index=True,
        comment='标签名称'
    )

    slug = db.Column(
        db.String(30),
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

    # 多对多 -> 文章
    posts = db.relationship(
        'Post',
        secondary=post_tags,
        lazy='dynamic',
        backref=db.backref('tags', lazy='dynamic')
    )

    def __repr__(self):
        return f'<Tag id={self.id} name={self.name!r}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# 博客文章
# ---------------------------------------------------------------------------
class Post(db.Model):
    """
    博客文章模型
    Blog Post Model

    字段说明:
        id:          主键，自增整数
        title:       文章标题，最大 200 字符
        content:     文章正文，TEXT 类型
        slug:        URL 友好的别名，全局唯一
        is_markdown: 是否 Markdown 格式
        created_at:  创建时间
        updated_at:  最后更新时间
        category_id: 所属分类外键（可空）
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

    is_markdown = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        comment='是否为 Markdown 格式'
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

    # 外键：分类（一对多）
    category_id = db.Column(
        db.Integer,
        db.ForeignKey('categories.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
        comment='所属分类 ID'
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
            'is_markdown': self.is_markdown,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'category_id': self.category_id,
            'category': self.category.to_dict() if self.category else None,
            'tags': [t.to_dict() for t in self.tags] if self.tags else [],
        }

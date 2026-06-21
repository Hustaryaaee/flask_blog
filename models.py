"""
数据模型模块 - MVC中的Model层
Database models for the blog application
"""
import re
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

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

    # 外键：作者（用户系统-阶段1新增）
    author_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
        comment='作者用户 ID'
    )

    # ---------- 阶段2：封面图 / 摘要 / SEO / 状态 / 定时发布 ----------
    cover_image = db.Column(
        db.String(500), nullable=True,
        comment='封面图 URL'
    )

    excerpt = db.Column(
        db.String(500), nullable=True,
        comment='摘要（可手动填写，未填则自动从正文截取）'
    )

    seo_title = db.Column(
        db.String(200), nullable=True,
        comment='SEO 标题（未填则用 title）'
    )

    seo_description = db.Column(
        db.String(300), nullable=True,
        comment='SEO 描述（meta description）'
    )

    seo_keywords = db.Column(
        db.String(200), nullable=True,
        comment='SEO 关键词（逗号分隔）'
    )

    # 状态：draft / scheduled / published / archived
    STATUS_DRAFT = 'draft'
    STATUS_SCHEDULED = 'scheduled'
    STATUS_PUBLISHED = 'published'
    STATUS_ARCHIVED = 'archived'
    STATUS_CHOICES = (STATUS_DRAFT, STATUS_SCHEDULED, STATUS_PUBLISHED, STATUS_ARCHIVED)

    status = db.Column(
        db.String(20), nullable=False, default=STATUS_PUBLISHED, index=True,
        comment='状态: draft/scheduled/published/archived'
    )

    published_at = db.Column(
        db.DateTime, nullable=True, index=True,
        comment='发布时间（可定时）'
    )

    view_count = db.Column(
        db.Integer, nullable=False, default=0,
        comment='浏览次数'
    )

    # ---------- 阶段2：版本历史 ----------
    revision = db.Column(
        db.Integer, nullable=False, default=1,
        comment='当前版本号'
    )

    def __repr__(self):
        return f'<Post id={self.id} title={self.title!r}>'

    @property
    def author(self):
        """向后兼容模板中的 post.author 字段"""
        return self.author_user.username if self.author_user else None

    @property
    def effective_seo_title(self) -> str:
        return self.seo_title or self.title

    @property
    def effective_seo_description(self) -> str:
        if self.seo_description:
            return self.seo_description
        if self.excerpt:
            return self.excerpt
        # 从 content 截前 160 字（去除 Markdown/HTML 标记）
        plain = re.sub(r'<[^>]+>', '', self.content or '')
        plain = re.sub(r'[#>*_`\-!\[\]\(\)]', '', plain)
        plain = re.sub(r'\s+', ' ', plain).strip()
        return plain[:160]

    @property
    def effective_seo_keywords(self) -> str:
        if self.seo_keywords:
            return self.seo_keywords
        names = [t.name for t in self.tags] if self.tags else []
        if self.category:
            names.insert(0, self.category.name)
        return ', '.join(names)

    def is_visible(self) -> bool:
        """是否对外可见：已发布 + 到达发布时间"""
        if self.status != self.STATUS_PUBLISHED:
            return False
        if self.published_at and self.published_at > datetime.utcnow():
            return False
        return True

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
            'author_id': self.author_id,
            'author': self.author_user.username if self.author_user else None,
            # 阶段2
            'cover_image': self.cover_image,
            'excerpt': self.excerpt,
            'seo_title': self.seo_title,
            'seo_description': self.seo_description,
            'seo_keywords': self.seo_keywords,
            'status': self.status,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'view_count': self.view_count,
            'revision': self.revision,
        }


# ---------------------------------------------------------------------------
# 评论（阶段3新增）
# ---------------------------------------------------------------------------
class Comment(db.Model):
    """
    文章评论 - 支持登录用户与游客、回复嵌套、待审核/已审核/垃圾
    """
    __tablename__ = 'comments'

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_SPAM = 'spam'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='主键ID')
    post_id = db.Column(
        db.Integer,
        db.ForeignKey('posts.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment='所属文章',
    )
    author_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
        comment='评论者（登录用户）',
    )
    guest_name = db.Column(db.String(50), nullable=True, comment='游客昵称')
    guest_email = db.Column(db.String(120), nullable=True, comment='游客邮箱')
    content = db.Column(db.Text, nullable=False, comment='评论内容')
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey('comments.id', ondelete='CASCADE'),
        nullable=True,
        index=True,
        comment='父评论 ID（回复）',
    )
    status = db.Column(
        db.String(20),
        nullable=False,
        default=STATUS_APPROVED,
        index=True,
        comment='pending/approved/spam',
    )
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    # 关联
    post = db.relationship('Post', backref=db.backref('comments', lazy='dynamic'))
    author = db.relationship('User', foreign_keys=[author_id])
    replies = db.relationship(
        'Comment',
        backref=db.backref('parent', remote_side=[id]),
        cascade='all, delete-orphan',
    )

    @property
    def display_name(self) -> str:
        if self.author:
            return self.author.username
        return self.guest_name or '匿名'

    @property
    def avatar(self) -> str:
        if self.author:
            return self.author.avatar()
        return f'https://api.dicebear.com/7.x/identicon/svg?seed={self.guest_name or "guest"}'

    def to_dict(self):
        return {
            'id': self.id,
            'post_id': self.post_id,
            'display_name': self.display_name,
            'author_id': self.author_id,
            'content': self.content,
            'parent_id': self.parent_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Comment id={self.id} post_id={self.post_id} by={self.display_name!r}>'


# ---------------------------------------------------------------------------
# 文章版本历史（阶段2新增）
# ---------------------------------------------------------------------------
class PostHistory(db.Model):
    """
    文章版本快照 - 每次保存自动留痕
    """
    __tablename__ = 'post_histories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(
        db.Integer,
        db.ForeignKey('posts.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    revision = db.Column(db.Integer, nullable=False, comment='版本号')
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.String(500), nullable=True)
    cover_image = db.Column(db.String(500), nullable=True)
    saved_by_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
    )
    saved_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    note = db.Column(db.String(200), nullable=True, comment='版本说明')

    # 关联
    post = db.relationship('Post', backref=db.backref('histories', lazy='dynamic', order_by='desc(PostHistory.revision)'))
    saved_by = db.relationship('User', foreign_keys=[saved_by_id])

    def __repr__(self):
        return f'<PostHistory post_id={self.post_id} rev={self.revision}>'

    def to_dict(self):
        return {
            'id': self.id,
            'post_id': self.post_id,
            'revision': self.revision,
            'title': self.title,
            'content': self.content,
            'excerpt': self.excerpt,
            'cover_image': self.cover_image,
            'saved_by': self.saved_by.username if self.saved_by else None,
            'saved_at': self.saved_at.isoformat() if self.saved_at else None,
            'note': self.note,
        }


# ---------------------------------------------------------------------------
# 用户（用户系统-阶段1新增）
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    """
    用户模型

    字段说明:
        id:            主键
        username:      用户名（唯一，2-30字符）
        email:         邮箱（唯一）
        password_hash: 密码哈希（不存明文）
        role:          角色 - admin / author / reader
        avatar_url:    头像 URL（默认使用首字母）
        bio:           个人简介
        created_at:    注册时间
        last_login:    最后登录时间
        is_active:     账号是否启用（Flask-Login 要求）
    """
    __tablename__ = 'users'

    # 角色常量
    ROLE_ADMIN = 'admin'
    ROLE_AUTHOR = 'author'
    ROLE_READER = 'reader'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, comment='主键ID')

    username = db.Column(
        db.String(30), unique=True, nullable=False, index=True, comment='用户名'
    )

    email = db.Column(
        db.String(120), unique=True, nullable=False, index=True, comment='邮箱'
    )

    password_hash = db.Column(
        db.String(255), nullable=False, comment='密码哈希'
    )

    role = db.Column(
        db.String(20), nullable=False, default=ROLE_READER, index=True,
        comment='角色:admin/author/reader'
    )

    avatar_url = db.Column(
        db.String(255), nullable=True, comment='头像 URL'
    )

    bio = db.Column(
        db.String(300), nullable=True, comment='个人简介'
    )

    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, comment='注册时间'
    )

    last_login = db.Column(
        db.DateTime, nullable=True, comment='最后登录时间'
    )

    is_active = db.Column(
        db.Boolean, nullable=False, default=True, comment='账号是否启用'
    )

    # 关联：作者一对多 -> 文章
    posts = db.relationship(
        'Post',
        backref=db.backref('author_user', lazy=True),
        lazy='dynamic',
        foreign_keys='Post.author_id',
    )

    # ---------- 密码处理 ----------
    def set_password(self, password: str) -> None:
        """设置密码（自动哈希）"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """校验密码"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    # ---------- 角色判断 ----------
    def is_admin(self) -> bool:
        return self.role == self.ROLE_ADMIN

    def is_author(self) -> bool:
        return self.role in (self.ROLE_ADMIN, self.ROLE_AUTHOR)

    # ---------- 头像默认 ----------
    def avatar(self) -> str:
        """返回头像 URL；无自定义头像时使用首字母占位"""
        if self.avatar_url:
            return self.avatar_url
        # 使用 DiceBear 生成首字母风格头像（纯前端服务，无需密钥）
        seed = self.username or 'user'
        return f'https://api.dicebear.com/7.x/initials/svg?seed={seed}'

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'avatar': self.avatar(),
            'bio': self.bio,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active,
        }

    def __repr__(self):
        return f'<User id={self.id} username={self.username!r} role={self.role!r}>'


# ---------------------------------------------------------------------------
# AI 对话（阶段6新增）
# ---------------------------------------------------------------------------
class ChatSession(db.Model):
    """
    AI 对话会话。
    关联到 user（必填）和可选 post（"问 AI 关于本文"模式）。
    title 默认为首条用户消息前 30 字。
    """
    __tablename__ = 'chat_sessions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    post_id = db.Column(
        db.Integer,
        db.ForeignKey('posts.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
        comment='关联文章（问 AI 关于本文）',
    )
    title = db.Column(db.String(120), nullable=False, default='新对话')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow,
    )

    user = db.relationship('User', backref=db.backref('chat_sessions', lazy='dynamic'))
    post = db.relationship('Post', backref=db.backref('chat_sessions', lazy='dynamic'))
    messages = db.relationship(
        'ChatMessage',
        backref='session',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='ChatMessage.created_at',
    )

    def __repr__(self):
        return f'<ChatSession id={self.id} user_id={self.user_id} title={self.title!r}>'


class ChatMessage(db.Model):
    """
    单条对话消息：role=user|assistant|system。
    """
    __tablename__ = 'chat_messages'

    ROLE_USER = 'user'
    ROLE_ASSISTANT = 'assistant'
    ROLE_SYSTEM = 'system'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey('chat_sessions.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    # 统计：tokens（可选）
    prompt_tokens = db.Column(db.Integer, nullable=True)
    completion_tokens = db.Column(db.Integer, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<ChatMessage id={self.id} role={self.role}>'

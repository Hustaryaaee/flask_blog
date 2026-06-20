"""
博客业务路由 - 文章 CRUD
Blog routes: list, detail, create, edit, delete
"""
import re
from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort
)

from models import db, Post

# 创建博客蓝图
blog_bp = Blueprint('blog', __name__)


# ----------------------------- 工具函数 -----------------------------

def _generate_slug(title: str) -> str:
    """根据标题生成 URL 友好的 slug"""
    # 仅保留字母数字、下划线、空格和连字符
    slug = re.sub(r'[^\w\s-]', '', title.lower().strip(), flags=re.UNICODE)
    # 将空格和多个连字符合并为单个连字符
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    # 默认回退方案
    if not slug:
        slug = f'post-{int(datetime.utcnow().timestamp())}'
    return slug[:200]  # 防止超过字段长度


def _generate_unique_slug(title: str, exclude_post_id: int = None) -> str:
    """
    生成全局唯一的 slug
    如果已存在，则追加数字后缀 -1, -2, ...
    """
    base_slug = _generate_slug(title)
    slug = base_slug
    counter = 1

    while True:
        query = Post.query.filter(Post.slug == slug)
        # 编辑文章时排除自身
        if exclude_post_id is not None:
            query = query.filter(Post.id != exclude_post_id)
        if query.first() is None:
            return slug
        counter += 1
        slug = f'{base_slug}-{counter}'


# ----------------------------- 路由视图 -----------------------------

@blog_bp.route('/', methods=['GET'])
def index():
    """
    GET /
    文章列表页：按创建时间倒序展示所有文章
    """
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts)


@blog_bp.route('/post/<string:slug>', methods=['GET'])
def detail(slug):
    """
    GET /post/<slug>
    文章详情页
    """
    post = Post.query.filter_by(slug=slug).first_or_404()
    return render_template('detail.html', post=post)


@blog_bp.route('/create', methods=['GET', 'POST'])
def create():
    """
    GET  /create  - 显示创建文章表单
    POST /create  - 提交创建文章
    """
    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        content = (request.form.get('content') or '').strip()

        # 基础校验
        if not title or not content:
            flash('标题和内容不能为空', 'error')
            return render_template('create.html', title=title, content=content)

        if len(title) > 200:
            flash('标题长度不能超过 200 字符', 'error')
            return render_template('create.html', title=title, content=content)

        # 构造模型
        post = Post(
            title=title,
            content=content,
            slug=_generate_unique_slug(title),
        )

        try:
            db.session.add(post)
            db.session.commit()
            flash('文章创建成功', 'success')
            return redirect(url_for('blog.detail', slug=post.slug))
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            flash(f'创建失败: {exc}', 'error')
            return render_template('create.html', title=title, content=content)

    # GET 请求，渲染空表单
    return render_template('create.html')


@blog_bp.route('/edit/<int:post_id>', methods=['GET', 'POST'])
def edit(post_id):
    """
    GET  /edit/<id>  - 显示编辑表单
    POST /edit/<id>  - 提交编辑
    """
    post = Post.query.get_or_404(post_id)

    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        content = (request.form.get('content') or '').strip()

        if not title or not content:
            flash('标题和内容不能为空', 'error')
            return render_template('edit.html', post=post)

        if len(title) > 200:
            flash('标题长度不能超过 200 字符', 'error')
            return render_template('edit.html', post=post)

        # 若标题变化则重新生成 slug
        if title != post.title:
            post.slug = _generate_unique_slug(title, exclude_post_id=post.id)
        post.title = title
        post.content = content

        try:
            db.session.commit()
            flash('文章更新成功', 'success')
            return redirect(url_for('blog.detail', slug=post.slug))
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            flash(f'更新失败: {exc}', 'error')
            return render_template('edit.html', post=post)

    # GET 请求，渲染已有数据的表单
    return render_template('edit.html', post=post)


@blog_bp.route('/delete/<int:post_id>', methods=['POST'])
def delete(post_id):
    """
    POST /delete/<id>
    删除文章（仅接受 POST，避免误删）
    """
    post = Post.query.get_or_404(post_id)

    try:
        db.session.delete(post)
        db.session.commit()
        flash('文章删除成功', 'success')
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        flash(f'删除失败: {exc}', 'error')

    return redirect(url_for('blog.index'))


# ----------------------------- 错误处理 -----------------------------

@blog_bp.app_errorhandler(404)
def page_not_found(error):  # noqa: ARG001
    return render_template('404.html'), 404
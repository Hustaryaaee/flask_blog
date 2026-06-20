"""
评论路由 - 阶段3
"""
import re

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
)
from flask_login import login_required, current_user

from models import db, Comment, Post

comment_bp = Blueprint('comment', __name__, url_prefix='/comment')

GUEST_NAME_RE = r'^[\w\-\u4e00-\u9fa5]{2,30}$'


def _clean(text: str, max_len: int = 2000) -> str:
    text = (text or '').strip()
    # 去危险标签
    text = re.sub(r'<[^>]+>', '', text)
    return text[:max_len]


@comment_bp.route('/post/<int:post_id>/create', methods=['POST'])
def create(post_id):
    """
    POST /comment/post/<id>/create
    提交评论（登录用户或游客均可）
    """
    post = Post.query.get_or_404(post_id)
    if not post.is_visible():
        abort(404)

    content = _clean(request.form.get('content', ''))
    parent_id = request.form.get('parent_id', type=int)

    if not content:
        flash('评论内容不能为空', 'error')
        return redirect(url_for('blog.detail', slug=post.slug) + '#comments')

    if len(content) < 2:
        flash('评论内容太短', 'error')
        return redirect(url_for('blog.detail', slug=post.slug) + '#comments')

    # 校验父评论
    parent = None
    if parent_id:
        parent = Comment.query.get(parent_id)
        if parent is None or parent.post_id != post.id:
            parent = None

    # 登录用户用 author_id；游客用 guest_name + guest_email
    author_id = None
    guest_name = None
    guest_email = None
    if current_user.is_authenticated:
        author_id = current_user.id
    else:
        guest_name = (request.form.get('guest_name') or '').strip()[:50]
        if not re.match(GUEST_NAME_RE, guest_name):
            flash('昵称需为 2-30 位字母/数字/中文/下划线', 'error')
            return redirect(url_for('blog.detail', slug=post.slug) + '#comments')
        guest_email = (request.form.get('guest_email') or '').strip()[:120] or None

    # 简单垃圾过滤：包含链接视为待审
    status = Comment.STATUS_PENDING if re.search(r'https?://', content) else Comment.STATUS_APPROVED

    c = Comment(
        post_id=post.id,
        author_id=author_id,
        guest_name=guest_name,
        guest_email=guest_email,
        content=content,
        parent_id=parent.id if parent else None,
        status=status,
    )
    try:
        db.session.add(c)
        db.session.commit()
        if status == Comment.STATUS_PENDING:
            flash('评论已提交，等待审核', 'info')
        else:
            flash('评论已发布', 'success')
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        flash(f'评论失败: {exc}', 'error')
    return redirect(url_for('blog.detail', slug=post.slug) + '#comments')


@comment_bp.route('/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete(comment_id):
    """POST /comment/<id>/delete - 作者/管理员/评论作者本人可删除"""
    c = Comment.query.get_or_404(comment_id)
    is_commenter = (c.author_id and c.author_id == current_user.id)
    is_post_author = (c.post and c.post.author_id == current_user.id)
    if not (is_commenter or is_post_author or current_user.is_admin()):
        flash('没有权限删除该评论', 'error')
        return redirect(url_for('blog.detail', slug=c.post.slug))

    slug = c.post.slug
    try:
        db.session.delete(c)
        db.session.commit()
        flash('评论已删除', 'success')
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        flash(f'删除失败: {exc}', 'error')
    return redirect(url_for('blog.detail', slug=slug) + '#comments')


@comment_bp.route('/<int:comment_id>/moderate', methods=['POST'])
@login_required
def moderate(comment_id):
    """POST /comment/<id>/moderate - 管理员可改状态"""
    if not current_user.is_admin():
        abort(403)
    c = Comment.query.get_or_404(comment_id)
    new_status = request.form.get('status')
    if new_status not in (Comment.STATUS_PENDING, Comment.STATUS_APPROVED, Comment.STATUS_SPAM):
        flash('无效状态', 'error')
        return redirect(url_for('blog.detail', slug=c.post.slug) + '#comments')
    c.status = new_status
    db.session.commit()
    flash(f'评论状态已设为 {new_status}', 'success')
    return redirect(url_for('blog.detail', slug=c.post.slug) + '#comments')

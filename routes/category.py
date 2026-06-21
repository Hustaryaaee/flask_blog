"""
分类/标签 路由 - 公共浏览与 JSON API
Category & Tag routes: public list pages + JSON API only

说明：分类/标签不是独立的管理对象，而是文章的字段。
本模块只提供公共浏览（按分类/标签查看文章）和工具 API（自动补全）。
如需创建/编辑/删除，请在写文章页面直接填写即可（routes/blog.py 会自动 upsert）。
"""
import re
from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort, jsonify
)

from models import db, Category, Tag, Post

# 分类/标签 蓝图
category_bp = Blueprint('category', __name__)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _generate_slug(name: str) -> str:
    """根据名称生成 URL 友好的 slug"""
    if not name:
        return ''
    slug = re.sub(r'[^\w\s-]', '', name.lower().strip(), flags=re.UNICODE)
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    return slug


def _generate_unique_slug(name: str, model, exclude_id: int = None) -> str:
    """
    生成全局唯一的 slug，如果已存在则追加数字后缀 -1, -2, ...
    """
    base_slug = _generate_slug(name)
    if not base_slug:
        base_slug = f'{model.__tablename__[:3]}-{int(datetime.utcnow().timestamp())}'

    slug = base_slug
    counter = 1
    while True:
        query = model.query.filter(model.slug == slug)
        if exclude_id is not None:
            query = query.filter(model.id != exclude_id)
        if query.first() is None:
            return slug
        counter += 1
        slug = f'{base_slug}-{counter}'


def _get_or_create_tags(tag_names):
    """
    解析字符串列表形式的标签名，返回已存在或新建的 Tag 对象列表
    """
    if not tag_names:
        return []

    result = []
    seen_slugs = set()
    for raw in tag_names:
        name = (raw or '').strip()
        if not name:
            continue
        slug = _generate_slug(name)
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        tag = Tag.query.filter(
            (Tag.slug == slug) | (Tag.name == name)
        ).first()
        if tag is None:
            tag = Tag(name=name, slug=slug)
            db.session.add(tag)
        result.append(tag)
    return result


# ---------------------------------------------------------------------------
# 公共浏览：按分类/标签筛选文章
# ---------------------------------------------------------------------------
@category_bp.route('/category/<string:slug>', methods=['GET'])
def category_posts(slug):
    """
    GET /category/<slug>
    按分类查看文章
    """
    category = Category.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)

    pagination = (
        Post.query
        .filter(Post.category_id == category.id)
        .order_by(Post.created_at.desc())
        .paginate(page=page, per_page=10, error_out=False)
    )

    return render_template(
        'category.html',
        category=category,
        posts=pagination.items,
        pagination=pagination,
    )


@category_bp.route('/tag/<string:slug>', methods=['GET'])
def tag_posts(slug):
    """
    GET /tag/<slug>
    按标签查看文章
    """
    tag = Tag.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)

    pagination = (
        Post.query
        .filter(Post.tags.any(Tag.id == tag.id))
        .order_by(Post.created_at.desc())
        .paginate(page=page, per_page=10, error_out=False)
    )

    return render_template(
        'tag.html',
        tag=tag,
        posts=pagination.items,
        pagination=pagination,
    )


# ---------------------------------------------------------------------------
# 侧边栏辅助：注入到所有模板
# ---------------------------------------------------------------------------
@category_bp.app_context_processor
def inject_sidebar_data():
    """向模板上下文注入分类列表与标签云数据"""
    categories = Category.query.order_by(Category.name.asc()).all()
    tags = Tag.query.order_by(Tag.name.asc()).all()
    return dict(all_categories=categories, all_tags=tags)


# ---------------------------------------------------------------------------
# 工具 API（供 create/edit 页面的标签自动补全使用）
# ---------------------------------------------------------------------------
@category_bp.route('/api/tags', methods=['GET'])
def api_tags():
    """
    GET /api/tags?q=xxx
    返回标签列表（JSON），用于前端自动补全
    """
    q = (request.args.get('q') or '').strip()
    query = Tag.query
    if q:
        query = query.filter(Tag.name.ilike(f'%{q}%'))
    tags = query.order_by(Tag.name.asc()).limit(20).all()
    return {
        'tags': [{'id': t.id, 'name': t.name, 'slug': t.slug} for t in tags]
    }


@category_bp.route('/api/categories', methods=['GET'])
def api_categories():
    """GET /api/categories - 返回全部分类（JSON）"""
    categories = Category.query.order_by(Category.name.asc()).all()
    return {
        'categories': [
            {
                'id': c.id,
                'name': c.name,
                'slug': c.slug,
                'description': c.description,
            } for c in categories
        ]
    }


# --------------------------------------------------------------------------
# JSON API - 分类 CRUD
# --------------------------------------------------------------------------
@category_bp.route('/api/category', methods=['POST'])
def api_create():
    """POST /api/category - 新建分类（JSON）"""
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()

    if not name:
        return jsonify({'error': '分类名称不能为空'}), 400
    if len(name) > 50:
        return jsonify({'error': '分类名称长度不能超过 50 字符'}), 400
    if Category.query.filter_by(name=name).first():
        return jsonify({'error': f'分类 "{name}" 已存在'}), 400

    try:
        category = Category(
            name=name,
            slug=_generate_unique_slug(name, Category),
            description=description or None,
        )
        db.session.add(category)
        db.session.commit()
        return jsonify({'id': category.id, 'name': category.name, 'slug': category.slug, 'description': category.description})
    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': f'创建失败: {exc}'}), 500


@category_bp.route('/api/category/<int:cat_id>', methods=['PUT'])
def api_update(cat_id):
    """PUT /api/category/<id> - 更新分类（JSON）"""
    category = Category.query.get_or_404(cat_id)
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()

    if not name:
        return jsonify({'error': '分类名称不能为空'}), 400
    if len(name) > 50:
        return jsonify({'error': '分类名称长度不能超过 50 字符'}), 400

    exists = Category.query.filter(Category.name == name, Category.id != category.id).first()
    if exists:
        return jsonify({'error': f'分类 "{name}" 已存在'}), 400

    try:
        category.name = name
        category.description = description or None
        if name != category.name or not category.slug:
            category.slug = _generate_unique_slug(name, Category, exclude_id=category.id)
        db.session.commit()
        return jsonify({'success': True, 'name': category.name, 'description': category.description})
    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': f'保存失败: {exc}'}), 500


@category_bp.route('/api/category/<int:cat_id>', methods=['DELETE'])
def api_delete(cat_id):
    """DELETE /api/category/<id> - 删除分类（JSON）"""
    category = Category.query.get_or_404(cat_id)

    if category.posts.count() > 0:
        return jsonify({'error': f'该分类仍包含 {category.posts.count()} 篇文章，无法删除'}), 400

    try:
        db.session.delete(category)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': f'删除失败: {exc}'}), 500


# --------------------------------------------------------------------------
# JSON API - 标签 CRUD
# --------------------------------------------------------------------------
@category_bp.route('/api/tag', methods=['POST'])
def api_create_tag():
    """POST /api/tag - 新建标签（JSON）"""
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()

    if not name:
        return jsonify({'error': '标签名称不能为空'}), 400
    if len(name) > 30:
        return jsonify({'error': '标签名称长度不能超过 30 字符'}), 400
    if Tag.query.filter_by(name=name).first():
        return jsonify({'error': f'标签 "{name}" 已存在'}), 400

    try:
        tag = Tag(
            name=name,
            slug=_generate_unique_slug(name, Tag),
        )
        db.session.add(tag)
        db.session.commit()
        return jsonify({'id': tag.id, 'name': tag.name, 'slug': tag.slug})
    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': f'创建失败: {exc}'}), 500


@category_bp.route('/api/tag', methods=['PUT'])
def api_update_tag():
    """PUT /api/tag?old=xxx - 更新标签（JSON）"""
    old_name = (request.args.get('old') or '').strip()
    data = request.get_json() or {}
    new_name = (data.get('name') or '').strip()

    if not old_name:
        return jsonify({'error': '缺少原标签名称'}), 400
    if not new_name:
        return jsonify({'error': '标签名称不能为空'}), 400
    if len(new_name) > 30:
        return jsonify({'error': '标签名称长度不能超过 30 字符'}), 400

    tag = Tag.query.filter_by(name=old_name).first()
    if not tag:
        return jsonify({'error': '标签不存在'}), 404
    if old_name != new_name and Tag.query.filter_by(name=new_name).first():
        return jsonify({'error': f'标签 "{new_name}" 已存在'}), 400

    try:
        tag.name = new_name
        tag.slug = _generate_unique_slug(new_name, Tag, exclude_id=tag.id)
        db.session.commit()
        return jsonify({'success': True, 'name': tag.name})
    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': f'保存失败: {exc}'}), 500

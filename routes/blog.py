"""
博客业务路由 - 文章 CRUD
Blog routes: list, detail, create, edit, delete
"""
import re
from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort
)
from flask_login import login_required, current_user
from urllib.parse import unquote

from models import db, Post, Category, Tag, PostHistory

# 创建博客蓝图
blog_bp = Blueprint('blog', __name__)


# ----------------------------- 工具函数 -----------------------------

def _resolve_category_by_name(name: str):
    """
    根据分类名称查找或新建分类。
    - 空字符串 / None → 返回 None（不分类）
    - 已存在 → 返回 Category
    - 不存在 → 自动创建并返回
    """
    if not name:
        return None
    name = name.strip()
    if not name:
        return None
    if len(name) > 50:
        name = name[:50]
    cat = Category.query.filter_by(name=name).first()
    if cat is not None:
        return cat
    # 创建
    base_slug = re.sub(r'[^\w\s-]', '', name.lower(), flags=re.UNICODE)
    base_slug = re.sub(r'[-\s]+', '-', base_slug).strip('-') or f'cat-{int(datetime.utcnow().timestamp())}'
    slug = base_slug
    n = 1
    while Category.query.filter_by(slug=slug).first():
        n += 1
        slug = f'{base_slug}-{n}'
    cat = Category(name=name, slug=slug)
    db.session.add(cat)
    db.session.flush()  # 不 commit，留给外层
    return cat


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


def _parse_tag_names(raw: str):
    """
    解析标签字符串为标签名列表
    支持中英文逗号 / 空格分隔
    """
    if not raw:
        return []
    names = re.split(r'[,，\s]+', raw)
    return [n.strip() for n in names if n.strip()]


def _slugify_tag(name: str) -> str:
    """生成 tag slug（与 category.py 保持一致）"""
    slug = re.sub(r'[^\w\s-]', '', name.lower().strip(), flags=re.UNICODE)
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    return slug


def _get_or_create_tags(tag_names):
    """
    根据标签名列表返回已存在或新建的 Tag 对象列表
    """
    if not tag_names:
        return []

    result = []
    seen_slugs = set()
    for raw in tag_names:
        name = (raw or '').strip()
        if not name or len(name) > 30:
            continue
        slug = _slugify_tag(name)
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


# ----------------------------- 工具: 阶段2 -----------------------------

def _parse_published_at(raw: str):
    """解析前端提交的发布时间；为空表示立即"""
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    # 支持 datetime-local 格式 YYYY-MM-DDTHH:MM
    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _save_history(post: Post, note: str = None) -> None:
    """保存一版历史快照（创建时不保存，仅编辑时留痕）"""
    hist = PostHistory(
        post_id=post.id,
        revision=post.revision,
        title=post.title,
        content=post.content,
        excerpt=post.excerpt,
        cover_image=post.cover_image,
        saved_by_id=current_user.id if current_user.is_authenticated else None,
        note=note or None,
    )
    db.session.add(hist)


# ----------------------------- 路由视图 -----------------------------

@blog_bp.route('/', methods=['GET'])
def index():
    """
    GET /
    文章列表页：仅展示可见文章（已发布 + 到达发布时间）
    作者/管理员可见自己的草稿、归档、定时文章
    """
    page = request.args.get('page', 1, type=int)
    q_str = request.args.get('q', '').strip()
    q = Post.query
    if not (current_user.is_authenticated):
        q = q.filter(Post.status == Post.STATUS_PUBLISHED)
        q = q.filter(
            (Post.published_at.is_(None)) | (Post.published_at <= datetime.utcnow())
        )
    # 已登录用户：额外展示自己的非公开内容
    if current_user.is_authenticated and not current_user.is_admin():
        from sqlalchemy import or_, and_
        q = q.filter(or_(
            and_(Post.status == Post.STATUS_PUBLISHED,
                 or_(Post.published_at.is_(None), Post.published_at <= datetime.utcnow())),
            Post.author_id == current_user.id,
        ))

    # 阶段3: 关键词搜索（标题或内容）
    if q_str:
        like = f'%{q_str}%'
        q = q.filter((Post.title.ilike(like)) | (Post.content.ilike(like)))

    pagination = q.order_by(Post.published_at.desc().nullslast(), Post.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    return render_template(
        'index.html',
        posts=pagination.items,
        pagination=pagination,
        q=q_str,
    )


@blog_bp.route('/search', methods=['GET'])
def search():
    """
    GET /search?q=xxx
    阶段3: 全文检索页（带高亮）
    """
    from models import Comment
    q_str = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    results = []
    pagination = None

    if q_str:
        like = f'%{q_str}%'
        query = Post.query.filter(Post.status == Post.STATUS_PUBLISHED).filter(
            (Post.title.ilike(like)) | (Post.content.ilike(like)) |
            (Post.excerpt.ilike(like))
        ).order_by(Post.published_at.desc().nullslast(), Post.created_at.desc())
        pagination = query.paginate(page=page, per_page=10, error_out=False)

        def _snippet(content, q_str, length=180):
            plain = re.sub(r'<[^>]+>', ' ', content or '')
            plain = re.sub(r'\s+', ' ', plain).strip()
            pos = plain.lower().find(q_str.lower())
            if pos < 0:
                return plain[:length] + ('...' if len(plain) > length else '')
            start = max(0, pos - 60)
            end = min(len(plain), pos + len(q_str) + 120)
            return ('...' if start > 0 else '') + plain[start:end] + ('...' if end < len(plain) else '')

        for p in pagination.items:
            results.append({
                'post': p,
                'snippet': _snippet(p.content, q_str),
            })

    return render_template('search.html', q=q_str, results=results, pagination=pagination)


@blog_bp.route('/archive', methods=['GET'])
def archive():
    """
    GET /archive
    阶段5: 按年月归档所有可见文章
    """
    from sqlalchemy import extract
    from collections import defaultdict
    # 公开可见的文章
    q = Post.query.filter(Post.status == Post.STATUS_PUBLISHED).filter(
        (Post.published_at.is_(None)) | (Post.published_at <= datetime.utcnow())
    )
    if current_user.is_authenticated and not current_user.is_admin():
        from sqlalchemy import or_, and_
        q = q.filter(or_(
            Post.author_id == current_user.id,
            Post.status == Post.STATUS_PUBLISHED,
        ))

    posts = q.order_by(
        Post.published_at.desc().nullslast(),
        Post.created_at.desc(),
    ).all()

    # 按年月分组
    grouped = defaultdict(list)
    total = len(posts)
    for p in posts:
        dt = p.published_at or p.created_at
        key = (dt.year, dt.month)
        grouped[key].append(p)

    # 转 (key, label, posts) 列表
    archive_data = []
    for (y, m), items in sorted(grouped.items(), key=lambda x: x[0], reverse=True):
        label = f'{y} 年 {m:02d} 月'
        archive_data.append({'year': y, 'month': m, 'label': label, 'posts': items})

    return render_template('archive.html', archive=archive_data, total=total)


@blog_bp.route('/post/<string:slug>', methods=['GET'])
def detail(slug):
    """
    GET /post/<slug>
    文章详情页
    """
    post = Post.query.filter_by(slug=slug).first_or_404()

    # 可见性：草稿 / 定时 / 归档 仅作者或管理员可见
    if not post.is_visible():
        if not (current_user.is_authenticated and (
                post.author_id == current_user.id or current_user.is_admin()
        )):
            abort(404)

    # 浏览计数（同一会话内不重复计数）
    if post.is_visible():
        from flask import session as _session
        seen_key = f'seen_post_{post.id}'
        if not _session.get(seen_key):
            _session[seen_key] = True
            post.view_count = (post.view_count or 0) + 1
            db.session.commit()

    # 阶段3: 评论（仅展示已通过审核的；管理员可看全部）
    from models import Comment
    visible_status = [Comment.STATUS_APPROVED]
    if current_user.is_authenticated and (current_user.is_admin() or post.author_id == current_user.id):
        visible_status.append(Comment.STATUS_PENDING)

    top_comments = (
        Comment.query
        .filter(
            Comment.post_id == post.id,
            Comment.parent_id.is_(None),
            Comment.status.in_(visible_status),
        )
        .order_by(Comment.created_at.asc())
        .all()
    )
    # 把每条顶级评论的回复也取出
    all_replies = (
        Comment.query
        .filter(
            Comment.post_id == post.id,
            Comment.parent_id.isnot(None),
            Comment.status.in_(visible_status),
        )
        .order_by(Comment.created_at.asc())
        .all()
    )
    replies_map = {}
    for r in all_replies:
        replies_map.setdefault(r.parent_id, []).append(r)
    comment_count = len(top_comments) + len(all_replies)

    # 阶段3: 搜索关键词高亮
    q = request.args.get('q', '').strip()

    return render_template(
        'post.html', post=post,
        top_comments=top_comments,
        replies_map=replies_map,
        comment_count=comment_count,
        q=q,
    )


@blog_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """
    GET  /create  - 显示创建文章表单
    POST /create  - 提交创建文章
    """
    categories = Category.query.order_by(Category.name.asc()).all()
    all_tags = Tag.query.order_by(Tag.name.asc()).all()

    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        content = (request.form.get('content') or '').strip()
        category_name = (request.form.get('category_name') or '').strip()
        tag_names = _parse_tag_names(request.form.get('tags', ''))
        is_markdown = request.form.get('is_markdown') in ('1', 'on', 'true')

        # 阶段2字段
        status = request.form.get('status') or Post.STATUS_PUBLISHED
        if status not in Post.STATUS_CHOICES:
            status = Post.STATUS_PUBLISHED
        cover_image = (request.form.get('cover_image') or '').strip() or None
        excerpt = (request.form.get('excerpt') or '').strip() or None
        seo_title = (request.form.get('seo_title') or '').strip() or None
        seo_description = (request.form.get('seo_description') or '').strip() or None
        seo_keywords = (request.form.get('seo_keywords') or '').strip() or None
        published_at = _parse_published_at(request.form.get('published_at', ''))

        # 校验状态权限：仅 admin 可发布归档
        if status == Post.STATUS_ARCHIVED and not current_user.is_admin():
            flash('只有管理员可设置归档状态', 'error')
            status = Post.STATUS_PUBLISHED

        # 校验：必填
        if not title or not content:
            flash('标题和内容不能为空', 'error')
            return render_template(
                'create.html',
                title=title, content=content,
                category_name=category_name, tags_raw=request.form.get('tags', ''),
                categories=categories, all_tags=all_tags,
                status=status, cover_image=cover_image, excerpt=excerpt,
                seo_title=seo_title, seo_description=seo_description,
                seo_keywords=seo_keywords,
                published_at=request.form.get('published_at', ''),
                STATUS_CHOICES=Post.STATUS_CHOICES,
            )

        if len(title) > 200:
            flash('标题长度不能超过 200 字符', 'error')
            return render_template(
                'create.html',
                title=title, content=content,
                category_name=category_name, tags_raw=request.form.get('tags', ''),
                categories=categories, all_tags=all_tags,
                status=status, cover_image=cover_image, excerpt=excerpt,
                seo_title=seo_title, seo_description=seo_description,
                seo_keywords=seo_keywords,
                published_at=request.form.get('published_at', ''),
                STATUS_CHOICES=Post.STATUS_CHOICES,
            )

        # 解析分类（按名称 upsert）
        try:
            category = _resolve_category_by_name(category_name)
        except Exception as exc:
            db.session.rollback()
            flash(f'分类创建失败: {exc}', 'error')
            return render_template(
                'create.html',
                title=title, content=content,
                category_name=category_name, tags_raw=request.form.get('tags', ''),
                categories=categories, all_tags=all_tags,
                status=status, cover_image=cover_image, excerpt=excerpt,
                seo_title=seo_title, seo_description=seo_description,
                seo_keywords=seo_keywords,
                published_at=request.form.get('published_at', ''),
                STATUS_CHOICES=Post.STATUS_CHOICES,
            )

        # 构造模型
        post = Post(
            title=title,
            content=content,
            slug=_generate_unique_slug(title),
            is_markdown=is_markdown,
            category_id=category.id if category else None,
            author_id=current_user.id,
            status=status,
            cover_image=cover_image,
            excerpt=excerpt,
            seo_title=seo_title,
            seo_description=seo_description,
            seo_keywords=seo_keywords,
            published_at=published_at,
            revision=1,
        )
        # 处理标签（按名称自动 upsert）
        post.tags = _get_or_create_tags(tag_names)

        try:
            db.session.add(post)
            db.session.commit()
            flash('文章创建成功', 'success')
            return redirect(url_for('blog.detail', slug=post.slug))
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            flash(f'创建失败: {exc}', 'error')
            return render_template(
                'create.html',
                title=title, content=content,
                category_name=category_name, tags_raw=request.form.get('tags', ''),
                categories=categories, all_tags=all_tags,
                status=status, cover_image=cover_image, excerpt=excerpt,
                seo_title=seo_title, seo_description=seo_description,
                seo_keywords=seo_keywords,
                published_at=request.form.get('published_at', ''),
                STATUS_CHOICES=Post.STATUS_CHOICES,
            )

    # GET 请求，渲染空表单 - 支持从 URL 参数预填 (来自 upload 等场景)
    prefill_title = unquote(request.args.get('title', '')).strip()
    prefill_content = unquote(request.args.get('content', ''))
    prefill_is_markdown = request.args.get('is_markdown', '') in ('1', 'true')
    prefill_cover = unquote(request.args.get('cover_image', '')).strip() or None
    prefill_excerpt = unquote(request.args.get('excerpt', '')).strip() or None
    prefill_tags = unquote(request.args.get('tags', '')).strip()
    prefill_category = unquote(request.args.get('category', '')).strip()

    if prefill_content:
        flash('已从上传文件预填内容,请编辑后发布', 'info')

    return render_template(
        'create.html',
        title=prefill_title,
        content=prefill_content,
        is_markdown=prefill_is_markdown,
        tags_raw=prefill_tags,
        category_name=prefill_category,
        categories=categories, all_tags=all_tags,
        status=Post.STATUS_PUBLISHED,
        cover_image=prefill_cover,
        excerpt=prefill_excerpt,
        seo_title=None, seo_description=None, seo_keywords=None,
        published_at='',
        STATUS_CHOICES=Post.STATUS_CHOICES,
    )


@blog_bp.route('/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit(post_id):
    """
    GET  /edit/<id>  - 显示编辑表单
    POST /edit/<id>  - 提交编辑
    """
    post = Post.query.get_or_404(post_id)

    # 权限校验：仅作者本人或管理员可编辑
    if post.author_id and post.author_id != current_user.id and not current_user.is_admin():
        flash('没有权限编辑该文章', 'error')
        return redirect(url_for('blog.detail', slug=post.slug))

    categories = Category.query.order_by(Category.name.asc()).all()
    all_tags = Tag.query.order_by(Tag.name.asc()).all()

    if request.method == 'POST':
        title = (request.form.get('title') or '').strip()
        content = (request.form.get('content') or '').strip()
        category_name = (request.form.get('category_name') or '').strip()
        tag_names = _parse_tag_names(request.form.get('tags', ''))
        is_markdown = request.form.get('is_markdown') in ('1', 'on', 'true')

        # 阶段2字段
        new_status = request.form.get('status') or post.status
        if new_status not in Post.STATUS_CHOICES:
            new_status = post.status
        if new_status == Post.STATUS_ARCHIVED and not current_user.is_admin():
            flash('只有管理员可设置归档状态', 'error')
            new_status = post.status
        cover_image = (request.form.get('cover_image') or '').strip() or None
        excerpt = (request.form.get('excerpt') or '').strip() or None
        seo_title = (request.form.get('seo_title') or '').strip() or None
        seo_description = (request.form.get('seo_description') or '').strip() or None
        seo_keywords = (request.form.get('seo_keywords') or '').strip() or None
        published_at = _parse_published_at(request.form.get('published_at', ''))

        if not title or not content:
            flash('标题和内容不能为空', 'error')
            return render_template(
                'edit.html', post=post,
                categories=categories, all_tags=all_tags,
                category_name=category_name, tags_raw=request.form.get('tags', ''),
                STATUS_CHOICES=Post.STATUS_CHOICES,
            )

        if len(title) > 200:
            flash('标题长度不能超过 200 字符', 'error')
            return render_template(
                'edit.html', post=post,
                categories=categories, all_tags=all_tags,
                category_name=category_name, tags_raw=request.form.get('tags', ''),
                STATUS_CHOICES=Post.STATUS_CHOICES,
            )

        # 解析分类（按名称 upsert；空字符串 → 不分类）
        try:
            category = _resolve_category_by_name(category_name)
        except Exception as exc:
            db.session.rollback()
            flash(f'分类创建失败: {exc}', 'error')
            return render_template(
                'edit.html', post=post,
                categories=categories, all_tags=all_tags,
                category_name=category_name, tags_raw=request.form.get('tags', ''),
                STATUS_CHOICES=Post.STATUS_CHOICES,
            )

        # 保存历史快照（编辑前）
        _save_history(post, note=(request.form.get('revision_note') or '').strip() or None)

        # 若标题变化则重新生成 slug
        if title != post.title:
            post.slug = _generate_unique_slug(title, exclude_post_id=post.id)
        post.title = title
        post.content = content
        post.is_markdown = is_markdown
        post.category_id = category.id if category else None
        post.status = new_status
        post.cover_image = cover_image
        post.excerpt = excerpt
        post.seo_title = seo_title
        post.seo_description = seo_description
        post.seo_keywords = seo_keywords
        post.published_at = published_at
        post.revision = (post.revision or 1) + 1
        # 重新绑定标签（按名称自动 upsert）
        post.tags = _get_or_create_tags(tag_names)

        try:
            db.session.commit()
            flash(f'文章已更新至 v{post.revision}', 'success')
            return redirect(url_for('blog.detail', slug=post.slug))
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            flash(f'更新失败: {exc}', 'error')
            return render_template(
                'edit.html', post=post,
                categories=categories, all_tags=all_tags,
                category_name=category_name, tags_raw=request.form.get('tags', ''),
                STATUS_CHOICES=Post.STATUS_CHOICES,
            )

    # GET 请求，渲染已有数据的表单
    return render_template(
        'edit.html', post=post,
        categories=categories, all_tags=all_tags,
        category_name=(post.category.name if post.category else ''),
        tags_raw=(', '.join(t.name for t in post.tags) if post.tags else ''),
        STATUS_CHOICES=Post.STATUS_CHOICES,
    )


@blog_bp.route('/delete/<int:post_id>', methods=['POST'])
@login_required
def delete(post_id):
    """
    POST /delete/<id>
    删除文章（仅接受 POST，避免误删）
    """
    post = Post.query.get_or_404(post_id)

    # 权限校验：仅作者本人或管理员可删除
    if post.author_id and post.author_id != current_user.id and not current_user.is_admin():
        flash('没有权限删除该文章', 'error')
        return redirect(url_for('blog.detail', slug=post.slug))

    try:
        db.session.delete(post)
        db.session.commit()
        flash('文章删除成功', 'success')
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        flash(f'删除失败: {exc}', 'error')

    return redirect(url_for('blog.index'))


@blog_bp.route('/post/<int:post_id>/history', methods=['GET'])
@login_required
def history(post_id):
    """
    GET /post/<id>/history - 查看版本历史
    """
    post = Post.query.get_or_404(post_id)
    if post.author_id and post.author_id != current_user.id and not current_user.is_admin():
        flash('没有权限查看该文章历史', 'error')
        return redirect(url_for('blog.detail', slug=post.slug))
    histories = post.histories.limit(50).all()
    return render_template('history.html', post=post, histories=histories)


@blog_bp.route('/post/<int:post_id>/history/<int:revision>/restore', methods=['POST'])
@login_required
def restore_history(post_id, revision):
    """
    POST /post/<id>/history/<rev>/restore - 回滚到指定版本
    """
    post = Post.query.get_or_404(post_id)
    if post.author_id and post.author_id != current_user.id and not current_user.is_admin():
        flash('没有权限回滚该文章', 'error')
        return redirect(url_for('blog.detail', slug=post.slug))

    hist = PostHistory.query.filter_by(post_id=post.id, revision=revision).first_or_404()

    # 备份当前到历史
    _save_history(post, note=f'回滚前自动备份')

    # 恢复字段
    post.title = hist.title
    post.content = hist.content
    post.excerpt = hist.excerpt
    post.cover_image = hist.cover_image
    post.slug = _generate_unique_slug(hist.title, exclude_post_id=post.id)
    post.revision = (post.revision or 1) + 1
    # 标签按历史快照中的名字恢复（PostHistory 不存 tags，需要从快照字段读取）
    # 当前模型没有 history.tags 字段 → 从 content 解析 #tag 形式作为兜底
    fallback_tag_names = re.findall(r'#([\w\-\u4e00-\u9fa5]{1,30})', hist.content or '')
    post.tags = _get_or_create_tags(fallback_tag_names)

    try:
        db.session.commit()
        flash(f'已回滚到 v{revision}（当前 v{post.revision}）', 'success')
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        flash(f'回滚失败: {exc}', 'error')
    return redirect(url_for('blog.edit', post_id=post.id))


# ----------------------------- 错误处理 -----------------------------

@blog_bp.app_errorhandler(404)
def page_not_found(error):  # noqa: ARG001
    return render_template('404.html', error=error), 404


# ----------------------------- JSON API -----------------------------

@blog_bp.route('/api/tag', methods=['POST'])
def api_delete_tag():
    """POST /api/tag - 删除标签（按名称）"""
    from flask import jsonify
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()

    if not name:
        return jsonify({'error': '标签名称不能为空'}), 400

    tag = Tag.query.filter_by(name=name).first()
    if not tag:
        return jsonify({'error': '标签不存在'}), 404

    try:
        db.session.delete(tag)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as exc:
        db.session.rollback()
        return jsonify({'error': f'删除失败: {exc}'}), 500

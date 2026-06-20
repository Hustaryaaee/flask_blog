"""
阶段4: 文章导入/导出 (Markdown)
- /post/<id>/export.md  下载为 .md
- /post/<id>/export    下载为 zip（包含 markdown + 元数据）
- /import              上传 .md 文件 → 重定向到 /create 并预填内容
"""
import io
import re
import zipfile
from datetime import datetime

from flask import (
    Blueprint, send_file, redirect, url_for, request, flash, render_template,
    current_app, abort
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models import db, Post
from utils.file_handler import allowed_file  # noqa

MAX_IMPORT_BYTES = 16 * 1024 * 1024  # 16MB

post_io_bp = Blueprint('post_io', __name__)


def _post_to_markdown(post: Post, with_frontmatter: bool = True) -> str:
    """导出 Post 为 Markdown 字符串（带 YAML front-matter）"""
    if with_frontmatter:
        fm_lines = ['---']
        fm_lines.append(f'title: "{post.title}"')
        if post.slug:
            fm_lines.append(f'slug: "{post.slug}"')
        if post.category:
            fm_lines.append(f'category: "{post.category.name}"')
        if post.tags:
            fm_lines.append(f'tags: [{", ".join(t.name for t in post.tags)}]')
        if post.cover_image:
            fm_lines.append(f'cover_image: "{post.cover_image}"')
        if post.excerpt:
            fm_lines.append(f'excerpt: "{post.excerpt}"')
        if post.status:
            fm_lines.append(f'status: "{post.status}"')
        if post.published_at:
            fm_lines.append(f'published_at: "{post.published_at.isoformat()}"')
        fm_lines.append(f'created_at: "{post.created_at.isoformat() if post.created_at else ""}"')
        if post.author_user:
            fm_lines.append(f'author: "{post.author_user.username}"')
        fm_lines.append('---')
        fm_lines.append('')
        return '\n'.join(fm_lines) + '\n' + (post.content or '')
    return post.content or ''


@post_io_bp.route('/post/<int:post_id>/export.md', methods=['GET'])
def export_md(post_id):
    """下载单篇 Markdown（含 frontmatter）"""
    post = Post.query.get_or_404(post_id)
    # 权限：作者 / 管理员 / 已发布文章对所有人
    if post.status != Post.STATUS_PUBLISHED or not post.is_visible():
        if not (current_user.is_authenticated and (
                post.author_id == current_user.id or current_user.is_admin()
        )):
            abort(404)
    md = _post_to_markdown(post, with_frontmatter=True)
    fname = secure_filename((post.slug or f'post-{post.id}') + '.md') or f'post-{post.id}.md'
    return send_file(
        io.BytesIO(md.encode('utf-8')),
        mimetype='text/markdown; charset=utf-8',
        as_attachment=True,
        download_name=fname,
    )


@post_io_bp.route('/post/<int:post_id>/export.zip', methods=['GET'])
@login_required
def export_zip(post_id):
    """下载 zip（包含 md 与 meta json）"""
    post = Post.query.get_or_404(post_id)
    if post.author_id != current_user.id and not current_user.is_admin():
        abort(403)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            secure_filename((post.slug or f'post-{post.id}') + '.md'),
            _post_to_markdown(post, with_frontmatter=True),
        )
        import json
        zf.writestr('meta.json', json.dumps(post.to_dict(), ensure_ascii=False, indent=2))
    buf.seek(0)
    return send_file(
        buf,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'post-{post.id}.zip',
    )


# ----- 简单 YAML front-matter 解析（避免新增依赖） -----
def _parse_frontmatter(text: str):
    """返回 (meta_dict, content)"""
    if not text.startswith('---'):
        return {}, text
    parts = text.split('---', 2)
    if len(parts) < 3:
        return {}, text
    meta_block = parts[1]
    body = parts[2].lstrip('\n')
    meta = {}
    for line in meta_block.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' in line:
            k, v = line.split(':', 1)
            v = v.strip().strip('"').strip("'")
            # 解析 [a, b]
            if v.startswith('[') and v.endswith(']'):
                items = [s.strip().strip('"').strip("'") for s in v[1:-1].split(',') if s.strip()]
                meta[k.strip()] = items
            else:
                meta[k.strip()] = v
    return meta, body


@post_io_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_md():
    """
    GET  /import  - 上传页
    POST /import  - 解析上传文件 → 重定向到 /create 预填
    """
    if request.method == 'GET':
        return render_template('import.html')

    file = request.files.get('file')
    if not file or not file.filename:
        flash('请选择一个文件', 'error')
        return redirect(url_for('post_io.import_md'))

    if not allowed_file(file.filename, {'md', 'markdown', 'txt'}):
        flash('仅支持 .md / .markdown / .txt 文件', 'error')
        return redirect(url_for('post_io.import_md'))

    raw = file.read(MAX_IMPORT_BYTES + 1)
    if len(raw) > MAX_IMPORT_BYTES:
        flash(f'文件过大（>{MAX_IMPORT_BYTES//1024//1024}MB）', 'error')
        return redirect(url_for('post_io.import_md'))

    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        text = raw.decode('gbk', errors='replace')

    meta, content = _parse_frontmatter(text)
    title = meta.get('title') or _guess_title_from_filename(file.filename)
    tags_raw = meta.get('tags', '')
    if isinstance(tags_raw, list):
        tags_raw = ', '.join(tags_raw)

    flash('已解析 Markdown，可继续编辑后发布', 'info')
    params = {
        'title': title,
        'content': content,
        'is_markdown': '1',
        'tags': tags_raw,
    }
    if meta.get('cover_image'):
        params['cover_image'] = meta['cover_image']
    if meta.get('excerpt'):
        params['excerpt'] = meta['excerpt']

    qs = '&'.join(f'{k}={urllib_quote(v)}' for k, v in params.items() if v)
    return redirect(url_for('blog.create') + '?' + qs)


def urllib_quote(s):
    from urllib.parse import quote
    return quote(s, safe='')


def _guess_title_from_filename(name: str) -> str:
    base = re.sub(r'\.[^.]+$', '', name)
    base = base.replace('-', ' ').replace('_', ' ').strip()
    return base[:200] or '导入的文章'

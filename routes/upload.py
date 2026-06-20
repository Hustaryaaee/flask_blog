"""
Markdown 文件上传路由
Upload blueprint for uploading .md / .txt files
"""
from urllib.parse import quote

from flask import (
    Blueprint, render_template, request,
    flash, redirect, url_for,
)

from utils.file_handler import save_upload, read_markdown_file

# 创建上传蓝图
upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """
    GET  /upload - 显示上传页面
    POST /upload - 接收上传文件, 解析后跳转到创建文章页
    """
    if request.method == 'POST':
        file = request.files.get('file')

        if not file or file.filename == '':
            flash('请选择文件', 'error')
            return render_template('upload.html')

        filepath = save_upload(file)
        if filepath:
            content = read_markdown_file(filepath)
            # 提取标题: 优先取第一个以 # 开头的行, 否则使用文件名
            title = ''
            for line in content.split('\n'):
                stripped = line.strip()
                if stripped.startswith('#'):
                    title = stripped.lstrip('#').strip()
                    break
            if not title:
                # 回退到文件名 (去掉扩展名)
                title = file.filename.rsplit('.', 1)[0]

            flash(f'文件上传成功!已读取 {len(content)} 字符', 'success')
            # 通过 URL 参数预填 create 表单 (内容用 URL 安全编码)
            return redirect(url_for(
                'blog.create',
                title=title,
                content=quote(content, safe=''),
                is_markdown=1,
            ))
        else:
            flash('不支持的文件类型,仅支持 .md 和 .txt', 'error')

    return render_template('upload.html')

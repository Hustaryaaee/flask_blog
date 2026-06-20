"""
文件处理工具 - 文件上传、Markdown 读取等
File handling utilities for uploads and markdown reading.
"""
import os

from flask import current_app
from werkzeug.utils import secure_filename


def allowed_file(filename: str) -> bool:
    """
    检查文件扩展名是否在允许列表中

    Args:
        filename: 原始文件名

    Returns:
        bool - 文件类型是否允许
    """
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']
    )


def save_upload(file):
    """
    保存上传的文件到 UPLOAD_FOLDER

    Args:
        file: werkzeug FileStorage 对象

    Returns:
        str | None - 成功返回保存路径，失败返回 None
    """
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # 避免文件名冲突：同名文件追加时间戳
        upload_dir = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)

        filepath = os.path.join(upload_dir, filename)
        if os.path.exists(filepath):
            name, ext = os.path.splitext(filename)
            import time
            filename = f"{name}_{int(time.time())}{ext}"
            filepath = os.path.join(upload_dir, filename)

        file.save(filepath)
        return filepath
    return None


def read_markdown_file(filepath: str) -> str:
    """
    读取 Markdown 文件内容

    Args:
        filepath: 文件绝对路径

    Returns:
        str - 文件内容字符串
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

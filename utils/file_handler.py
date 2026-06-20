"""
文件处理工具 - 文件上传、Markdown 读取等
File handling utilities for uploads and markdown reading.
"""
import os
import time

from werkzeug.utils import secure_filename

# 默认允许的文件扩展名
ALLOWED_EXTENSIONS = {'md', 'txt'}


def allowed_file(filename: str, allowed_extensions: set = None) -> bool:
    """
    检查文件扩展名是否在允许列表中

    Args:
        filename: 原始文件名
        allowed_extensions: 允许的扩展名集合，默认使用 ALLOWED_EXTENSIONS

    Returns:
        bool - 文件类型是否允许
    """
    extensions = allowed_extensions or ALLOWED_EXTENSIONS
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in extensions
    )


def save_upload(file, upload_folder: str, allowed_extensions: set = None):
    """
    保存上传的文件到指定目录

    Args:
        file: werkzeug FileStorage 对象
        upload_folder: 上传目录路径
        allowed_extensions: 允许的扩展名集合

    Returns:
        str | None - 成功返回保存路径，失败返回 None
    """
    if file and allowed_file(file.filename, allowed_extensions):
        filename = secure_filename(file.filename)
        # 避免文件名冲突：同名文件追加时间戳
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, filename)
        if os.path.exists(filepath):
            name, ext = os.path.splitext(filename)
            filename = f"{name}_{int(time.time())}{ext}"
            filepath = os.path.join(upload_folder, filename)

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

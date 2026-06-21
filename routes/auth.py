"""
用户认证路由 - 注册、登录、登出、个人中心
Auth blueprint: register / login / logout / profile
"""
import re
from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, current_app, abort,
)
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
import os
import uuid

from models import db, User, Post
from werkzeug.utils import secure_filename

# 允许的头像格式
ALLOWED_AVATAR_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2MB

# 用户认证蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
USERNAME_RE = re.compile(r'^[A-Za-z0-9_\-]{2,30}$')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _is_safe_next_url(target: str) -> bool:
    """防止开放重定向：仅允许跳转到站内相对路径"""
    if not target:
        return False
    parsed = urlparse(target)
    # 仅接受相对路径（无 netloc / scheme）
    return not parsed.netloc and not parsed.scheme and target.startswith('/')


def _save_avatar(file_storage, user_id: int):
    """
    保存头像文件到 uploads/avatars/。
    返回 (ok: bool, info: str)
        - 成功：ok=True, info=最终 URL（形如 /uploads/avatars/<uuid>.<ext>）
        - 失败：ok=False, info=错误消息
    """
    if not file_storage or not file_storage.filename:
        return False, '未选择文件'

    # 取扩展名
    orig = file_storage.filename.lower()
    ext = orig.rsplit('.', 1)[-1] if '.' in orig else ''
    if ext not in ALLOWED_AVATAR_EXT:
        return False, f'仅支持 {", ".join(sorted(ALLOWED_AVATAR_EXT))} 格式'

    # 读字节判大小
    raw = file_storage.read()
    if len(raw) > MAX_AVATAR_SIZE:
        return False, f'文件过大（>{MAX_AVATAR_SIZE // 1024 // 1024}MB）'

    # 存盘目录
    folder = os.path.join(current_app.root_path, 'uploads', 'avatars')
    os.makedirs(folder, exist_ok=True)

    # 用 uuid 避免冲突 / 路径穿越
    fname = f'user-{user_id}-{uuid.uuid4().hex[:8]}.{ext}'
    fpath = os.path.join(folder, fname)

    with open(fpath, 'wb') as f:
        f.write(raw)

    return True, f'/uploads/avatars/{fname}'


def _validate_username(username: str) -> str | None:
    """校验用户名，返回错误信息或 None"""
    if not username:
        return '用户名不能为空'
    if len(username) < 2 or len(username) > 30:
        return '用户名长度需在 2-30 字符之间'
    if not USERNAME_RE.match(username):
        return '用户名仅允许字母、数字、下划线、连字符'
    return None


def _validate_email(email: str) -> str | None:
    if not email:
        return '邮箱不能为空'
    if len(email) > 120:
        return '邮箱长度不能超过 120 字符'
    if not EMAIL_RE.match(email):
        return '邮箱格式不正确'
    return None


def _validate_password(password: str) -> str | None:
    if not password:
        return '密码不能为空'
    if len(password) < 6:
        return '密码至少 6 个字符'
    if len(password) > 128:
        return '密码长度不能超过 128 字符'
    return None


# ---------------------------------------------------------------------------
# 注册
# ---------------------------------------------------------------------------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """GET /auth/register  显示注册表单
       POST /auth/register 创建新用户
    """
    if current_user.is_authenticated:
        return redirect(url_for('blog.index'))

    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        confirm = request.form.get('confirm_password') or ''

        # 校验
        for field, validator in (
            ('username', _validate_username(username)),
            ('email', _validate_email(email)),
            ('password', _validate_password(password)),
        ):
            if validator:
                flash(validator, 'error')
                return render_template(
                    'auth/register.html',
                    username=username, email=email,
                )

        if password != confirm:
            flash('两次输入的密码不一致', 'error')
            return render_template(
                'auth/register.html',
                username=username, email=email,
            )

        if User.query.filter_by(username=username).first():
            flash(f'用户名 "{username}" 已被占用', 'error')
            return render_template(
                'auth/register.html',
                username=username, email=email,
            )

        if User.query.filter_by(email=email).first():
            flash(f'邮箱 "{email}" 已被注册', 'error')
            return render_template(
                'auth/register.html',
                username=username, email=email,
            )

        # 默认角色：首个注册用户为 admin（覆盖自动创建逻辑），其余为 reader
        existing_count = User.query.count()
        user = User(
            username=username,
            email=email,
            role=User.ROLE_ADMIN if existing_count == 0 else User.ROLE_READER,
        )
        user.set_password(password)
        try:
            db.session.add(user)
            db.session.commit()
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            flash(f'注册失败: {exc}', 'error')
            return render_template(
                'auth/register.html',
                username=username, email=email,
            )

        # 自动登录
        login_user(user)
        flash(f'欢迎加入, {user.username}!', 'success')
        if user.is_admin() and existing_count == 0:
            flash('你是首个注册用户, 已自动获得管理员权限', 'info')
        return redirect(url_for('blog.index'))

    return render_template('auth/register.html')


# ---------------------------------------------------------------------------
# 登录
# ---------------------------------------------------------------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """GET /auth/login  显示登录表单
       POST /auth/login 验证并登录
    """
    if current_user.is_authenticated:
        return redirect(url_for('blog.index'))

    if request.method == 'POST':
        identifier = (request.form.get('identifier') or '').strip()
        password = request.form.get('password') or ''
        remember = request.form.get('remember') in ('1', 'on', 'true')
        next_url = request.form.get('next') or request.args.get('next')

        if not identifier or not password:
            flash('请输入账号与密码', 'error')
            return render_template(
                'auth/login.html',
                identifier=identifier, next_url=next_url,
            )

        # 支持用户名 / 邮箱登录
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if not user or not user.check_password(password):
            flash('账号或密码错误', 'error')
            return render_template(
                'auth/login.html',
                identifier=identifier, next_url=next_url,
            )

        if not user.is_active:
            flash('该账号已被禁用, 请联系管理员', 'error')
            return render_template(
                'auth/login.html',
                identifier=identifier, next_url=next_url,
            )

        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.session.commit()

        login_user(user, remember=remember)
        flash(f'欢迎回来, {user.username}!', 'success')

        # 安全跳转
        if next_url and _is_safe_next_url(next_url):
            return redirect(next_url)
        return redirect(url_for('blog.index'))

    return render_template(
        'auth/login.html',
        next_url=request.args.get('next'),
    )


# ---------------------------------------------------------------------------
# 登出
# ---------------------------------------------------------------------------
@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """登出当前账号"""
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('blog.index'))


# ---------------------------------------------------------------------------
# 个人中心
# ---------------------------------------------------------------------------
@auth_bp.route('/profile', methods=['GET'])
@auth_bp.route('/profile/<string:username>', methods=['GET'])
def profile(username: str = None):
    """GET /auth/profile - 个人中心（默认查看自己）"""
    if username:
        user = User.query.filter_by(username=username).first_or_404()
    else:
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login', next=request.full_path))
        user = current_user

    # 查询该用户的文章
    page = request.args.get('page', 1, type=int)
    pagination = (
        Post.query
        .filter(Post.author_id == user.id)
        .order_by(Post.created_at.desc())
        .paginate(page=page, per_page=10, error_out=False)
    )

    return render_template(
        'auth/profile.html',
        profile_user=user,
        is_owner=(current_user.is_authenticated and current_user.id == user.id),
        posts=pagination.items,
        pagination=pagination,
    )


@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def profile_edit():
    """GET/POST /auth/profile/edit - 编辑个人简介 / 头像"""
    if request.method == 'POST':
        bio = (request.form.get('bio') or '').strip()
        avatar_url = (request.form.get('avatar_url') or '').strip()

        if len(bio) > 300:
            flash('个人简介不能超过 300 字符', 'error')
            return render_template('auth/profile_edit.html', user=current_user)

        # 处理头像文件上传
        avatar_file = request.files.get('avatar_file')
        if avatar_file and avatar_file.filename:
            ok, info = _save_avatar(avatar_file, current_user.id)
            if not ok:
                flash(info, 'error')
                return render_template('auth/profile_edit.html', user=current_user)
            # 上传成功 → 覆盖 URL 字段（保存为 /uploads/avatars/<id>.<ext> 静态路径）
            avatar_url = info  # info 即为最终 URL
            flash('头像已上传', 'success')

        current_user.bio = bio or None
        current_user.avatar_url = avatar_url or None
        try:
            db.session.commit()
            if not avatar_file or not avatar_file.filename:
                flash('个人资料已更新', 'success')
            return redirect(url_for('auth.profile'))
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            flash(f'更新失败: {exc}', 'error')

    return render_template('auth/profile_edit.html', user=current_user)


@auth_bp.route('/password', methods=['GET', 'POST'])
@login_required
def change_password():
    """GET/POST /auth/password - 修改密码"""
    if request.method == 'POST':
        old_pwd = request.form.get('old_password') or ''
        new_pwd = request.form.get('new_password') or ''
        confirm = request.form.get('confirm_password') or ''

        if not current_user.check_password(old_pwd):
            flash('原密码错误', 'error')
            return render_template('auth/change_password.html')

        err = _validate_password(new_pwd)
        if err:
            flash(err, 'error')
            return render_template('auth/change_password.html')

        if new_pwd != confirm:
            flash('两次输入的新密码不一致', 'error')
            return render_template('auth/change_password.html')

        current_user.set_password(new_pwd)
        try:
            db.session.commit()
            flash('密码已修改, 请使用新密码重新登录', 'success')
            logout_user()
            return redirect(url_for('auth.login'))
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            flash(f'修改失败: {exc}', 'error')

    return render_template('auth/change_password.html')


# ---------------------------------------------------------------------------
# 用户列表（公开）
# ---------------------------------------------------------------------------
@auth_bp.route('/users', methods=['GET'])
def user_list():
    """GET /auth/users - 用户列表"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('auth/user_list.html', users=users)
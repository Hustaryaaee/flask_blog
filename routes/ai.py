"""
AI 对话路由 - 阶段6
- GET  /ai                     聊天主页（会话列表 + 消息流）
- GET  /ai/session/<id>        加载某个会话
- POST /ai/session/new         新建会话（可携带 post_id）
- POST /ai/session/<id>/send   发送消息，返回 AI 回复（JSON）
- POST /ai/session/<id>/delete 删除会话
- POST /ai/post/<post_id>/ask  "问 AI 关于本文" - 创建会话并首问
"""
import json
import urllib.request
import urllib.error

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, jsonify, current_app, abort,
)
from flask_login import login_required, current_user

from models import db, ChatSession, ChatMessage, Post

ai_bp = Blueprint('ai', __name__, url_prefix='/ai')


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def _build_messages(session: ChatSession, user_text: str):
    """
    构造 messages + system。
    返回 (system: str|None, messages: list)
    - OpenAI 协议：system 放在 messages[0]
    - Anthropic 协议：system 放在顶层 system 字段，messages 不含 system role
    """
    cfg = current_app.config
    system_text = cfg['AI_SYSTEM_PROMPT']

    # 若绑定了文章，把文章摘要拼进 system
    if session.post_id and session.post:
        post = session.post
        ctx = f'\n\n[当前参考文章]\n标题: {post.title}\n'
        if post.excerpt:
            ctx += f'摘要: {post.excerpt}\n'
        ctx += f'正文:\n{post.content or ""}'
        # 截断避免超长
        if len(ctx) > 4000:
            ctx = ctx[:4000] + '\n...(文章过长已截断)'
        system_text += ctx

    # 历史（最近 10 条）
    hist = session.messages.order_by(ChatMessage.created_at.desc()).limit(10).all()
    hist = list(reversed(hist))
    msgs = []
    for m in hist:
        if m.role in (ChatMessage.ROLE_USER, ChatMessage.ROLE_ASSISTANT):
            if cfg['AI_PROTOCOL'] == 'anthropic':
                # Anthropic 要求 content 是结构化数组
                msgs.append({'role': m.role, 'content': [{'type': 'text', 'text': m.content}]})
            else:
                msgs.append({'role': m.role, 'content': m.content})
    # 当前用户问题
    if cfg['AI_PROTOCOL'] == 'anthropic':
        msgs.append({'role': 'user', 'content': [{'type': 'text', 'text': user_text}]})
    else:
        msgs.append({'role': 'user', 'content': user_text})
    return system_text, msgs


def _call_ai(system_text, messages):
    """
    调用大模型。返回 (reply_text, usage_dict)。
    根据 cfg['AI_PROTOCOL'] 走 OpenAI 或 Anthropic 协议。
    """
    cfg = current_app.config
    api_key = cfg['AI_API_KEY']
    base = cfg['AI_BASE_URL'].rstrip('/')

    if cfg['AI_PROTOCOL'] == 'anthropic':
        # Anthropic Messages API
        url = base + '/v1/messages'
        payload = {
            'model': cfg['AI_MODEL'],
            'max_tokens': cfg['AI_MAX_TOKENS'],
            'messages': messages,
        }
        if system_text:
            payload['system'] = system_text
        # Anthropic 不支持 temperature 与 max_tokens 之外的随意参数；这里只保留基础字段
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
        }
        resp = urllib.request.urlopen(
            urllib.request.Request(url, data=json.dumps(payload).encode(), method='POST', headers=headers),
            timeout=cfg['AI_TIMEOUT'],
        )
        body = json.loads(resp.read().decode('utf-8'))
        # 提取 text
        parts = body.get('content', [])
        reply = ''.join(p.get('text', '') for p in parts if p.get('type') == 'text')
        usage = body.get('usage', {})
        return reply, {
            'prompt_tokens': usage.get('input_tokens'),
            'completion_tokens': usage.get('output_tokens'),
        }

    # OpenAI 兼容
    url = base + '/chat/completions'
    oa_msgs = []
    if system_text:
        oa_msgs.append({'role': 'system', 'content': system_text})
    oa_msgs.extend(messages)
    payload = {
        'model': cfg['AI_MODEL'],
        'messages': oa_msgs,
        'max_tokens': cfg['AI_MAX_TOKENS'],
        'temperature': cfg['AI_TEMPERATURE'],
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    }
    import logging
    logging.warning(f'[AI] call openai url={url} model={cfg["AI_MODEL"]}')
    resp = urllib.request.urlopen(
        urllib.request.Request(url, data=json.dumps(payload).encode(), method='POST', headers=headers),
        timeout=cfg['AI_TIMEOUT'],
    )
    body = json.loads(resp.read().decode('utf-8'))
    reply = body['choices'][0]['message']['content']
    usage = body.get('usage', {})
    return reply, {
        'prompt_tokens': usage.get('prompt_tokens'),
        'completion_tokens': usage.get('completion_tokens'),
    }


def _demo_reply(user_text: str) -> str:
    """未配置 API key 时的演示回复"""
    return (
        f'[AI 演示模式] 你说的是："{user_text[:80]}"\n\n'
        '当前未配置 AI_API_KEY，无法连接真实大模型。\n'
        '在 .env 中设置 AI_ENABLED=true、AI_API_KEY=xxx、AI_BASE_URL、AI_MODEL 后即可启用真实对话。\n'
        '示例：\n'
        '  AI_ENABLED=true\n'
        '  AI_API_KEY=sk-xxxxxxxx\n'
        '  AI_BASE_URL=https://api.openai.com/v1\n'
        '  AI_MODEL=gpt-3.5-turbo'
    )


# ---------------------------------------------------------------------------
# 页面路由
# ---------------------------------------------------------------------------
@ai_bp.route('/', methods=['GET'])
@login_required
def index():
    """AI 聊天主页：左侧会话列表 + 右侧当前会话消息"""
    sessions = (
        ChatSession.query
        .filter_by(user_id=current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(50)
        .all()
    )
    cfg = current_app.config
    return render_template(
        'ai/chat.html',
        sessions=sessions,
        active_session=None,
        cfg=cfg,
    )


@ai_bp.route('/session/<int:session_id>', methods=['GET'])
@login_required
def view_session(session_id):
    session = ChatSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(404)

    sessions = (
        ChatSession.query
        .filter_by(user_id=current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(50)
        .all()
    )
    cfg = current_app.config
    messages = session.messages.order_by(ChatMessage.created_at.asc()).all()
    return render_template(
        'ai/chat.html',
        sessions=sessions,
        active_session=session,
        messages=messages,
        cfg=cfg,
    )


# ---------------------------------------------------------------------------
# 操作路由（AJAX）
# ---------------------------------------------------------------------------
@ai_bp.route('/session/new', methods=['POST'])
@login_required
def new_session():
    """
    新建会话。Body: { post_id?: int, title?: str }
    """
    data = request.get_json(silent=True) or request.form
    # 兼容 JSON dict 与 MultiDict（request.form 支持 type= 关键字）
    def _get(name, default=None):
        if hasattr(data, 'get'):
            try:
                return data.get(name, default)
            except Exception:
                return default
        return default

    def _get_int(name):
        v = _get(name)
        if v is None or v == '':
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    post_id = _get_int('post_id')
    title = str(_get('title') or '新对话').strip()[:120]
    post = None
    if post_id:
        post = Post.query.get(post_id)
        if post is None:
            return jsonify({'error': '文章不存在'}), 404
    sess = ChatSession(user_id=current_user.id, post_id=post.id if post else None, title=title)
    db.session.add(sess)
    db.session.commit()
    return jsonify({
        'id': sess.id,
        'title': sess.title,
        'post_id': sess.post_id,
    })


@ai_bp.route('/session/<int:session_id>/send', methods=['POST'])
@login_required
def send(session_id):
    """发送一条消息，调用大模型，返回 assistant 回复"""
    session = ChatSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(404)

    data = request.get_json(silent=True) or request.form
    user_text = (data.get('message') or '').strip()
    if not user_text:
        return jsonify({'error': '消息不能为空'}), 400
    if len(user_text) > 4000:
        return jsonify({'error': '消息过长（>4000 字符）'}), 400

    # 1) 持久化用户消息
    user_msg = ChatMessage(
        session_id=session.id,
        role=ChatMessage.ROLE_USER,
        content=user_text,
    )
    db.session.add(user_msg)
    # 首条用户消息 → 自动用其内容作为会话标题
    if session.title == '新对话':
        session.title = user_text[:30] + ('…' if len(user_text) > 30 else '')

    cfg = current_app.config
    reply_text = None
    usage = {}
    err = None

    try:
        if cfg['AI_DEMO_MODE'] or not cfg['AI_ENABLED']:
            reply_text = _demo_reply(user_text)
        else:
            system_text, messages = _build_messages(session, user_text)
            reply_text, usage = _call_ai(system_text, messages)
    except urllib.error.HTTPError as exc:
        err = f'AI 服务返回错误: {exc.code} {exc.reason}'
        try:
            err += '\n' + exc.read().decode('utf-8', errors='ignore')[:300]
        except Exception:
            pass
    except Exception as exc:
        err = f'调用 AI 失败: {exc}'

    if err:
        reply_text = f'[出错] {err}'

    ai_msg = ChatMessage(
        session_id=session.id,
        role=ChatMessage.ROLE_ASSISTANT,
        content=reply_text,
        prompt_tokens=usage.get('prompt_tokens'),
        completion_tokens=usage.get('completion_tokens'),
    )
    db.session.add(ai_msg)
    db.session.commit()

    return jsonify({
        'session_id': session.id,
        'user_message': user_msg.to_dict(),
        'assistant_message': ai_msg.to_dict(),
        'demo_mode': cfg['AI_DEMO_MODE'] or not cfg['AI_ENABLED'],
    })


@ai_bp.route('/session/<int:session_id>/delete', methods=['POST'])
@login_required
def delete_session(session_id):
    session = ChatSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(404)
    db.session.delete(session)
    db.session.commit()
    return jsonify({'success': True})


@ai_bp.route('/session/<int:session_id>/rename', methods=['POST'])
@login_required
def rename_session(session_id):
    """POST /ai/session/<id>/rename - 修改会话标题"""
    session = ChatSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        abort(404)
    data = request.get_json(silent=True) or request.form
    new_title = (data.get('title') or '').strip()[:120]
    if not new_title:
        return jsonify({'error': '标题不能为空'}), 400
    session.title = new_title
    db.session.commit()
    return jsonify({'success': True, 'title': session.title})


# ---------------------------------------------------------------------------
# 文章页"问 AI"快捷入口
# ---------------------------------------------------------------------------
@ai_bp.route('/post/<int:post_id>/ask', methods=['POST'])
@login_required
def ask_about_post(post_id):
    """创建绑定了文章的会话，并携带首条用户问题"""
    post = Post.query.get_or_404(post_id)
    data = request.get_json(silent=True) or request.form
    question = (data.get('question') or '').strip()
    if not question:
        # 默认问题
        question = '请帮我总结这篇文章的要点'

    sess = ChatSession(
        user_id=current_user.id,
        post_id=post.id,
        title=f'关于《{post.title}》',
    )
    db.session.add(sess)
    db.session.flush()  # 拿 id

    # 直接复用 send 流程：手动插入用户消息 + AI 回复
    # 为了简单，把消息持久化后调用 _build_messages/_call_ai
    user_msg = ChatMessage(
        session_id=sess.id,
        role=ChatMessage.ROLE_USER,
        content=question,
    )
    db.session.add(user_msg)

    cfg = current_app.config
    reply_text = None
    usage = {}
    try:
        if cfg['AI_DEMO_MODE'] or not cfg['AI_ENABLED']:
            reply_text = _demo_reply(question)
        else:
            system_text, messages = _build_messages(sess, question)
            reply_text, usage = _call_ai(system_text, messages)
    except Exception as exc:
        reply_text = f'[出错] 调用 AI 失败: {exc}'

    ai_msg = ChatMessage(
        session_id=sess.id,
        role=ChatMessage.ROLE_ASSISTANT,
        content=reply_text,
        prompt_tokens=usage.get('prompt_tokens'),
        completion_tokens=usage.get('completion_tokens'),
    )
    db.session.add(ai_msg)
    db.session.commit()

    return jsonify({
        'session_id': sess.id,
        'redirect_url': url_for('ai.view_session', session_id=sess.id),
    })
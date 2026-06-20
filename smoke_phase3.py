"""阶段3 测试: 评论 + 搜索"""
import re
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

HOST, PORT = '127.0.0.1', 5000


def op():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def csrf(html):
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return m.group(1) if m else None


def post(o, p, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        f'http://{HOST}:{PORT}{p}',
        data=body, method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    return o.open(req)


def get(o, p):
    return o.open(urllib.request.Request(f'http://{HOST}:{PORT}{p}'))


# 1) 登录 admin
o = op()
html = get(o, '/auth/login').read().decode()
tok = csrf(html)
post(o, '/auth/login', {'csrf_token': tok, 'identifier': 'admin', 'password': 'admin123456', 'remember': '1'})

# 2) 找到第一篇可见文章
idx = get(o, '/').read().decode()
url = None
for piece in idx.split('href="'):
    if '/post/' in piece:
        url = piece.split('"')[0]
        break
print(f'[*] 文章 URL: {url}')

# 通过 DB 拿 post_id
import sqlite3
conn = sqlite3.connect(r'd:\codeXcode\博客\instance\blog.db')
# 反查 slug -> id
slug_dec = urllib.parse.unquote(url.replace('/post/', ''))
cur = conn.execute('SELECT id FROM posts WHERE slug=?', (slug_dec,))
row = cur.fetchone()
post_id = row[0] if row else 1
conn.close()
print(f'[*] post_id = {post_id}')

# 3) 详情页含评论区表单
body = get(o, url).read().decode()
print(f'[*] 详情含评论表单 = {"id=\"comments\"" in body}')
print(f'[*] 详情含当前用户徽章 = {"以 <strong>admin" in body}')

# 4) 发评论
post_html = get(o, url).read().decode()
tok = csrf(post_html)
post(o, f'/comment/post/{post_id}/create', {
    'csrf_token': tok,
    'content': '这是管理员的第一条评论',
    'parent_id': '',
})

# 5) 游客评论（重新打开一个会话）
guest = op()
ghtml = get(guest, url).read().decode()
gtok = csrf(ghtml)
post(guest, f'/comment/post/{post_id}/create', {
    'csrf_token': gtok,
    'guest_name': '访客小明',
    'guest_email': 'x@example.com',
    'content': '访客留言：链接 https://example.com 应进入待审核',
    'parent_id': '',
})

# 6) 验证
body = get(o, url).read().decode()
print(f'[*] 管理员评论可见 = {"管理员的第一条评论" in body}')
print(f'[*] 游客评论含"待审核"徽章 = {"待审核" in body}')
print(f'[*] 游客显示昵称 = {"访客小明" in body}')
print(f'[*] 评论数 badge > 0 = {bool(re.search(r"badge bg-secondary\">[1-9]", body))}')

# 7) 回复评论
import sqlite3
conn = sqlite3.connect(r'd:\codeXcode\博客\instance\blog.db')
cur = conn.execute(f'SELECT id FROM comments WHERE post_id={post_id} ORDER BY id')
ids = [r[0] for r in cur.fetchall()]
conn.close()
parent_id = ids[0] if ids else None
print(f'[*] 父评论 id = {parent_id}')
post_html = get(o, url).read().decode()
tok = csrf(post_html)
post(o, f'/comment/post/{post_id}/create', {
    'csrf_token': tok,
    'content': '回复给管理员',
    'parent_id': str(parent_id),
})

body = get(o, url).read().decode()
print(f'[*] 嵌套回复可见 = {"回复给管理员" in body}')

# 8) 搜索
q_enc = urllib.parse.quote('阶段2')
search = get(o, f'/search?q={q_enc}').read().decode()
print(f'[*] /search?q=阶段2 含结果 = {"找到" in search or "/post/" in search}')

# 9) 索引页带 ?q=
search_idx = get(o, f'/?q={q_enc}').read().decode()
print(f'[*] /?q=阶段2 含结果 = {"/post/" in search_idx}')

print('\n[OK] 阶段3 评论+搜索验证完成')
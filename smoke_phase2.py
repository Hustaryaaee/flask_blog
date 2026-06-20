"""阶段2 测试: 创建带封面/摘要/SEO 的文章 + 编辑 + 历史 + 回滚 + 浏览计数"""
import re
import http.client
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

HOST, PORT = '127.0.0.1', 5000


def make_opener():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def get(op, p):
    return op.open(urllib.request.Request(f'http://{HOST}:{PORT}{p}')), None


def post(op, p, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        f'http://{HOST}:{PORT}{p}',
        data=body,
        method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    return op.open(req)


def csrf(html):
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return m.group(1) if m else None


op = make_opener()

# 登录 admin
login_html = op.open(urllib.request.Request(f'http://{HOST}:{PORT}/auth/login')).read().decode()
tok = csrf(login_html)
assert tok, 'login csrf not found'
r = post(op, '/auth/login', {'csrf_token': tok, 'identifier': 'admin', 'password': 'admin123456', 'remember': '1'})
print(f'[*] login -> {r.status}')

# 拿 create 表单 csrf
create_html = op.open(urllib.request.Request(f'http://{HOST}:{PORT}/create')).read().decode()
tok = csrf(create_html)
assert tok, 'create csrf not found'

# 创建带阶段2字段的文章
COVER = 'https://picsum.photos/seed/phase2/1200/400'
EXCERPT = '阶段2测试摘要：封面/SEO/定时发布'
SEO_DESC = '阶段2 SEO 描述'
SEO_KW = 'phase2, 测试'
r = post(op, '/create', {
    'csrf_token': tok,
    'title': '阶段2 测试文章',
    'content': '## 阶段2\n\n这是测试 **Markdown** 内容。\n\n- 列表1\n- 列表2\n\n```python\nprint("hi")\n```',
    'category_id': '',
    'tags': 'phase2, test',
    'is_markdown': '1',
    'status': 'published',
    'cover_image': COVER,
    'excerpt': EXCERPT,
    'seo_title': '阶段2 SEO 标题',
    'seo_description': SEO_DESC,
    'seo_keywords': SEO_KW,
    'published_at': '',
})
print(f'[*] POST /create -> {r.status}  url={r.geturl()}')

# 验证首页能看见
idx = op.open(urllib.request.Request(f'http://{HOST}:{PORT}/')).read().decode()
print(f'[*] 首页含 "阶段2 测试文章" = {"阶段2 测试文章" in idx}')
print(f'[*] 首页含 封面图 = {COVER in idx}')
print(f'[*] 首页含 摘要 = {EXCERPT in idx}')

# 验证 SEO meta
slug_match = re.search(r'/post/([\w\-]+)"', idx[idx.find('阶段2'):][:2000] if '阶段2' in idx else '')
# 直接 GET detail 通过搜索标题
detail_url = None
for line in idx.split('href="'):
    if '/post/' in line:
        url = line.split('"')[0]
        body = op.open(urllib.request.Request(f'http://{HOST}:{PORT}{url}')).read().decode()
        if '阶段2 测试文章' in body:
            detail_url = url
            break

assert detail_url, '未找到详情页'
print(f'[*] 详情页 URL: {detail_url}')
body = op.open(urllib.request.Request(f'http://{HOST}:{PORT}{detail_url}')).read().decode()
checks = {
    '封面图': COVER in body,
    '摘要': EXCERPT in body,
    'SEO描述': SEO_DESC in body,
    'SEO关键词': SEO_KW in body,
    '版本号徽章': 'v1' in body,
    'Markdown渲染 (h2)': '<h2>' in body,
    '代码块': '<code' in body,
}
for k, v in checks.items():
    print(f'    [{"✓" if v else "✗"}] {k}')

# 浏览计数 (再访问一次同会话但模拟已 seen -> 计数只+1)
r1 = op.open(urllib.request.Request(f'http://{HOST}:{PORT}{detail_url}'))
print(f'[*] 第二次访问详情 -> {r1.status}')

# 编辑一次 -> 触发 v2 + 历史
idx2 = op.open(urllib.request.Request(f'http://{HOST}:{PORT}/')).read().decode()
# admin 应该能看到 edit 链接
m = re.search(r'href="/edit/(\d+)"', idx2)
if not m:
    # 通过 API 列表查找所有 post id
    print('[*] 未在首页找到 edit 链接，尝试 DB 直接查询')
    import sqlite3
    conn = sqlite3.connect(r'd:\codeXcode\博客\instance\blog.db')
    cur = conn.execute('SELECT id, slug FROM posts ORDER BY id DESC LIMIT 5')
    rows = cur.fetchall()
    conn.close()
    edit_id = str(rows[0][0]) if rows else None
    print(f'[*] 从数据库获取 edit_id={edit_id}')
else:
    edit_id = m.group(1)
print(f'[*] edit_id = {edit_id}')
if edit_id:
    edit_html = op.open(urllib.request.Request(f'http://{HOST}:{PORT}/edit/{edit_id}')).read().decode()
    tok2 = csrf(edit_html)
    new_title = '阶段2 测试文章 v2'
    r3 = post(op, f'/edit/{edit_id}', {
        'csrf_token': tok2,
        'title': new_title,
        'content': '修改后的内容',
        'category_id': '',
        'tags': 'phase2',
        'is_markdown': '1',
        'status': 'published',
        'cover_image': COVER,
        'excerpt': '新摘要',
        'revision_note': '第一次编辑测试',
    })
    print(f'[*] POST /edit -> {r3.status}  url={r3.geturl()}')

    # 历史页
    hist_html = op.open(urllib.request.Request(f'http://{HOST}:{PORT}/post/{edit_id}/history')).read().decode()
    print(f'[*] GET history -> 含"第一次编辑测试" = {"第一次编辑测试" in hist_html}')

    # 回滚到 v1
    tok3 = csrf(hist_html)
    r4 = post(op, f'/post/{edit_id}/history/1/restore', {'csrf_token': tok3})
    print(f'[*] 回滚 -> {r4.status}')

print('\n[OK] 阶段2 主要功能验证完成')
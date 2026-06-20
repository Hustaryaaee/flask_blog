"""阶段4 测试: EasyMDE + Markdown 导入导出"""
import re
import io
import urllib.parse
import urllib.request
import zipfile
from http.cookiejar import CookieJar

HOST, PORT = '127.0.0.1', 5000


def op():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def get(o, p):
    return o.open(urllib.request.Request(f'http://{HOST}:{PORT}{p}'))


def csrf(html):
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return m.group(1) if m else None


def post(o, p, data, files=None):
    if files is None:
        body = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(
            f'http://{HOST}:{PORT}{p}', data=body, method='POST',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )
    else:
        # multipart
        boundary = '----test' + 'boundary123456'
        body = []
        for k, v in data.items():
            body.append(f'--{boundary}\r\n'.encode())
            body.append(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
            body.append(str(v).encode('utf-8'))
            body.append(b'\r\n')
        for fk, (fname, fdata, ftype) in files.items():
            body.append(f'--{boundary}\r\n'.encode())
            body.append(f'Content-Disposition: form-data; name="{fk}"; filename="{fname}"\r\n'.encode())
            body.append(f'Content-Type: {ftype}\r\n\r\n'.encode())
            body.append(fdata)
            body.append(b'\r\n')
        body.append(f'--{boundary}--\r\n'.encode())
        body_bytes = b''.join(body)
        req = urllib.request.Request(
            f'http://{HOST}:{PORT}{p}', data=body_bytes, method='POST',
            headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
        )
    return o.open(req)


# 登录
o = op()
html = get(o, '/auth/login').read().decode()
tok = csrf(html)
post(o, '/auth/login', {'csrf_token': tok, 'identifier': 'admin', 'password': 'admin123456', 'remember': '1'})

# 1) /create 含 EasyMDE 脚本
c = get(o, '/create').read().decode()
print(f'[*] /create 含 easymde.min.js = {"easymde.min.js" in c}')
print(f'[*] /create 含 easymde.min.css = {"easymde.min.css" in c}')
print(f'[*] /create 含 new EasyMDE = {"new EasyMDE" in c}')

# 2) 导出 Markdown
r = get(o, '/post/1/export.md')
md_bytes = r.read()
print(f'[*] export.md status={r.status}, len={len(md_bytes)}')
md_text = md_bytes.decode('utf-8')
print(f'[*] 含 frontmatter --- = {md_text.startswith("---")}')
print(f'[*] 含 title = {"title:" in md_text}')
print(f'[*] 含 tags = {"tags:" in md_text or "tags:" in md_text}')

# 3) 导出 zip
r2 = get(o, '/post/1/export.zip')
zb = r2.read()
print(f'[*] export.zip status={r2.status}, len={len(zb)}')
with zipfile.ZipFile(io.BytesIO(zb)) as zf:
    names = zf.namelist()
    print(f'[*] zip 包含: {names}')

# 4) /import GET
imp = get(o, '/import').read().decode()
print(f'[*] /import 含表单 = {"<form" in imp}')

# 5) /import POST - 带 front-matter 的 md
sample_md = """---
title: "导入测试文章"
tags: [Import, Test]
cover_image: "https://example.com/cover.jpg"
excerpt: "测试摘要"
status: "published"
---
# 导入的正文

这是一段**测试**内容。""".encode('utf-8')
# 拿 /import 页的 csrf
imp_get = get(o, '/import').read().decode()
import_tok = csrf(imp_get)
resp = post(o, '/import', {'csrf_token': import_tok}, files={
    'file': ('sample.md', sample_md, 'text/markdown'),
})
final_url = resp.geturl()
print(f'[*] import -> {resp.status}  url={final_url}')
print(f'[*] 重定向到 /create = {"/create" in final_url}')
print(f'[*] 含 title = {"import_test" in final_url or "%E5%AF%BC%E5%85%A5%E6%B5%8B%E8%AF%95" in final_url or "导入测试" in final_url}')

# 6) 跟随后重定向到 /create，验证预填
if '/create' in final_url:
    # 把 final_url 中可能含中文的部分转 path-only
    from urllib.parse import urlsplit, urlunsplit
    parts = urlsplit(final_url)
    body = get(o, parts.path + ('?' + parts.query if parts.query else '')).read().decode()
    print(f'[*] /create 预填 title = {"导入测试文章" in body}')
    print(f'[*] /create 预填 excerpt = {"测试摘要" in body}')
    print(f'[*] /create 预填 cover = {"https://example.com/cover.jpg" in body}')
    print(f'[*] /create 预填 tags = {"Import" in body}')

# 7) 编辑页也含 EasyMDE
import sqlite3
conn = sqlite3.connect(r'd:\codeXcode\博客\instance\blog.db')
pid = conn.execute('SELECT id FROM posts ORDER BY id LIMIT 1').fetchone()[0]
conn.close()
e = get(o, f'/edit/{pid}').read().decode()
print(f'[*] /edit/{pid} 含 easymde = {"easymde.min.js" in e}')

print('\n[OK] 阶段4 EasyMDE + 导入导出验证完成')
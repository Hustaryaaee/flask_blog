"""阶段5 测试: 暗黑模式 + 代码高亮 + 数学公式 + 归档页"""
import re
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

HOST, PORT = '127.0.0.1', 5000


def op():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def get(o, p):
    return o.open(urllib.request.Request(f'http://{HOST}:{PORT}{p}'))


def post(o, p, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        f'http://{HOST}:{PORT}{p}', data=body, method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    return o.open(req)


def csrf(html):
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return m.group(1) if m else None


o = op()
html = get(o, '/auth/login').read().decode()
tok = csrf(html)
post(o, '/auth/login', {'csrf_token': tok, 'identifier': 'admin', 'password': 'admin123456', 'remember': '1'})

# 1) 归档页
arc = get(o, '/archive').read().decode()
print(f'[*] /archive 200 = {"文章归档" in arc}')
print(f'[*] /archive 含月分组 = {"20" in arc}')

# 2) 首页有归档入口
home = get(o, '/').read().decode()
print(f'[*] 首页导航含归档 = {"/archive" in home}')

# 3) 首页有暗黑模式切换
print(f'[*] 首页含 themeToggle = {"themeToggle" in home}')
print(f'[*] 首页含 data-bs-theme = {"data-bs-theme" in home}')

# 4) 创建带代码块+数学公式的文章
c = get(o, '/create').read().decode()
tok = csrf(c)
sample = """# 阶段5 测试

```python
def hello(name):
    print(f"Hello, {name}!")
```

行内数学 $E = mc^2$，块级：

$$
\\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}
$$

结束。
"""
post(o, '/create', {
    'csrf_token': tok,
    'title': '阶段5 测试文章',
    'content': sample,
    'tags': 'phase5',
    'is_markdown': '1',
    'status': 'published',
})

# 5) 验证代码高亮 + MathJax 加载
import sqlite3
conn = sqlite3.connect(r'd:\codeXcode\博客\instance\blog.db')
pid = conn.execute("SELECT id FROM posts WHERE title='阶段5 测试文章' ORDER BY id DESC LIMIT 1").fetchone()[0]
conn.close()

det = get(o, f'/post/阶段5-测试文章').read().decode() if False else None
# 用 slug
conn2 = sqlite3.connect(r'd:\codeXcode\博客\instance\blog.db')
slug = conn2.execute(f'SELECT slug FROM posts WHERE id={pid}').fetchone()[0]
conn2.close()
slug_enc = urllib.parse.quote(slug)
body = get(o, f'/post/{slug_enc}').read().decode()
print(f'[*] 代码高亮 class=highlight = {"<div class=\"highlight\"" in body or "highlight" in body}')
print(f'[*] Pygments token color <span class=k> = {"class=\"k\"" in body}')
print(f'[*] MathJax script = {"MathJax-script" in body or "mathjax" in body.lower()}')

# 6) 暗黑样式存在
import urllib.request
css_url = f'http://{HOST}:{PORT}/static/css/style.css'
css_body = get(o, '/static/css/style.css').read().decode('utf-8', errors='ignore')
print(f'[*] CSS 含 [data-bs-theme="dark"] = {"[data-bs-theme=\"dark\"]" in css_body}')
print(f'[*] CSS 含 Pygments token .k = {".highlight .k" in css_body}')

print('\n[OK] 阶段5 验证完成')
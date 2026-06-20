"""阶段1 路由冒烟测试"""
import urllib.request
import urllib.error

BASE = 'http://127.0.0.1:5000'
URLS = [
    '/',                  # 公开
    '/auth/login',        # 公开
    '/auth/register',     # 公开
    '/auth/users',        # 公开
    '/auth/profile',      # 应 302 -> /auth/login
    '/create',            # 应 302 -> /auth/login
    '/edit/1',            # 应 302 -> /auth/login
]

for path in URLS:
    url = BASE + path
    try:
        req = urllib.request.Request(url, method='GET')
        # 不要跟随重定向，看真实状态码
        opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
        # 简单方法：使用低级 HTTP
        import http.client
        conn = http.client.HTTPConnection('127.0.0.1', 5000, timeout=5)
        conn.request('GET', path)
        resp = conn.getresponse()
        print(f'GET {path:<22} -> {resp.status}  Location: {resp.getheader("Location") or "-"}')
        resp.read()
        conn.close()
    except Exception as e:
        print(f'GET {path} -> ERROR {e}')
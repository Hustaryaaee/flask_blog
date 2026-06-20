"""阶段1 登录流程测试 - urllib + cookiejar 单 session"""
import re
import http.client
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

BASE_HOST = '127.0.0.1'
BASE_PORT = 5000


def make_session():
    cj = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    return opener


def get(opener, path):
    return opener.open(urllib.request.Request(f'http://{BASE_HOST}:{BASE_PORT}{path}'), timeout=5)


def post(opener, path, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        f'http://{BASE_HOST}:{BASE_PORT}{path}',
        data=body,
        method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    return opener.open(req, timeout=5)


opener = make_session()

# 1) GET /auth/login 拿 csrf + session cookie
html = get(opener, '/auth/login').read().decode('utf-8', errors='ignore')
m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
assert m, 'csrf_token 未找到'
csrf = m.group(1)
print(f'[*] csrf_token = {csrf[:16]}...')

# 2) POST 登录
resp = post(opener, '/auth/login', {
    'csrf_token': csrf,
    'identifier': 'admin',
    'password': 'admin123456',
    'remember': '1',
})
print(f'[*] POST /auth/login -> {resp.status}  URL: {resp.geturl()}')

# 3) /create
r2 = get(opener, '/create')
print(f'[*] GET /create (登录后) -> {r2.status}')

# 4) /auth/profile
body = get(opener, '/auth/profile').read().decode('utf-8', errors='ignore')
print(f'[*] GET /auth/profile -> 含admin={"admin" in body}, 含角色徽章={"管理员" in body}')

# 5) /auth/logout
try:
    r4 = get(opener, '/auth/logout')
    print(f'[*] GET /auth/logout -> {r4.status}  URL: {r4.geturl()}')
except urllib.error.HTTPError as e:
    print(f'[!] logout: {e.code} {e.reason}')

# 6) 退出后再访问 /create
conn = http.client.HTTPConnection(BASE_HOST, BASE_PORT, timeout=5)
conn.request('GET', '/create')
r = conn.getresponse()
print(f'[*] GET /create (退出后) -> {r.status}  Location: {r.getheader("Location")}')
r.read()

print('\n[OK] 阶段1 登录流程完成')
"""测试文件上传功能"""
import requests
import os

# 读取测试文件
test_file = os.path.join(os.path.dirname(__file__), 'test_upload.md')

# 读取文件内容
with open(test_file, 'rb') as f:
    files = {'file': ('test_upload.md', f, 'text/markdown')}
    
    # 发送POST请求
    response = requests.post(
        'http://127.0.0.1:5000/upload',
        files=files,
        allow_redirects=False
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Location: {response.headers.get('Location', 'None')}")
    
    if response.status_code == 302:
        # 重定向到创建页面
        redirect_url = response.headers.get('Location')
        print(f"Redirect to: {redirect_url}")
        
        # 访问重定向的页面
        get_response = requests.get('http://127.0.0.1:5000' + redirect_url)
        print(f"Create page status: {get_response.status_code}")
        
        # 检查是否包含文件内容
        if '测试文章' in get_response.text:
            print("✓ 文件内容已正确预填!")
        else:
            print("✗ 文件内容未找到")
    else:
        print(f"Response: {response.text[:500]}")

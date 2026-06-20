# Flask Blog

一个简洁美观的Flask博客项目。

## 技术栈

- **后端**: Flask 3.0, Flask-SQLAlchemy, Flask-Migrate
- **前端**: Bootstrap 5, Jinja2模板引擎
- **数据库**: SQLite (可扩展至MySQL/PostgreSQL)

## 项目结构

```
flask_blog/
├── app.py              # 应用入口
├── config.py           # 配置文件
├── models.py           # 数据模型
├── requirements.txt    # Python依赖
├── routes/             # 路由蓝图
│   ├── __init__.py
│   └── blog.py
├── templates/          # Jinja2模板
│   ├── base.html
│   ├── index.html
│   ├── post.html
│   ├── create.html
│   ├── edit.html
│   └── macros.html
└── static/             # 静态资源
    ├── css/style.css
    └── js/main.js
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

### 3. 初始化数据库

```bash
flask db init
flask db migrate
flask db upgrade
```

### 4. 运行应用

```bash
flask run
```

访问 http://127.0.0.1:5000

## 功能特性

- [x] 文章列表页（支持分页）
- [x] 文章详情页
- [x] 创建文章
- [x] 编辑文章
- [x] 删除文章
- [x] 响应式设计
- [ ] 用户认证
- [ ] 评论系统
- [ ] 分类/标签
- [ ] 搜索功能

## 待开发功能

- 用户注册/登录
- Markdown编辑器
- 文章分类和标签
- 评论和回复
- 图片上传
- 站点地图SEO
- RSS订阅

## License

MIT

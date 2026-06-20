"""
数据库迁移脚本
添加新字段: is_markdown, category_id 到 posts 表
创建 categories, tags, post_tags 表
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'blog.db')

def migrate():
    """执行数据库迁移"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查posts表结构
        cursor.execute("PRAGMA table_info(posts)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # 添加 is_markdown 字段
        if 'is_markdown' not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN is_markdown BOOLEAN DEFAULT 1")
            print("✓ 添加 is_markdown 字段成功")
        else:
            print("- is_markdown 字段已存在")
        
        # 添加 category_id 字段 (SQLite不支持在ALTER TABLE中加外键约束)
        if 'category_id' not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN category_id INTEGER")
            print("✓ 添加 category_id 字段成功")
        else:
            print("- category_id 字段已存在")
        
        # 创建 categories 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(50) UNIQUE NOT NULL,
                slug VARCHAR(50) UNIQUE NOT NULL,
                description VARCHAR(200),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ categories 表已创建/已存在")
        
        # 创建 tags 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(30) UNIQUE NOT NULL,
                slug VARCHAR(30) UNIQUE NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✓ tags 表已创建/已存在")
        
        # 创建 post_tags 关联表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS post_tags (
                post_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                PRIMARY KEY (post_id, tag_id),
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )
        """)
        print("✓ post_tags 表已创建/已存在")

        # ---------- 阶段2 字段 ----------
        cursor.execute("PRAGMA table_info(posts)")
        columns = [col[1] for col in cursor.fetchall()]
        phase2_cols = {
            'status': "ALTER TABLE posts ADD COLUMN status VARCHAR(20) DEFAULT 'published'",
            'cover_image': "ALTER TABLE posts ADD COLUMN cover_image VARCHAR(255)",
            'excerpt': "ALTER TABLE posts ADD COLUMN excerpt VARCHAR(500)",
            'seo_title': "ALTER TABLE posts ADD COLUMN seo_title VARCHAR(200)",
            'seo_description': "ALTER TABLE posts ADD COLUMN seo_description VARCHAR(300)",
            'seo_keywords': "ALTER TABLE posts ADD COLUMN seo_keywords VARCHAR(200)",
            'published_at': "ALTER TABLE posts ADD COLUMN published_at DATETIME",
            'view_count': "ALTER TABLE posts ADD COLUMN view_count INTEGER DEFAULT 0",
            'revision': "ALTER TABLE posts ADD COLUMN revision INTEGER DEFAULT 1",
        }
        for col, sql in phase2_cols.items():
            if col not in columns:
                cursor.execute(sql)
                print(f"✓ posts.{col} 已添加")
            else:
                print(f"- posts.{col} 已存在")
        # post_histories 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS post_histories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                revision INTEGER NOT NULL,
                title VARCHAR(200) NOT NULL,
                content TEXT NOT NULL,
                excerpt VARCHAR(500),
                cover_image VARCHAR(500),
                saved_by_id INTEGER,
                saved_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                note VARCHAR(200),
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                FOREIGN KEY (saved_by_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_post_histories_post_id ON post_histories(post_id)")
        print("✓ post_histories 表已创建/已存在")

        # 索引
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_posts_status ON posts(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_posts_published_at ON posts(published_at)")

        # ---------- 阶段3 评论表 ----------
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                author_id INTEGER,
                guest_name VARCHAR(50),
                guest_email VARCHAR(120),
                content TEXT NOT NULL,
                parent_id INTEGER,
                status VARCHAR(20) NOT NULL DEFAULT 'approved',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET NULL,
                FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_comments_post_id ON comments(post_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_comments_status ON comments(status)")
        print("✓ comments 表已创建/已存在")

        conn.commit()
        print("\n✅ 阶段3 评论表同步完成!")

    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()

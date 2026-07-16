"""数据库迁移：添加 language 字段"""

from app.database.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'zh' NOT NULL;"))
    db.commit()
    print("语言字段添加成功")
except Exception as e:
    db.rollback()
    print(f"添加失败: {str(e)}")
finally:
    db.close()
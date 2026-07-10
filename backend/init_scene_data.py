# 文件路径: D:\Project\team\backend\init_scene_data.py
import json

from app.database.session import SessionLocal
from app.entity.db_models import DetectionScene


def init():
    db = SessionLocal()
    try:
        # 1. 检查是否已经有 scene_id=1 的数据了，避免重复插入
        exists = db.query(DetectionScene).filter(DetectionScene.id == 1).first()
        if exists:
            print("✅ 数据库中已经存在 scene_id=1 的数据，无需重复添加。")
            return

        # 2. 根据你的 db_models.py 构造插入的数据
        # 注意：class_names 和 class_names_cn 如果是 JSON 字段，通常需要 json.dumps()
        new_scene = DetectionScene(
            id=1,
            name="remote_sensing",
            display_name="遥感目标检测",
            description="用于遥感图像中的飞机、油罐、立交桥、操场检测",
            category="rsod",
            class_names=json.dumps(["aircraft", "oiltank", "overpass", "playground"]),
            class_names_cn=json.dumps(
                {
                    "aircraft": "飞机",
                    "oiltank": "油罐",
                    "overpass": "立交桥",
                    "playground": "操场",
                }
            ),
            is_active=True,
            created_by=1,  # 假设你的 testuser 用户 ID 是 1
        )

        db.add(new_scene)
        db.commit()
        print("✅ 成功插入 scene_id=1 的基础数据！现在可以开始训练了。")

    except Exception as e:
        db.rollback()
        print(f"❌ 插入失败，错误信息: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    init()

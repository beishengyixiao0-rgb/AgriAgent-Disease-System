"""
单图检测接口测试脚本

使用方法：
    cd C:\Users\II\Desktop\MelonPestDetection-AgentPlatform\AgriAgent-Disease-System\backend
    python test_detection.py
"""

import requests
import json
import os

# 配置
BASE_URL = "http://localhost:8000"
USERNAME = "string5"
PASSWORD = "string5"
IMAGE_PATH = r"C:\Users\II\Desktop\OIP-C.png"


def test_single_detection():
    """测试单图检测接口"""
    print("=" * 60)
    print("单图检测接口测试")
    print("=" * 60)

    # 1. 登录获取 token
    print("\n[1/3] 登录获取 Token...")
    login_resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": USERNAME, "password": PASSWORD}
    )

    if login_resp.status_code != 200:
        print(f"登录失败: {login_resp.status_code}")
        print(login_resp.text)
        return

    token = login_resp.json()["access_token"]
    print(f"✓ 登录成功，Token: {token[:50]}...")

    # 2. 检查测试图片是否存在
    print("\n[2/3] 检查测试图片...")
    if not os.path.exists(IMAGE_PATH):
        print(f"✗ 测试图片不存在: {IMAGE_PATH}")
        print("请修改脚本中的 IMAGE_PATH 变量")
        return
    print(f"✓ 测试图片: {IMAGE_PATH}")

    # 3. 调用单图检测接口
    print("\n[3/3] 调用单图检测接口...")
    with open(IMAGE_PATH, "rb") as f:
        files = {"file": (os.path.basename(IMAGE_PATH), f, "image/png")}
        headers = {"Authorization": f"Bearer {token}"}

        resp = requests.post(
            f"{BASE_URL}/api/detection/single",
            files=files,
            headers=headers,
            data={"conf": "0.25"}
        )

    print(f"\n状态码: {resp.status_code}")

    if resp.status_code == 200:
        result = resp.json()
        print("\n" + "=" * 60)
        print("检测结果")
        print("=" * 60)
        print(f"文件名: {result.get('filename', 'N/A')}")
        print(f"检测目标数: {result.get('total_objects', 0)}")
        print(f"推理耗时: {result.get('inference_time', 0):.2f} ms")
        print(f"任务 ID: {result.get('task_id', 'N/A')}")

        if result.get("class_counts"):
            print("\n各类别数量:")
            for class_name, count in result["class_counts"].items():
                print(f"  - {class_name}: {count}")

        if result.get("detections"):
            print("\n检测详情 (前 5 个):")
            for i, det in enumerate(result["detections"][:5], 1):
                print(f"  {i}. {det['class_name']}: {det['confidence']:.2%}")
                print(f"     位置: {det['bbox']}")

        if result.get("annotated_image_url"):
            print(f"\n标注图 URL: {result['annotated_image_url']}")

        if result.get("annotated_image_base64"):
            print(f"标注图 Base64: {len(result['annotated_image_base64'])} 字符")

        print("\n" + "=" * 60)
        print("✓ 检测成功")
        print("=" * 60)
    else:
        print(f"\n✗ 检测失败")
        print(f"错误信息: {resp.text}")


if __name__ == "__main__":
    test_single_detection()

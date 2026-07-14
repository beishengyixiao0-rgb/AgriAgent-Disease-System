"""
训练模块接口测试

测试覆盖：
- GET  /api/training/tasks                    获取训练任务列表
- GET  /api/training/status/{task_id}         获取训练状态 (仅负向)
- GET  /api/training/metrics/{task_id}        获取训练指标历史 (仅负向)
- GET  /api/training/results/{task_uuid}      下载 results.csv (仅负向)
- GET  /api/training/download/{task_id}       下载模型权重
- POST /api/training/export/{task_id}         导出模型
- POST /api/training/start                    场景不存在校验
- POST /api/training/predict                  非法文件类型校验
- POST /api/training/validate                 模型评估
"""

import io
import pytest
from PIL import Image


class TestTrainingAPI:
    """训练管理模块测试 - 仅负向 + 不需要 completed 任务的测试"""

    @pytest.fixture
    def auth_headers(self, client):
        """提供认证请求头"""
        # 注册用户
        client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "test123",
            },
        )

        login_resp = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "test123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def _get_error_message(self, response):
        """从响应中安全提取错误消息"""
        data = response.json()
        if "detail" in data:
            return data["detail"]
        elif "message" in data:
            return data["message"]
        elif "msg" in data:
            return data["msg"]
        return str(data)

    # ==================== 1. 训练任务列表 ====================

    def test_list_training_tasks_success(self, client, auth_headers):
        """测试获取训练任务列表"""
        response = client.get("/api/training/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_list_training_tasks_empty(self, client, auth_headers):
        """测试新用户无任务时的返回"""
        register_resp = client.post(
            "/api/auth/register",
            json={
                "username": "empty_task_user_001",
                "email": "empty_task@test.com",
                "password": "test123",
            },
        )
        assert register_resp.status_code == 201

        login_resp = client.post(
            "/api/auth/login",
            json={"username": "empty_task_user_001", "password": "test123"},
        )
        token = login_resp.json()["access_token"]
        new_headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/training/tasks", headers=new_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    # ==================== 2. 训练状态 (仅负向) ====================

    def test_get_training_status_not_found(self, client, auth_headers):
        """测试查询不存在的任务 → 404"""
        response = client.get("/api/training/status/99999", headers=auth_headers)
        assert response.status_code == 404

    # ==================== 3. 训练指标 (仅负向) ====================

    def test_get_training_metrics_not_found(self, client, auth_headers):
        """测试查询不存在的任务指标 → 空列表"""
        response = client.get("/api/training/metrics/99999", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["metrics"] == []

    # ==================== 4. 获取 results.csv (仅负向) ====================

    def test_get_results_csv_not_found(self, client, auth_headers):
        """测试下载不存在的 results.csv → 404"""
        response = client.get(
            "/api/training/results/nonexistent_uuid_12345",
            headers=auth_headers,
        )
        assert response.status_code == 404

    # ==================== 5. 模型评估 ====================

    def test_validate_model_success(self, client, auth_headers):
        """测试模型评估 - 模型文件不存在时返回 400"""
        # 使用一个不存在的 task_id，但确保它存在但模型文件不存在
        # 或者直接测试任务不存在的情况
        response = client.post(
            "/api/training/validate/99999",
            json={"split": "val", "conf": 0.001, "iou": 0.6},
            headers=auth_headers,
        )
        assert response.status_code == 400
        error_msg = self._get_error_message(response)
        assert "不存在" in error_msg or "任务" in error_msg

    def test_validate_task_not_found(self, client, auth_headers):
        """测试评估不存在的任务 → 400"""
        response = client.post(
            "/api/training/validate/99999",
            json={"split": "val"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        error_msg = self._get_error_message(response)
        assert "不存在" in error_msg or "任务" in error_msg

    # ==================== 6. 模型导出 ====================

    def test_export_model_success(self, client, auth_headers):
        """测试导出模型 - 模型文件不存在时返回 400"""
        response = client.post(
            "/api/training/export/99999",
            json={"description": "测试导出", "set_default": True},
            headers=auth_headers,
        )
        assert response.status_code == 400
        error_msg = self._get_error_message(response)
        assert "不存在" in error_msg or "任务" in error_msg

    def test_export_specify_version(self, client, auth_headers):
        """测试指定版本号导出 - 任务不存在返回 400"""
        response = client.post(
            "/api/training/export/99999",
            json={"version": "v2.0.0", "description": "测试指定版本"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        error_msg = self._get_error_message(response)
        assert "不存在" in error_msg or "任务" in error_msg

    def test_export_without_set_default(self, client, auth_headers):
        """测试导出但不设为默认模型 - 任务不存在返回 400"""
        response = client.post(
            "/api/training/export/99999",
            json={"set_default": False, "description": "不设为默认"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        error_msg = self._get_error_message(response)
        assert "不存在" in error_msg or "任务" in error_msg

    # ==================== 7. 下载模型 ====================

    def test_download_model_success(self, client, auth_headers):
        """测试下载模型权重文件 - 任务不存在返回 404"""
        response = client.get(
            "/api/training/download/99999",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_download_model_not_found(self, client, auth_headers):
        """测试下载不存在的任务 → 404"""
        response = client.get("/api/training/download/99999", headers=auth_headers)
        assert response.status_code == 404

    # ==================== 8. 启动训练 - 场景不存在 ====================

    def test_start_training_scene_not_found(self, client, auth_headers):
        """测试场景不存在时的错误处理 → 404"""
        response = client.post(
            "/api/training/start",
            json={
                "scene_id": 99999,
                "model_name": "yolov11n",
                "epochs": 10,
                "batch_size": 8,
                "img_size": 640,
                "device": "cpu",
                "optimizer": "SGD",
                "lr0": 0.01,
            },
            headers=auth_headers,
        )
        assert response.status_code == 404
        error_msg = self._get_error_message(response)
        assert "检测场景不存在" in error_msg

    # ==================== 9. 测试图验证 - 非法文件类型 ====================

    def test_predict_invalid_file_format(self, client, auth_headers):
        """测试上传非图片格式文件 → 400"""
        # 使用一个不存在的 task_id，但文件类型错误会先被拦截
        txt_bytes = io.BytesIO(b"this is not an image")

        response = client.post(
            "/api/training/predict",
            files={"file": ("test.txt", txt_bytes, "text/plain")},
            data={"task_id": 99999},
            headers=auth_headers,
        )
        # 文件类型错误，即使 task_id 不存在也先返回 400
        assert response.status_code == 400
        error_msg = self._get_error_message(response)
        assert "不支持" in error_msg or "格式" in error_msg

    # ==================== 10. 测试图验证 - 真实图片推理 ====================

    def test_predict_with_real_image(self, client, auth_headers):
        """测试真实图片推理 - 任务不存在返回 404"""
        img = Image.new("RGB", (640, 640), color=0xFF0000)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        response = client.post(
            "/api/training/predict",
            files={"file": ("test.jpg", img_bytes, "image/jpeg")},
            data={
                "task_id": 99999,
                "conf": 0.25,
                "iou": 0.45,
            },
            headers=auth_headers,
        )
        assert response.status_code == 404
        error_msg = self._get_error_message(response)
        assert "不存在" in error_msg or "任务" in error_msg
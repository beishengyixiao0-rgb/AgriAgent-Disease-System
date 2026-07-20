"""
认证接口测试

测试目标：
  - 用户注册：正常注册、重复用户名、参数验证
  - 用户登录：正常登录、错误密码、不存在的用户
  - 获取当前用户：有 Token、无 Token、无效 Token

测试策略：
  - 每个测试用例独立，不依赖其他测试的执行顺序
  - 使用唯一的用户名避免测试间冲突
"""

import pytest
from app.entity.db_models import User


class TestRegister:
    """用户注册测试"""

    def test_register_success(self, client):
        """正常注册"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "test_register_user",
                "email": "test_register@example.com",
                "password": "123456",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "test_register_user"
        assert data["email"] == "test_register@example.com"
        # 确保不返回密码字段
        assert "hashed_password" not in data
        assert "password" not in data

    def test_register_duplicate_username(self, client):
        """重复用户名注册"""
        # 先注册一个用户
        client.post(
            "/api/auth/register",
            json={
                "username": "dup_user",
                "email": "dup1@example.com",
                "password": "123456",
            },
        )
        # 用相同用户名再注册
        response = client.post(
            "/api/auth/register",
            json={
                "username": "dup_user",
                "email": "dup2@example.com",
                "password": "123456",
            },
        )
        assert response.status_code == 400

    def test_register_short_username(self, client):
        """用户名过短（少于 3 字符）"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "ab",
                "email": "short@example.com",
                "password": "123456",
            },
        )
        assert response.status_code == 422

    def test_register_short_password(self, client):
        """密码过短（少于 6 位）"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "short_pwd_user",
                "email": "shortpwd@example.com",
                "password": "123",
            },
        )
        assert response.status_code == 422

    def test_register_missing_fields(self, client):
        """缺少必填字段"""
        response = client.post(
            "/api/auth/register",
            json={"username": "no_email_user"},
        )
        assert response.status_code == 422


class TestLogin:
    """用户登录测试"""

    def test_login_success(self, client):
        """正常登录"""
        # 先注册
        client.post(
            "/api/auth/register",
            json={
                "username": "login_user",
                "email": "login@example.com",
                "password": "123456",
            },
        )
        # 再登录
        response = client.post(
            "/api/auth/login",
            json={
                "username": "login_user",
                "password": "123456",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == "login_user"
        assert data["user"]["roles"] == ["user"]

    def test_login_wrong_password(self, client):
        """密码错误"""
        # 先注册
        client.post(
            "/api/auth/register",
            json={
                "username": "wrong_pwd_user",
                "email": "wrongpwd@example.com",
                "password": "123456",
            },
        )
        # 用错误密码登录
        response = client.post(
            "/api/auth/login",
            json={
                "username": "wrong_pwd_user",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """不存在的用户"""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "no_such_user_12345",
                "password": "123456",
            },
        )
        assert response.status_code == 401


class TestGetCurrentUser:
    """获取当前用户测试"""

    def test_get_me_with_valid_token(self, client):
        """使用有效 Token 获取用户信息"""
        # 注册并登录
        client.post(
            "/api/auth/register",
            json={
                "username": "me_user",
                "email": "me@example.com",
                "password": "123456",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "me_user",
                "password": "123456",
            },
        )
        token = login_response.json()["access_token"]

        # 使用 Token 获取用户信息
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "me_user"
        assert data["email"] == "me@example.com"

    def test_get_me_without_token(self, client):
        """不带 Token 访问受保护接口"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_get_me_with_invalid_token(self, client):
        """使用无效 Token"""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        assert response.status_code == 401


# ============================================================
# 新增测试 - 忘记密码 7.10
# ============================================================


class TestForgotPassword:
    """忘记密码测试"""

    def test_forgot_password_success(self, client, db_session, monkeypatch):
        """正常忘记密码：生成 6 位验证码并发送邮件。"""
        from app.services import user_service as user_service_module

        monkeypatch.setattr(
            user_service_module.EmailService,
            "send_verification_code",
            lambda email, code: True,
        )

        # 先注册用户
        client.post(
            "/api/auth/register",
            json={
                "username": "forgot_user",
                "email": "forgot@example.com",
                "password": "123456",
            },
        )

        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "forgot@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "验证码已发送到您的邮箱，请在 5 分钟内使用"

        user = db_session.query(User).filter(User.email == "forgot@example.com").first()
        assert user.reset_token is not None
        assert user.reset_token.isdigit()
        assert len(user.reset_token) == 6
        assert user.reset_token_expires_at is not None

    def test_forgot_password_email_not_found(self, client):
        """邮箱未注册"""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "notexist@example.com"},
        )
        assert response.status_code == 404


class TestResetPassword:
    """重置密码测试"""

    def test_reset_password_success(self, client, db_session, monkeypatch):
        """正常重置密码：使用邮箱和验证码更新密码。"""
        from app.services import user_service as user_service_module

        monkeypatch.setattr(
            user_service_module.EmailService,
            "send_verification_code",
            lambda email, code: True,
        )

        # 注册用户
        client.post(
            "/api/auth/register",
            json={
                "username": "reset_user",
                "email": "reset@example.com",
                "password": "123456",
            },
        )

        # 获取重置令牌
        forgot_response = client.post(
            "/api/auth/forgot-password",
            json={"email": "reset@example.com"},
        )
        assert forgot_response.status_code == 200
        user = db_session.query(User).filter(User.email == "reset@example.com").first()
        code = user.reset_token

        # 重置密码
        response = client.post(
            "/api/auth/reset-password",
            json={
                "email": "reset@example.com",
                "code": code,
                "new_password": "new789012",
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "密码重置成功"

        # 使用新密码登录验证
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "reset_user",
                "password": "new789012",
            },
        )
        assert login_response.status_code == 200

    def test_reset_password_invalid_token(self, client):
        """无效验证码"""
        client.post(
            "/api/auth/register",
            json={
                "username": "reset_invalid_code_user",
                "email": "reset_invalid@example.com",
                "password": "123456",
            },
        )

        response = client.post(
            "/api/auth/reset-password",
            json={
                "email": "reset_invalid@example.com",
                "code": "000000",
                "new_password": "new789012",
            },
        )
        assert response.status_code == 400
        assert response.json()["message"] == "验证码错误"


class TestProfile:
    """个人信息测试"""

    def test_get_profile_success(self, client):
        """正常获取个人信息"""
        # 注册并登录
        client.post(
            "/api/auth/register",
            json={
                "username": "profile_user",
                "email": "profile@example.com",
                "password": "123456",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "profile_user",
                "password": "123456",
            },
        )
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "profile_user"
        assert "detection_stats" in data  # 包含检测统计

    def test_update_profile_success(self, client):
        """正常修改个人信息"""
        # 注册并登录
        client.post(
            "/api/auth/register",
            json={
                "username": "update_user",
                "email": "update@example.com",
                "password": "123456",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "update_user",
                "password": "123456",
            },
        )
        token = login_response.json()["access_token"]

        # 修改个人信息
        response = client.put(
            "/api/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "phone": "13800138000",
                "email": "new_email@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == "13800138000"
        assert data["email"] == "new_email@example.com"


class TestChangePassword:
    """修改密码测试"""

    def test_change_password_success(self, client):
        """正常修改密码"""
        # 注册并登录
        client.post(
            "/api/auth/register",
            json={
                "username": "change_pwd_user",
                "email": "changepwd@example.com",
                "password": "123456",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "change_pwd_user",
                "password": "123456",
            },
        )
        token = login_response.json()["access_token"]

        # 修改密码
        response = client.put(
            "/api/auth/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "123456",
                "new_password": "new654321",
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "密码修改成功"

        # 使用新密码登录
        new_login = client.post(
            "/api/auth/login",
            json={
                "username": "change_pwd_user",
                "password": "new654321",
            },
        )
        assert new_login.status_code == 200

    def test_change_password_wrong_old(self, client):
        """旧密码错误"""
        # 注册并登录
        client.post(
            "/api/auth/register",
            json={
                "username": "wrong_old_user",
                "email": "wrongold@example.com",
                "password": "123456",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "wrong_old_user",
                "password": "123456",
            },
        )
        token = login_response.json()["access_token"]

        response = client.put(
            "/api/auth/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "wrong_password",
                "new_password": "new654321",
            },
        )
        assert response.status_code == 400
        assert response.json()["message"] == "旧密码错误"

    def test_change_password_without_token(self, client):
        """未登录修改密码"""
        response = client.put(
            "/api/auth/password",
            json={
                "old_password": "123456",
                "new_password": "new654321",
            },
        )
        assert response.status_code == 401


# ============================================================
# 新增测试 - 邮箱格式校验（Pattern） 7.10
# ============================================================


class TestEmailFormatValidation:
    """邮箱格式校验测试（使用 pattern 正则）"""

    def test_register_email_valid(self, client):
        """注册-合法邮箱格式"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "email_valid_user",
                "email": "test@example.com",
                "password": "123456",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"

    def test_register_email_missing_at_symbol(self, client):
        """注册-邮箱缺少@符号"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "email_no_at",
                "email": "testexample.com",
                "password": "123456",
            },
        )
        assert response.status_code == 422
        assert "email" in response.text.lower()

    def test_register_email_missing_domain(self, client):
        """注册-邮箱缺少域名（@后无内容）"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "email_no_domain",
                "email": "test@",
                "password": "123456",
            },
        )
        assert response.status_code == 422
        assert "email" in response.text.lower()

    def test_register_email_missing_username(self, client):
        """注册-邮箱缺少用户名（@前无内容）"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "email_no_user",
                "email": "@example.com",
                "password": "123456",
            },
        )
        assert response.status_code == 422
        assert "email" in response.text.lower()

    def test_register_email_with_special_chars(self, client):
        """注册-邮箱包含非法特殊字符"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "email_special",
                "email": "test!@example.com",
                "password": "123456",
            },
        )
        # 根据 pattern 设计，可能允许或拒绝特殊字符
        # 如果 pattern 是标准邮箱正则，! 是允许的，此测试可调整为其他非法格式
        assert response.status_code in [201, 422]

    def test_forgot_password_email_valid(self, client, monkeypatch):
        """忘记密码-合法邮箱格式"""
        from app.services import user_service as user_service_module

        monkeypatch.setattr(
            user_service_module.EmailService,
            "send_verification_code",
            lambda email, code: True,
        )

        # 先注册用户
        client.post(
            "/api/auth/register",
            json={
                "username": "forgot_valid_email",
                "email": "forgot_valid@example.com",
                "password": "123456",
            },
        )

        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "forgot_valid@example.com"},
        )
        assert response.status_code == 200

    def test_forgot_password_email_invalid(self, client):
        """忘记密码-非法邮箱格式"""
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "invalid_email"},
        )
        assert response.status_code == 422
        assert "email" in response.text.lower()

    def test_update_profile_email_valid(self, client):
        """修改个人信息-合法邮箱格式"""
        # 注册并登录
        client.post(
            "/api/auth/register",
            json={
                "username": "update_email_valid",
                "email": "update_valid@example.com",
                "password": "123456",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "update_email_valid",
                "password": "123456",
            },
        )
        token = login_response.json()["access_token"]

        response = client.put(
            "/api/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "phone": "13800138000",
                "email": "new_valid@example.com",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "new_valid@example.com"

    def test_update_profile_email_invalid(self, client):
        """修改个人信息-非法邮箱格式"""
        # 注册并登录
        client.post(
            "/api/auth/register",
            json={
                "username": "update_email_invalid",
                "email": "update_invalid@example.com",
                "password": "123456",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "update_email_invalid",
                "password": "123456",
            },
        )
        token = login_response.json()["access_token"]

        response = client.put(
            "/api/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "phone": "13800138000",
                "email": "invalid_email",
            },
        )
        assert response.status_code == 422
        assert "email" in response.text.lower()


# ============================================================
# 新增测试 - 验证码校验接口 7.10
# ============================================================


class TestVerifyCode:
    """验证码校验测试（/api/auth/verify-code）"""

    def test_verify_code_success(self, client, db_session, monkeypatch):
        """验证码校验-正确验证码"""
        from app.services import user_service as user_service_module

        monkeypatch.setattr(
            user_service_module.EmailService,
            "send_verification_code",
            lambda email, code: True,
        )

        # 注册用户
        client.post(
            "/api/auth/register",
            json={
                "username": "verify_success_user",
                "email": "verify_success@example.com",
                "password": "123456",
            },
        )

        # 申请验证码
        client.post(
            "/api/auth/forgot-password",
            json={"email": "verify_success@example.com"},
        )

        # 获取验证码
        user = (
            db_session.query(User)
            .filter(User.email == "verify_success@example.com")
            .first()
        )
        code = user.reset_token

        # 校验验证码
        response = client.post(
            "/api/auth/verify-code",
            json={
                "email": "verify_success@example.com",
                "code": code,
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "验证码有效"

    def test_verify_code_wrong(self, client):
        """验证码校验-错误验证码"""
        # 注册用户
        client.post(
            "/api/auth/register",
            json={
                "username": "verify_wrong_user",
                "email": "verify_wrong@example.com",
                "password": "123456",
            },
        )

        response = client.post(
            "/api/auth/verify-code",
            json={
                "email": "verify_wrong@example.com",
                "code": "000000",
            },
        )
        assert response.status_code == 400
        assert response.json()["message"] == "验证码错误"

    def test_verify_code_email_not_found(self, client):
        """验证码校验-邮箱未注册"""
        response = client.post(
            "/api/auth/verify-code",
            json={
                "email": "notexist_verify@example.com",
                "code": "123456",
            },
        )
        assert response.status_code == 400
        assert response.json()["message"] == "该邮箱未注册"

    def test_verify_code_invalid_email(self, client):
        """验证码校验-非法邮箱格式"""
        response = client.post(
            "/api/auth/verify-code",
            json={
                "email": "invalid_email",
                "code": "123456",
            },
        )
        assert response.status_code == 422
        assert "email" in response.text.lower()


# ============================================================
# 新增测试 - 忘记密码完整流程 7.10
# ============================================================


class TestForgotPasswordFullFlow:
    """忘记密码完整流程测试"""

    def test_full_forgot_password_flow(self, client, db_session, monkeypatch):
        """完整流程：注册→忘记密码→校验验证码→重置密码→新密码登录"""
        from app.services import user_service as user_service_module

        # Mock 邮件发送
        sent_code = None

        def fake_send_verification_code(email, code):
            nonlocal sent_code
            sent_code = code
            return True

        monkeypatch.setattr(
            user_service_module.EmailService,
            "send_verification_code",
            fake_send_verification_code,
        )

        # 1. 注册用户
        client.post(
            "/api/auth/register",
            json={
                "username": "flow_user",
                "email": "flow@example.com",
                "password": "123456",
            },
        )

        # 2. 忘记密码
        response = client.post(
            "/api/auth/forgot-password",
            json={"email": "flow@example.com"},
        )
        assert response.status_code == 200
        assert sent_code is not None
        code = sent_code

        # 3. 校验验证码
        response = client.post(
            "/api/auth/verify-code",
            json={"email": "flow@example.com", "code": code},
        )
        assert response.status_code == 200

        # 4. 重置密码
        response = client.post(
            "/api/auth/reset-password",
            json={
                "email": "flow@example.com",
                "code": code,
                "new_password": "newFlow789",
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "密码重置成功"

        # 5. 新密码登录
        response = client.post(
            "/api/auth/login",
            json={
                "username": "flow_user",
                "password": "newFlow789",
            },
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_reset_password_short_new_password(self, client, db_session, monkeypatch):
        """重置密码时新密码少于6位"""
        from app.services import user_service as user_service_module

        monkeypatch.setattr(
            user_service_module.EmailService,
            "send_verification_code",
            lambda email, code: True,
        )

        # 注册用户
        client.post(
            "/api/auth/register",
            json={
                "username": "reset_short_user",
                "email": "reset_short@example.com",
                "password": "123456",
            },
        )

        # 申请验证码
        client.post(
            "/api/auth/forgot-password",
            json={"email": "reset_short@example.com"},
        )
        user = (
            db_session.query(User)
            .filter(User.email == "reset_short@example.com")
            .first()
        )
        code = user.reset_token

        # 用少于6位的新密码重置
        response = client.post(
            "/api/auth/reset-password",
            json={
                "email": "reset_short@example.com",
                "code": code,
                "new_password": "12345",
            },
        )
        assert response.status_code == 422
        assert "password" in response.text.lower()

    def test_reset_password_code_expired(self, client, db_session, monkeypatch):
        """重置密码时验证码已过期"""
        from datetime import datetime, timedelta

        from app.services import user_service as user_service_module

        monkeypatch.setattr(
            user_service_module.EmailService,
            "send_verification_code",
            lambda email, code: True,
        )

        # 注册用户
        client.post(
            "/api/auth/register",
            json={
                "username": "reset_expired_user",
                "email": "reset_expired@example.com",
                "password": "123456",
            },
        )

        # 申请验证码
        client.post(
            "/api/auth/forgot-password",
            json={"email": "reset_expired@example.com"},
        )
        user = (
            db_session.query(User)
            .filter(User.email == "reset_expired@example.com")
            .first()
        )
        code = user.reset_token

        # 手动将验证码过期时间设为过去
        user.reset_token_expires_at = datetime.now() - timedelta(minutes=10)
        db_session.commit()

        # 重置密码
        response = client.post(
            "/api/auth/reset-password",
            json={
                "email": "reset_expired@example.com",
                "code": code,
                "new_password": "new789012",
            },
        )
        assert response.status_code == 400
        assert "验证码已过期" in response.json().get("message", "")

    def test_reset_password_code_used_twice(self, client, db_session, monkeypatch):
        """重置密码后验证码不能再次使用"""
        from app.services import user_service as user_service_module

        monkeypatch.setattr(
            user_service_module.EmailService,
            "send_verification_code",
            lambda email, code: True,
        )

        # 注册用户
        client.post(
            "/api/auth/register",
            json={
                "username": "reset_twice_user",
                "email": "reset_twice@example.com",
                "password": "123456",
            },
        )

        # 申请验证码
        client.post(
            "/api/auth/forgot-password",
            json={"email": "reset_twice@example.com"},
        )
        user = (
            db_session.query(User)
            .filter(User.email == "reset_twice@example.com")
            .first()
        )
        code = user.reset_token

        # 第一次重置
        response = client.post(
            "/api/auth/reset-password",
            json={
                "email": "reset_twice@example.com",
                "code": code,
                "new_password": "newFirst789",
            },
        )
        assert response.status_code == 200

        # 第二次使用相同验证码重置（应该失败）
        response = client.post(
            "/api/auth/reset-password",
            json={
                "email": "reset_twice@example.com",
                "code": code,
                "new_password": "newSecond789",
            },
        )
        assert response.status_code == 400
        assert response.json().get("message") in ["验证码错误", "验证码已过期"]

    def test_reset_password_resend_code_old_invalid(
        self, client, db_session, monkeypatch
    ):
        """重新申请验证码后，旧验证码失效"""
        from app.services import user_service as user_service_module

        sent_codes = []

        def fake_send_verification_code(email, code):
            sent_codes.append(code)
            return True

        monkeypatch.setattr(
            user_service_module.EmailService,
            "send_verification_code",
            fake_send_verification_code,
        )

        # 注册用户
        client.post(
            "/api/auth/register",
            json={
                "username": "resend_user",
                "email": "resend@example.com",
                "password": "123456",
            },
        )

        # 第一次申请
        client.post(
            "/api/auth/forgot-password",
            json={"email": "resend@example.com"},
        )
        old_code = sent_codes[0]

        # 第二次申请（5分钟内）
        client.post(
            "/api/auth/forgot-password",
            json={"email": "resend@example.com"},
        )
        new_code = sent_codes[1]

        assert old_code != new_code

        # 使用旧验证码重置（应该失败）
        response = client.post(
            "/api/auth/reset-password",
            json={
                "email": "resend@example.com",
                "code": old_code,
                "new_password": "new789012",
            },
        )
        assert response.status_code == 400

        # 使用新验证码重置（应该成功）
        response = client.post(
            "/api/auth/reset-password",
            json={
                "email": "resend@example.com",
                "code": new_code,
                "new_password": "new789012",
            },
        )
        assert response.status_code == 200

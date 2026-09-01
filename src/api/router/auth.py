"""认证 API 路由：用户注册、登录、获取当前用户信息。

支持 JWT Bearer Token 认证，注册时自动创建租户。
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.api_key import require_auth
from src.auth.context import AuthContext
from src.config.settings import Settings, get_settings
from src.db.models import Tenant, User
from src.db.postgres import get_db_session

router = APIRouter(prefix="/auth", tags=["认证"])


# ==================== Pydantic Schemas ====================


class RegisterRequest(BaseModel):
    """用户注册请求。

    注册时创建自己的工作空间（租户），用户成为该空间的首个成员。
    一个工作空间可以有多个用户协作。
    """

    username: str = Field(min_length=3, max_length=50, description="用户名（登录用）")
    password: str = Field(min_length=6, max_length=100, description="密码")
    display_name: str | None = Field(default=None, max_length=100, description="显示名称")
    workspace_name: str = Field(
        min_length=2, max_length=100, description="工作空间名称（公司/团队名）"
    )


class LoginRequest(BaseModel):
    """用户登录请求。"""

    username: str = Field(description="用户名")
    password: str = Field(description="密码")


class TokenResponse(BaseModel):
    """Token 响应。"""

    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token 类型")
    expires_in: int = Field(description="过期时间（秒）")
    user: "UserInfo" = Field(description="用户信息")


class UserInfo(BaseModel):
    """用户信息响应。"""

    id: int
    username: str
    display_name: str | None
    tenant_id: str
    tenant_name: str


class MeResponse(BaseModel):
    """当前用户响应。"""

    user: UserInfo
    tenant: dict


# ==================== 密码哈希 ====================


def hash_password(password: str) -> str:
    """使用 PBKDF2-HMAC-SHA256 哈希密码。

    Args:
        password: 明文密码。

    Returns:
        格式为 ``pbkdf2:sha256:<iterations>:<salt>:<hash>`` 的密码哈希。
    """
    salt = secrets.token_hex(16)
    iterations = 600_000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    return f"pbkdf2:sha256:{iterations}:{salt}:{dk.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码。

    Args:
        password: 明文密码。
        password_hash: 存储的密码哈希。

    Returns:
        密码是否正确。
    """
    try:
        parts = password_hash.split(":")
        if len(parts) != 5 or parts[0] != "pbkdf2" or parts[1] != "sha256":
            return False
        iterations = int(parts[2])
        salt = parts[3]
        stored_hash = parts[4]
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
        return secrets.compare_digest(dk.hex(), stored_hash)
    except (ValueError, AttributeError, IndexError):
        return False


# ==================== JWT 工具 ====================


def create_jwt_token(user: User, tenant: Tenant, settings: Settings) -> tuple[str, int]:
    """创建 JWT access token。

    Args:
        user: 用户对象。
        tenant: 租户对象。
        settings: 应用配置。

    Returns:
        (token_string, expires_in_seconds) 元组。
    """
    expires_in = settings.auth_jwt_expire_minutes * 60
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "tenant_id": user.tenant_id,
        "tenant_name": tenant.name,
        "scopes": ["*"],
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.auth_jwt_secret_key, algorithm="HS256")
    return token, expires_in


def decode_jwt_token(token: str, settings: Settings) -> dict:
    """解码并验证 JWT token。

    Args:
        token: JWT token 字符串。
        settings: 应用配置。

    Returns:
        解码后的 payload 字典。

    Raises:
        HTTPException: 401 当 token 无效或过期时。
    """
    try:
        payload = jwt.decode(token, settings.auth_jwt_secret_key, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token 无效")


def verify_jwt_token(token: str, settings: Settings) -> AuthContext:
    """验证 JWT token 并返回 AuthContext。

    Args:
        token: JWT token 字符串。
        settings: 应用配置。

    Returns:
        认证后的 AuthContext。
    """
    payload = decode_jwt_token(token, settings)
    return AuthContext(
        tenant_id=payload.get("tenant_id", "dev"),
        user_id=payload.get("username", payload.get("sub", "")),
        scopes=payload.get("scopes", ["*"]),
    )


# ==================== API 端点 ====================


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, settings: Settings = Depends(get_settings)) -> dict:
    """用户注册。

    自动创建租户并返回 JWT token。用户名和租户 ID 均需唯一。

    Args:
        request: 注册请求。
        settings: 应用配置。

    Returns:
        包含 JWT token 和用户信息的响应。

    Raises:
        HTTPException: 400 当用户名已存在时。
    """
    async with get_db_session() as session:
        # 检查用户名是否已存在
        result = await session.execute(select(User).where(User.username == request.username))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(status_code=400, detail=f"用户名 '{request.username}' 已被注册")

        # 生成唯一租户 ID
        tenant_id = f"tenant_{uuid.uuid4().hex[:12]}"
        while True:
            result = await session.execute(
                select(Tenant).where(Tenant.tenant_id == tenant_id)
            )
            if not result.scalar_one_or_none():
                break
            tenant_id = f"tenant_{uuid.uuid4().hex[:12]}"

        # 创建租户（工作空间）
        tenant = Tenant(
            tenant_id=tenant_id,
            name=request.workspace_name,
            is_active=True,
        )
        session.add(tenant)
        await session.flush()

        # 创建用户
        user = User(
            username=request.username,
            password_hash=hash_password(request.password),
            tenant_id=tenant_id,
            display_name=request.display_name or request.username,
            is_active=True,
        )
        session.add(user)
        await session.flush()
        await session.commit()

        # 生成 JWT
        token, expires_in = create_jwt_token(user, tenant, settings)

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "user": {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "tenant_id": user.tenant_id,
                "tenant_name": tenant.name,
            },
        }


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, settings: Settings = Depends(get_settings)) -> dict:
    """用户登录。

    验证用户名密码，返回 JWT token。

    Args:
        request: 登录请求。
        settings: 应用配置。

    Returns:
        包含 JWT token 和用户信息的响应。

    Raises:
        HTTPException: 401 当用户名或密码错误时。
    """
    async with get_db_session() as session:
        # 查找用户
        result = await session.execute(select(User).where(User.username == request.username))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        if not user.is_active:
            raise HTTPException(status_code=401, detail="账户已被禁用")

        # 验证密码
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        # 查找租户
        result = await session.execute(
            select(Tenant).where(Tenant.tenant_id == user.tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=401, detail="关联租户不存在")

        # 生成 JWT
        token, expires_in = create_jwt_token(user, tenant, settings)

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "user": {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "tenant_id": user.tenant_id,
                "tenant_name": tenant.name,
            },
        }


@router.get("/me", response_model=MeResponse)
async def get_me(auth: AuthContext = Depends(require_auth)) -> dict:
    """获取当前登录用户信息。

    Args:
        auth: 认证上下文。

    Returns:
        当前用户和租户信息。
    """
    async with get_db_session() as session:
        result = await session.execute(
            select(User).where(User.username == auth.user_id)
        )
        user = result.scalar_one_or_none()

        result = await session.execute(
            select(Tenant).where(Tenant.tenant_id == auth.tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not user:
            # 开发模式或 token 注册表模式
            return {
                "user": {
                    "id": 0,
                    "username": auth.user_id,
                    "display_name": auth.user_id,
                    "tenant_id": auth.tenant_id,
                    "tenant_name": auth.tenant_id,
                },
                "tenant": {
                    "tenant_id": auth.tenant_id,
                    "name": auth.tenant_id,
                    "is_active": True,
                },
            }

        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "tenant_id": user.tenant_id,
                "tenant_name": tenant.name if tenant else user.tenant_id,
            },
            "tenant": {
                "tenant_id": tenant.tenant_id if tenant else user.tenant_id,
                "name": tenant.name if tenant else user.tenant_id,
                "is_active": tenant.is_active if tenant else True,
            },
        }

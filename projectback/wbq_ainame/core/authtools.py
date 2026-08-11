import jwt
import settings
from datetime import datetime, timezone
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN
from dotenv import load_dotenv
load_dotenv()
import os
from models import AsyncSessionFactory
from models.User import User

'''
JWT 登录认证
1. JWT  JSON网络令牌
2. JWT 通常由三部分组成: Header.Payload.Signature   头.内容.签名
3. Header("alg","type")  Payload("user_id","type"="access" 访问短期的业务接口/"refresh" 自动辅助生成 access,"exp" 有效期)
 Signature( HS256(Header + Payload + 密钥) )  最后将这三个进行编码，这个密钥是自己随机给定的
4. 取 JWT 到请求头里面进行登录验证
'''


# 自定义密钥
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")


class AuthHandler:
    # 类属性
    security = HTTPBearer()      # 通过客户请求头里面的 Bearer 来验证
    algorithm = "HS256"          # 算法

    def __init__(self):
        # 实例属性
        self.secret = JWT_SECRET_KEY

    # 创建 JWT  Header.Payload.Signature  定义一个模版
    def _create_token(
        self,
        user_id: int,
        token_type: str,
        expires_delta,
        auth_version: int = 0,
    ):
        # Payload
        payload = {
            "user_id": user_id,
            "type": token_type,
            "auth_version": auth_version,
            "exp": datetime.now(timezone.utc) + expires_delta,
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)  # 创建jwt.encode()

    # 定义传参的内容，生成给用户
    def encode_login_token(self, user_id: int, auth_version: int = 0):  # use_id 是从 router 传入的
        return {
            "access_token": self._create_token(
                user_id=user_id,
                token_type="access",
                expires_delta=settings.JWT_ACCESS_TOKEN_EXPIRES,  # setting.__init__ 文件中放置的非保密配置参数，JWT 的 access 时间
                auth_version=auth_version,
            ),
            "refresh_token": self._create_token(
                user_id=user_id,
                token_type="refresh",
                expires_delta=settings.JWT_REFRESH_TOKEN_EXPIRES,   # JWT 的 refresh 时间
                auth_version=auth_version,
            )
        }

    # 更新 token 当用户的id 改变时
    def encode_update_token(self, user_id: int, auth_version: int = 0):
        return {
            "access_token": self._create_token(
                user_id=user_id,
                token_type="access",
                expires_delta=settings.JWT_ACCESS_TOKEN_EXPIRES,
                auth_version=auth_version,
            )
        }

    # 通过 token 来进行校验令牌
    def _decode_claims(self, token: str, token_type: str, status_code: int):
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])  # 解码令牌中 payload 信息

            if payload.get("type") != token_type:
                raise HTTPException(status_code=status_code, detail="Token类型错误")

            return {
                "user_id": int(payload["user_id"]),
                # 兼容上线前签发且没有版本字段的旧令牌。
                "auth_version": int(payload.get("auth_version", 0)),
            }

        except HTTPException:
            raise

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status_code, detail="Token已过期")

        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status_code, detail="Token无效")

        except Exception:
            raise HTTPException(status_code=status_code, detail="Token解析失败")

    def _decode_token(self, token: str, token_type: str, status_code: int):
        """保留原有公开行为，返回令牌中的用户 ID。"""
        return self._decode_claims(token, token_type, status_code)["user_id"]

    # access 解码的结果
    def decode_access_token(self, token: str):
        return self._decode_token(
            token=token,
            token_type="access",
            status_code=HTTP_401_UNAUTHORIZED,
        )

    # refresh 解码的结果
    def decode_refresh_token(self, token: str):
        return self._decode_token(
            token=token,
            token_type="refresh",
            status_code=HTTP_401_UNAUTHORIZED,
        )

    # HTTPBearer() 自动的切取  Authorization:Bearer  所有信息
    # Security(HTTPBearer()).credentials 得到 token 字符串信息 -> jwt.decode(auth.credentials) 得到 payload  -> payload["user_id"] == user_id
    async def _get_available_user(
        self,
        user_id: int,
        token_auth_version: int | None = None,
    ) -> User:
        async with AsyncSessionFactory() as session:
            user = await session.get(User, user_id)

        if not user or user.status == "deleted":
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="账号不存在或已失效")
        if user.status == "frozen":
            raise HTTPException(status_code=423, detail="账号已被冻结，请联系管理员")
        if user.status != "active":
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="账号状态异常")
        if (
            token_auth_version is not None
            and user.auth_version != token_auth_version
        ):
            raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="登录状态已失效")
        return user

    async def auth_access_dependency(
        self,
        auth: HTTPAuthorizationCredentials = Security(security),
    ):
        claims = self._decode_claims(
            auth.credentials,
            token_type="access",
            status_code=HTTP_401_UNAUTHORIZED,
        )
        user = await self._get_available_user(
            claims["user_id"],
            claims["auth_version"],
        )
        return user.id

    async def auth_refresh_dependency(
        self,
        auth: HTTPAuthorizationCredentials = Security(security),
    ):
        claims = self._decode_claims(
            auth.credentials,
            token_type="refresh",
            status_code=HTTP_401_UNAUTHORIZED,
        )
        return await self._get_available_user(
            claims["user_id"],
            claims["auth_version"],
        )

    async def admin_dependency(
        self,
        auth: HTTPAuthorizationCredentials = Security(security),
    ) -> int:
        claims = self._decode_claims(
            auth.credentials,
            token_type="access",
            status_code=HTTP_401_UNAUTHORIZED,
        )
        user = await self._get_available_user(
            claims["user_id"],
            claims["auth_version"],
        )
        if user.role != "admin":
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="需要管理员权限")
        return user.id

    async def expert_dependency(
        self,
        auth: HTTPAuthorizationCredentials = Security(security),
    ) -> int:
        """校验正式专家角色及专家资料状态。"""
        user_id = self.decode_access_token(auth.credentials)
        user = await self._get_available_user(user_id)
        if user.role != "expert":
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="需要专家权限")
        from sqlalchemy import select
        from modules.expert.expert_models import ExpertProfile

        async with AsyncSessionFactory() as session:
            profile = await session.scalar(
                select(ExpertProfile).where(ExpertProfile.user_id == user.id)
            )
        if not profile or profile.status != "approved":
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="专家资格未生效或已停用")
        return user.id

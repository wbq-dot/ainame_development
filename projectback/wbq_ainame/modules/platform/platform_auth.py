import hashlib
import secrets
from datetime import datetime, timezone

import jwt
from fastapi import Header, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy import select

import settings
from core.redistools import redis_client
from models import AsyncSessionFactory
from modules.platform.platform_models import DeveloperAccount, DeveloperApiKey


class DeveloperAuth:
    security = HTTPBearer()
    algorithm = "HS256"

    def _token(self, developer: DeveloperAccount, token_type: str, expires) -> str:
        payload = {
            "sub": str(developer.id),
            "aud": "developer",
            "type": token_type,
            "auth_version": developer.auth_version,
            "exp": datetime.now(timezone.utc) + expires,
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=self.algorithm)

    def login_tokens(self, developer: DeveloperAccount) -> dict:
        return {
            "access_token": self._token(developer, "access", settings.JWT_ACCESS_TOKEN_EXPIRES),
            "refresh_token": self._token(developer, "refresh", settings.JWT_REFRESH_TOKEN_EXPIRES),
        }

    async def _authenticate(self, credentials: HTTPAuthorizationCredentials, token_type: str) -> DeveloperAccount:
        try:
            claims = jwt.decode(
                credentials.credentials,
                settings.JWT_SECRET_KEY,
                algorithms=[self.algorithm],
                audience="developer",
            )
            if claims.get("type") != token_type:
                raise ValueError("wrong token type")
            developer_id = int(claims["sub"])
        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(401, "开发者登录已过期") from exc
        except Exception as exc:
            raise HTTPException(401, "开发者登录凭据无效") from exc
        async with AsyncSessionFactory() as session:
            developer = await session.get(DeveloperAccount, developer_id)
        if not developer or developer.status != "active":
            raise HTTPException(423 if developer else 401, "开发者账号不可用")
        if developer.auth_version != int(claims.get("auth_version", -1)):
            raise HTTPException(401, "开发者登录状态已失效")
        return developer

    async def access(self, credentials: HTTPAuthorizationCredentials = Security(security)) -> DeveloperAccount:
        return await self._authenticate(credentials, "access")

    async def refresh(self, credentials: HTTPAuthorizationCredentials = Security(security)) -> DeveloperAccount:
        return await self._authenticate(credentials, "refresh")


developer_auth = DeveloperAuth()


def api_key_digest(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_api_key() -> tuple[str, str, str]:
    raw = f"zn_live_{secrets.token_urlsafe(32)}"
    return raw, raw[:16], api_key_digest(raw)


async def api_key_dependency(x_api_key: str = Header(..., alias="X-API-Key")) -> tuple[DeveloperApiKey, DeveloperAccount]:
    digest = api_key_digest(x_api_key)
    async with AsyncSessionFactory() as session:
        pair = (
            await session.execute(
                select(DeveloperApiKey, DeveloperAccount)
                .join(DeveloperAccount, DeveloperAccount.id == DeveloperApiKey.developer_id)
                .where(DeveloperApiKey.key_digest == digest)
            )
        ).first()
        if not pair or pair[0].status != "active" or pair[1].status != "active":
            raise HTTPException(401, "API Key 无效或已停用")
        key, developer = pair
        try:
            bucket = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
            rate_key = f"platform:rate:{key.id}:{bucket}"
            count = await redis_client.incr(rate_key)
            if count == 1:
                await redis_client.expire(rate_key, 70)
        except Exception as exc:
            raise HTTPException(503, "调用限速服务暂不可用") from exc
        if count > developer.rate_limit_per_minute:
            raise HTTPException(429, "API Key 调用频率超过限制")
        key.last_used_at = datetime.now()
        await session.commit()
        return key, developer


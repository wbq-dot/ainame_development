import os
import textwrap

from alipay import AliPay

import settings


class PaymentConfigurationError(RuntimeError):
    pass


SANDBOX_GATEWAY = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"
PRODUCTION_GATEWAY = "https://openapi.alipay.com/gateway.do"


def _format_key(key: str, label: str, begin: str, end: str) -> str:
    if not key:
        raise PaymentConfigurationError(f"{label}未配置")
    normalized = key.replace(" ", "").replace("\n", "")
    wrapped = "\n".join(textwrap.wrap(normalized, 64))
    return f"{begin}\n{wrapped}\n{end}"


def format_private_key(key: str) -> str:
    return _format_key(
        key,
        "支付宝应用私钥",
        "-----BEGIN RSA PRIVATE KEY-----",
        "-----END RSA PRIVATE KEY-----",
    )


def format_public_key(key: str) -> str:
    return _format_key(
        key,
        "支付宝公钥",
        "-----BEGIN PUBLIC KEY-----",
        "-----END PUBLIC KEY-----",
    )


def validate_payment_settings() -> None:
    if settings.ALIPAY_ENVIRONMENT not in {"sandbox", "production"}:
        raise PaymentConfigurationError(
            "ALIPAY_ENVIRONMENT 必须是 sandbox 或 production"
        )
    required = {
        "ALIPAY_APP_ID": settings.ALIPAY_APP_ID,
        "ALIPAY_SELLER_ID": settings.ALIPAY_SELLER_ID,
        "ALIPAY_NOTIFY_URL": settings.ALIPAY_NOTIFY_URL,
        "ALIPAY_RETURN_URL": settings.ALIPAY_RETURN_URL,
        "ALIPAY_APP_PRIVATE_KEY": settings.ALIPAY_APP_PRIVATE_KEY,
        "ALIPAY_PUBLIC_KEY": settings.ALIPAY_PUBLIC_KEY,
        "PAYMENT_FRONTEND_RESULT_URL": settings.PAYMENT_FRONTEND_RESULT_URL,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise PaymentConfigurationError(
            f"支付功能缺少配置：{', '.join(missing)}"
        )


def create_alipay() -> AliPay:
    if not settings.PAYMENT_ENABLED:
        raise PaymentConfigurationError("支付功能未启用")
    validate_payment_settings()
    return AliPay(
        appid=settings.ALIPAY_APP_ID,
        app_notify_url=settings.ALIPAY_NOTIFY_URL,
        app_private_key_string=format_private_key(settings.ALIPAY_APP_PRIVATE_KEY),
        alipay_public_key_string=format_public_key(settings.ALIPAY_PUBLIC_KEY),
        sign_type="RSA2",
        debug=settings.ALIPAY_ENVIRONMENT == "sandbox",
    )


def get_alipay_gateway() -> str:
    configured = os.getenv("ALIPAY_GATEWAY", "").strip()
    if configured:
        return configured
    if settings.ALIPAY_ENVIRONMENT == "sandbox":
        return SANDBOX_GATEWAY
    return PRODUCTION_GATEWAY


def get_return_url() -> str:
    return settings.ALIPAY_RETURN_URL


def get_notify_url() -> str:
    return settings.ALIPAY_NOTIFY_URL

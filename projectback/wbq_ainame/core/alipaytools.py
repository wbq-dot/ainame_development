import os
import textwrap
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

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


def verify_alipay_response(
    raw_params: Mapping[str, Any],
    *,
    require_seller_id: bool = False,
) -> dict[str, Any] | None:
    """验签并校验支付宝应用身份，成功时返回移除签名字段后的参数。"""
    params = dict(raw_params)
    sign = params.pop("sign", None)
    sign_type = params.pop("sign_type", None)
    if not sign or sign_type != "RSA2":
        return None
    if not create_alipay().verify(params, str(sign)):
        return None
    if params.get("app_id") != settings.ALIPAY_APP_ID:
        return None
    if require_seller_id and params.get("seller_id") != settings.ALIPAY_SELLER_ID:
        return None
    return params


def parse_alipay_amount(value: Any) -> Decimal | None:
    """安全解析支付宝金额，拒绝空值、非法小数和非有限数。"""
    if value in (None, ""):
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return amount if amount.is_finite() else None


def build_alipay_page_pay_url(
    *,
    out_trade_no: str,
    subject: str,
    total_amount: str,
    return_url: str,
    notify_url: str | None = None,
) -> str:
    """使用统一参数生成支付宝电脑网站支付链接。"""
    gateway = get_alipay_gateway()
    if not gateway:
        raise ValueError("支付宝网关尚未配置")
    if not return_url:
        raise ValueError("支付宝浏览器返回地址尚未配置")

    pay_kwargs = {
        "out_trade_no": out_trade_no,
        "subject": subject,
        "total_amount": total_amount,
        "timeout_express": f"{settings.PAYMENT_ORDER_TIMEOUT_MINUTES}m",
        "return_url": return_url,
    }
    if notify_url:
        pay_kwargs["notify_url"] = notify_url

    order_string = create_alipay().api_alipay_trade_page_pay(**pay_kwargs)
    return f"{gateway}?{order_string}"


def get_expert_return_url():
    return os.getenv("EXPERT_ALIPAY_RETURN_URL") or _derive_expert_url(
        get_return_url(), "/pay/success", "/expert-pay/return"
    )


def get_expert_notify_url():
    return os.getenv("EXPERT_ALIPAY_NOTIFY_URL") or _derive_expert_url(
        get_notify_url(), "/pay/paySuccess", "/expert-pay/notify"
    )


def _derive_expert_url(source_url: str | None, old_path: str, new_path: str):
    """优先保留现有反向代理路径，无法匹配时使用同域名根路径。"""
    if not source_url:
        return None
    parts = urlsplit(source_url)
    path = parts.path
    if path.endswith(old_path):
        path = f"{path[:-len(old_path)]}{new_path}"
    else:
        path = new_path
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


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

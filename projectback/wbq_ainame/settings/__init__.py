# 非保密配置文件

from datetime import timedelta
import os
from dotenv import load_dotenv
load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")

JWT_ACCESS_TOKEN_EXPIRES=timedelta(minutes=15)
JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30)


QUEUE_NAME = "rag_document_queue"

# 将这个 .env 先导入到settings 文件再倒入其他文件
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL", "").strip().rstrip("/")
WANXIANG_MODEL = os.getenv("WANXIANG_MODEL", "wan2.6-t2i")
APP_BASE_URL = os.getenv("APP_BASE_URL",
"http://127.0.0.1:8000").strip().rstrip("/")
ADMIN_BOOTSTRAP_SECRET = os.getenv("ADMIN_BOOTSTRAP_SECRET", "").strip()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


ALIPAY_APP_ID = os.getenv("ALIPAY_APP_ID", "").strip()
ALIPAY_SELLER_ID = os.getenv("ALIPAY_SELLER_ID", "").strip()
ALIPAY_NOTIFY_URL = os.getenv("ALIPAY_NOTIFY_URL", "").strip()
ALIPAY_RETURN_URL = os.getenv("ALIPAY_RETURN_URL", "").strip()
ALIPAY_APP_PRIVATE_KEY = os.getenv("ALIPAY_APP_PRIVATE_KEY", "").strip()
ALIPAY_PUBLIC_KEY = os.getenv("ALIPAY_PUBLIC_KEY", "").strip()
ALIPAY_ENVIRONMENT = os.getenv("ALIPAY_ENVIRONMENT", "sandbox").strip().lower()
PAYMENT_ENABLED = _env_bool("PAYMENT_ENABLED", bool(ALIPAY_APP_ID))
PAYMENT_FRONTEND_RESULT_URL = os.getenv(
    "PAYMENT_FRONTEND_RESULT_URL",
    "http://127.0.0.1:8080/#/pages/payment/result",
).strip()
DEVELOPER_PAYMENT_RESULT_URL = os.getenv(
    "DEVELOPER_PAYMENT_RESULT_URL",
    "http://127.0.0.1:8080/#/pages/developer/console?section=billing",
).strip()
PAYMENT_ORDER_TIMEOUT_MINUTES = max(
    1, int(os.getenv("PAYMENT_ORDER_TIMEOUT_MINUTES", "60"))
)
PAYMENT_RECONCILE_INTERVAL_SECONDS = max(
    10, int(os.getenv("PAYMENT_RECONCILE_INTERVAL_SECONDS", "30"))
)
PAYMENT_RECONCILE_BATCH_SIZE = min(
    100, max(1, int(os.getenv("PAYMENT_RECONCILE_BATCH_SIZE", "50")))
)
REFUND_WINDOW_HOURS = max(1, int(os.getenv("REFUND_WINDOW_HOURS", "24")))


def _split_env_list(value: str) -> list[str]:
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


# H5 联调可通过 CORS_ORIGINS 追加准确来源，多个地址使用英文逗号分隔。
CORS_ORIGINS = _split_env_list(os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080",
))

# 默认只额外允许本机和局域网地址，便于 HBuilderX H5/真机联调。
CORS_ORIGIN_REGEX = os.getenv(
    "CORS_ORIGIN_REGEX",
    r"^https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?$",
)

MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(10 * 1024 * 1024)))

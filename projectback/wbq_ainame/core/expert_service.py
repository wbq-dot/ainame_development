import os
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile


COMMISSION_RATE = Decimal("0.2000")
MAX_PDF_SIZE = 10 * 1024 * 1024
MAX_ORDER_IMAGE_SIZE = 5 * 1024 * 1024
MAX_ORDER_IMAGES = 3
EXPERT_TIERS = {
    "ordinary": {
        "code": "ordinary",
        "name": "普通专家",
        "price": Decimal("29.90"),
        "delivery_days": 3,
        "description": "由审核通过的起名专家接单，提供结构化起名方案与一次修改。",
    },
    "renowned": {
        "code": "renowned",
        "name": "知名专家",
        "price": Decimal("69.90"),
        "delivery_days": 2,
        "description": "由知名级起名专家接单，提供更深入的五行与寓意分析。",
    },
    "top": {
        "code": "top",
        "name": "顶级专家",
        "price": Decimal("159.90"),
        "delivery_days": 1,
        "description": "由顶级起名专家优先接单，提供完整命名方案与重点答复。",
    },
}
ORDER_IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def calculate_commission(amount: Decimal) -> tuple[Decimal, Decimal]:
    fee = (amount * COMMISSION_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return fee, amount - fee


def create_expert_order_no(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return f"EX{current.strftime('%Y%m%d%H%M%S')}{uuid4().hex[:8].upper()}"


def private_storage_dir() -> Path:
    default_dir = Path(__file__).resolve().parents[1] / "private_storage" / "expert"
    return Path(os.getenv("EXPERT_PRIVATE_STORAGE_DIR", str(default_dir))).resolve()


async def save_private_pdf(file: UploadFile, prefix: str) -> tuple[str, str, int, str]:
    filename = Path(file.filename or "report.pdf").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")
    content_type = (file.content_type or "").lower()
    if content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="文件类型必须是 PDF")

    content = await file.read(MAX_PDF_SIZE + 1)
    if len(content) > MAX_PDF_SIZE:
        raise HTTPException(status_code=413, detail="PDF 文件不能超过 10MB")
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="文件内容不是有效的 PDF")

    target_dir = private_storage_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    key = f"{prefix}_{uuid4().hex}.pdf"
    (target_dir / key).write_bytes(content)
    return key, filename, len(content), "application/pdf"


async def save_private_image(file: UploadFile, prefix: str) -> tuple[str, str, int, str]:
    filename = Path(file.filename or "customer-image").name
    extension = Path(filename).suffix.lower()
    if extension not in ORDER_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="仅支持 JPG、PNG 或 WEBP 图片")
    content_type = (file.content_type or "").lower()
    expected_type = ORDER_IMAGE_TYPES[extension]
    if content_type not in {expected_type, "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="上传文件类型与图片扩展名不一致")

    content = await file.read(MAX_ORDER_IMAGE_SIZE + 1)
    if len(content) > MAX_ORDER_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="单张客户图片不能超过 5MB")
    is_jpeg = content.startswith(b"\xff\xd8\xff")
    is_png = content.startswith(b"\x89PNG\r\n\x1a\n")
    is_webp = len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    signature_ok = {
        "image/jpeg": is_jpeg,
        "image/png": is_png,
        "image/webp": is_webp,
    }[expected_type]
    if not signature_ok:
        raise HTTPException(status_code=400, detail="文件内容不是有效图片")

    target_dir = private_storage_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    stored_extension = ".jpg" if expected_type == "image/jpeg" else extension
    key = f"{prefix}_{uuid4().hex}{stored_extension}"
    (target_dir / key).write_bytes(content)
    return key, filename, len(content), expected_type


def private_file_path(key: str) -> Path:
    safe_name = Path(key).name
    target = (private_storage_dir() / safe_name).resolve()
    if target.parent != private_storage_dir() or not target.is_file():
        raise HTTPException(status_code=404, detail="附件不存在")
    return target


def paid_deadlines(now: datetime) -> tuple[datetime, datetime]:
    return now + timedelta(hours=24), now + timedelta(hours=1)


def delivery_deadline(now: datetime, delivery_days: int) -> datetime:
    return now + timedelta(days=delivery_days)


def confirmation_deadline(now: datetime) -> datetime:
    return now + timedelta(days=7)

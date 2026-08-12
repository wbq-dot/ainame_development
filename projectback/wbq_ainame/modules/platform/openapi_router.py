import csv
import io
import time
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.rag_service import KnowledgeRetrievalUnavailableError
from core.workflow import generate_naming
from dependencies import get_session
from modules.platform.platform_auth import api_key_dependency
from modules.platform.platform_models import DeveloperAccount, DeveloperApiKey
from modules.platform.platform_repo import PlatformConflict, PlatformNotFound, PlatformRepository
from modules.platform.platform_schemas import BatchCreateIn, PublicNameOut
from modules.platform.task_service import publish_or_mark_failed
from schemas.name_schemas import NameIn


router = APIRouter(prefix="/openapi/v1", tags=["openapi-v1"])


def docs_description() -> str:
    return "使用 X-API-Key 认证。收费 POST 请求必须提供 Idempotency-Key；同一键可安全重试。"


@router.post("/names/generate", response_model=PublicNameOut, description=docs_description())
async def generate_name(
    data: NameIn,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=100),
    identity: tuple[DeveloperApiKey, DeveloperAccount] = Depends(api_key_dependency),
    session: AsyncSession = Depends(get_session),
):
    key, developer = identity
    repo = PlatformRepository(session)
    payload = data.model_dump(mode="json")
    try: call, created = await repo.create_call(developer.id, key.id, "/openapi/v1/names/generate", idempotency_key, payload)
    except PlatformConflict as exc: raise HTTPException(409, str(exc)) from exc
    if call.status == "succeeded": return call.response_data
    if not created and call.status == "processing": raise HTTPException(409, "相同请求正在处理中，请稍后重试")
    if not created and call.status == "failed": raise HTTPException(409, "该幂等请求此前已失败，请使用新的 Idempotency-Key 重试")
    started = time.perf_counter()
    try:
        await repo.reserve_credits(developer.id, 1, call.request_no)
        result = await generate_naming(data, developer.id, use_private_knowledge=False)
        output = result.get("final_output") or {}
        if not output.get("names"): raise ValueError("模型没有返回有效候选名字")
        remaining = await repo.finalize_credits(developer.id, 1, call.request_no)
        response = {"request_no": call.request_no, "names": output["names"], "remaining_credits": remaining}
        await repo.complete_call(call.id, status="succeeded", response=response, credits=1, duration_ms=int((time.perf_counter()-started)*1000))
        return response
    except PlatformConflict as exc:
        await repo.complete_call(call.id, status="failed", response=None, credits=0, duration_ms=int((time.perf_counter()-started)*1000), error_type="insufficient_credit")
        raise HTTPException(402, str(exc)) from exc
    except KnowledgeRetrievalUnavailableError as exc:
        await repo.release_credits(developer.id, 1)
        await repo.complete_call(call.id, status="failed", response=None, credits=0, duration_ms=int((time.perf_counter()-started)*1000), error_type="knowledge_unavailable")
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        await repo.release_credits(developer.id, 1)
        await repo.complete_call(call.id, status="failed", response=None, credits=0, duration_ms=int((time.perf_counter()-started)*1000), error_type=type(exc).__name__)
        raise HTTPException(502, "命名服务暂不可用，本次未扣费") from exc


@router.post("/batches", status_code=202, description=docs_description())
async def create_batch(
    data: BatchCreateIn,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=100),
    identity: tuple[DeveloperApiKey, DeveloperAccount] = Depends(api_key_dependency),
    session: AsyncSession = Depends(get_session),
):
    key, developer = identity; repo = PlatformRepository(session)
    payload = data.model_dump(mode="json")
    try: call, created = await repo.create_call(developer.id, key.id, "/openapi/v1/batches", idempotency_key, payload)
    except PlatformConflict as exc: raise HTTPException(409, str(exc)) from exc
    if call.response_data: return call.response_data
    if not created: raise HTTPException(409, "相同批量请求正在处理中，请稍后重试")
    try: await repo.reserve_credits(developer.id, len(data.items), call.request_no)
    except PlatformConflict as exc:
        await repo.complete_call(call.id, status="failed", response=None, credits=0, duration_ms=0, error_type="insufficient_credit")
        raise HTTPException(402, str(exc)) from exc
    task = await repo.create_task(task_type="batch_naming", owner_type="developer", owner_id=developer.id, api_key_id=key.id, total=len(data.items), reserved=len(data.items), payload=None, items=[item.model_dump(mode="json") for item in data.items])
    response = {"request_no": call.request_no, "task_id": task.task_no, "status": task.status, "total_count": task.total_count}
    await repo.complete_call(call.id, status="succeeded", response=response, credits=0, duration_ms=0)
    published = await publish_or_mark_failed(task.task_no)
    if not published: response["status"] = "publish_failed"
    return response


@router.get("/batches/{task_id}")
async def batch_detail(task_id: str, identity: tuple[DeveloperApiKey, DeveloperAccount] = Depends(api_key_dependency), session: AsyncSession = Depends(get_session)):
    _, developer = identity
    try: return await PlatformRepository(session).task_detail(task_id, "developer", developer.id)
    except PlatformNotFound as exc: raise HTTPException(404, str(exc)) from exc


@router.get("/batches/{task_id}/export")
async def batch_export(task_id: str, identity: tuple[DeveloperApiKey, DeveloperAccount] = Depends(api_key_dependency), session: AsyncSession = Depends(get_session)):
    _, developer = identity
    try: detail = await PlatformRepository(session).task_detail(task_id, "developer", developer.id)
    except PlatformNotFound as exc: raise HTTPException(404, str(exc)) from exc
    buffer = io.StringIO(); writer = csv.writer(buffer); writer.writerow(["序号", "状态", "输入", "结果", "错误"])
    for item in detail["items"]: writer.writerow([item.item_index+1, item.status, str(item.input_data or ""), str(item.output_data or ""), item.error or ""])
    content = "\ufeff" + buffer.getvalue()
    return StreamingResponse(iter([content.encode("utf-8")]), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{task_id}.csv"'})

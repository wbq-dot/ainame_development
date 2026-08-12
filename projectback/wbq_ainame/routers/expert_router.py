from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.alipaytools import (
    build_alipay_page_pay_url,
    get_expert_notify_url,
    get_expert_return_url,
)
from core.authtools import AuthHandler
from dependencies import get_session
from models.User import User
from models.expert_models import ExpertOrder, ExpertOrderAttachment, ExpertProfile
from repository.expert_repo import ExpertDomainError, ExpertRepository
from schemas.expert_schemas import (
    ExpertApplicationIn,
    ExpertApplicationOut,
    ExpertOrderCreateIn,
    ExpertOrderCreatedOut,
    ExpertOrderAttachmentOut,
    ExpertOrderOut,
    ExpertPackageIn,
    ExpertPackageOut,
    ExpertProfileOut,
    ExpertReportOut,
    ExpertReportIn,
    ExpertTierOut,
    ExpertReviewIn,
    IncomeSummaryOut,
    SettlementCreateIn,
    SettlementOut,
    TextReasonIn,
)
from core.expert_service import (
    MAX_ORDER_IMAGES,
    EXPERT_TIERS,
    private_file_path,
    save_private_image,
    save_private_pdf,
)


router = APIRouter(tags=["expert-service"])
payment_status_router = APIRouter(prefix="/expert-pay", tags=["expert-pay"])
auth_handler = AuthHandler()


def _raise_domain(exc: ExpertDomainError):
    raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


def _build_expert_pay_url(order: ExpertOrder) -> str:
    notify_url = get_expert_notify_url()
    return_url = get_expert_return_url()
    if not return_url:
        raise HTTPException(status_code=503, detail="专家订单支付宝浏览器返回地址尚未配置")
    return build_alipay_page_pay_url(
        out_trade_no=order.order_no,
        subject=f"专家精批-{order.package_name}",
        total_amount=str(order.amount),
        notify_url=notify_url,
        return_url=return_url,
    )


async def _require_order_asset_access(
    session: AsyncSession, order_id: int, user_id: int
) -> ExpertOrder:
    order = await session.get(ExpertOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    user = await session.get(User, user_id)
    profile = await session.get(ExpertProfile, order.expert_id)
    viewer_profile = await session.scalar(
        select(ExpertProfile).where(
            ExpertProfile.user_id == user_id,
            ExpertProfile.status == "approved",
        )
    )
    pool_access = (
        viewer_profile
        and order.expert_id is None
        and order.payment_status == "paid"
        and order.service_status == "pending_acceptance"
        and order.expert_level == viewer_profile.expert_level
    )
    allowed = order.user_id == user_id or (user and user.role == "admin") or (
        profile and profile.user_id == user_id
    ) or pool_access
    if not allowed:
        raise HTTPException(status_code=403, detail="无权查看该订单的客户图片")
    return order


@router.get("/experts", response_model=list[ExpertProfileOut])
async def list_experts(session: AsyncSession = Depends(get_session)):
    return await ExpertRepository(session).list_public_experts()


@router.get("/expert-tiers", response_model=list[ExpertTierOut])
async def list_expert_tiers():
    return list(EXPERT_TIERS.values())


@router.get("/expert-packages", response_model=list[ExpertPackageOut])
async def list_public_packages(
    expert_id: int | None = None,
    session: AsyncSession = Depends(get_session),
):
    return await ExpertRepository(session).list_public_packages(expert_id)


@router.get("/expert-packages/{package_id}", response_model=ExpertPackageOut)
async def public_package_detail(
    package_id: int,
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).get_public_package(package_id)
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.get("/expert-applications/me", response_model=ExpertApplicationOut | None)
async def my_application(
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    return await ExpertRepository(session).profile_for_user(user_id)


@router.post("/expert-applications", response_model=ExpertApplicationOut)
async def submit_application(
    data: ExpertApplicationIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).submit_application(
            user_id, data.model_dump()
        )
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.post("/expert-applications/credential", response_model=ExpertApplicationOut)
async def upload_expert_credential(
    credential: UploadFile = File(...),
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    profile = await ExpertRepository(session).profile_for_user(user_id)
    if not profile or profile.status not in {"pending", "rejected"}:
        raise HTTPException(status_code=409, detail="当前申请状态不能上传资质附件")
    saved = await save_private_pdf(credential, f"credential_{user_id}")
    try:
        return await ExpertRepository(session).attach_credential(user_id, saved)
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.get("/expert-applications/{profile_id}/credential")
async def download_expert_credential(
    profile_id: int,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    profile = await session.get(ExpertProfile, profile_id)
    user = await session.get(User, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="专家申请不存在")
    if profile.user_id != user_id and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权下载该资质附件")
    if not profile.credential_file_key:
        raise HTTPException(status_code=404, detail="申请没有资质附件")
    return FileResponse(
        private_file_path(profile.credential_file_key),
        media_type="application/pdf",
        filename=profile.credential_file_name or "expert-credential.pdf",
    )


@router.get("/expert-workbench/profile", response_model=ExpertProfileOut)
async def expert_profile(
    user_id: int = Depends(auth_handler.expert_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).require_expert_profile(user_id)
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.get("/expert-workbench/packages", response_model=list[ExpertPackageOut])
async def expert_packages(
    user_id: int = Depends(auth_handler.expert_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).list_expert_packages(user_id)
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.post("/expert-workbench/packages", response_model=ExpertPackageOut)
async def create_expert_package(
    data: ExpertPackageIn,
    user_id: int = Depends(auth_handler.expert_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).save_package(user_id, data.model_dump())
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.put("/expert-workbench/packages/{package_id}", response_model=ExpertPackageOut)
async def update_expert_package(
    package_id: int,
    data: ExpertPackageIn,
    user_id: int = Depends(auth_handler.expert_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).save_package(
            user_id, data.model_dump(), package_id
        )
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.post("/expert-workbench/packages/{package_id}/submit", response_model=ExpertPackageOut)
async def submit_expert_package(
    package_id: int,
    user_id: int = Depends(auth_handler.expert_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).submit_package(user_id, package_id)
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.post("/expert-orders", response_model=ExpertOrderCreatedOut)
async def create_expert_order(
    data: ExpertOrderCreateIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    if not get_expert_return_url():
        raise HTTPException(status_code=503, detail="专家订单支付宝浏览器返回地址尚未配置")
    try:
        order = await ExpertRepository(session).create_order(user_id, data.model_dump())
    except ExpertDomainError as exc:
        _raise_domain(exc)

    values = ExpertRepository._order_dict(order)
    values["pay_url"] = _build_expert_pay_url(order)
    return values


@router.get("/expert-orders/mine", response_model=list[ExpertOrderOut])
async def my_expert_orders(
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).list_orders(user_id)
    except ExpertDomainError as exc:
        _raise_domain(exc)


@payment_status_router.get("/status/{order_no}")
async def expert_payment_status(
    order_no: str,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    order = await session.scalar(
        select(ExpertOrder).where(
            ExpertOrder.order_no == order_no,
            ExpertOrder.user_id == user_id,
        )
    )
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return {
        "order_no": order.order_no,
        "payment_status": order.payment_status,
        "service_status": order.service_status,
    }


@router.get("/expert-orders/{order_id}", response_model=ExpertOrderOut)
async def expert_order_detail(
    order_id: int,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).order_detail(order_id, user_id)
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.post(
    "/expert-orders/{order_id}/images", response_model=ExpertOrderAttachmentOut
)
async def upload_expert_order_image(
    order_id: int,
    image: UploadFile = File(...),
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    repository = ExpertRepository(session)
    try:
        order = await repository.get_order_for_user(order_id, user_id)
        existing = await repository.list_order_attachments(order.id)
        if len(existing) >= MAX_ORDER_IMAGES:
            raise HTTPException(
                status_code=400,
                detail=f"每个订单最多上传 {MAX_ORDER_IMAGES} 张客户图片",
            )
        if order.payment_status != "unpaid" or order.service_status != "pending_payment":
            raise HTTPException(status_code=409, detail="只能在订单付款前补充客户图片")
        saved = await save_private_image(image, f"order_{order_id}")
        return await repository.add_order_attachment(
            order_id, user_id, saved, MAX_ORDER_IMAGES
        )
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.get(
    "/expert-orders/{order_id}/images", response_model=list[ExpertOrderAttachmentOut]
)
async def list_expert_order_images(
    order_id: int,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    await _require_order_asset_access(session, order_id, user_id)
    return await ExpertRepository(session).list_order_attachments(order_id)


@router.get("/expert-orders/{order_id}/images/{attachment_id}")
async def download_expert_order_image(
    order_id: int,
    attachment_id: int,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    await _require_order_asset_access(session, order_id, user_id)
    item = await session.scalar(
        select(ExpertOrderAttachment).where(
            ExpertOrderAttachment.id == attachment_id,
            ExpertOrderAttachment.order_id == order_id,
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail="客户图片不存在")
    return FileResponse(
        private_file_path(item.file_key),
        media_type=item.content_type,
        filename=item.file_name,
    )


@router.post("/expert-orders/{order_id}/cancel", response_model=ExpertOrderOut)
async def cancel_expert_order(
    order_id: int,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).cancel_unpaid(order_id, user_id)
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.post("/expert-orders/{order_id}/pay-link")
async def recreate_expert_pay_link(
    order_id: int,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        order = await ExpertRepository(session).get_order_for_user(order_id, user_id)
    except ExpertDomainError as exc:
        _raise_domain(exc)
    if order.payment_status != "unpaid" or order.service_status != "pending_payment":
        raise HTTPException(status_code=409, detail="当前订单不能继续支付")
    return {"order_no": order.order_no, "pay_url": _build_expert_pay_url(order)}


@router.post("/expert-orders/{order_id}/revision", response_model=ExpertOrderOut)
async def request_report_revision(
    order_id: int,
    data: TextReasonIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).request_revision(
            order_id, user_id, data.reason
        )
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.post("/expert-orders/{order_id}/confirm", response_model=ExpertOrderOut)
async def confirm_expert_order(
    order_id: int,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).user_confirm(order_id, user_id)
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.post("/expert-orders/{order_id}/dispute", response_model=ExpertOrderOut)
async def dispute_expert_order(
    order_id: int,
    data: TextReasonIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).dispute(order_id, user_id, data.reason)
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.post("/expert-orders/{order_id}/reviews")
async def review_expert_order(
    order_id: int,
    data: ExpertReviewIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        review = await ExpertRepository(session).add_review(
            order_id, user_id, data.rating, data.content
        )
        return {"message": "评价已提交", "review_id": review.id}
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.get("/expert-orders/{order_id}/report", response_model=ExpertReportOut)
async def get_expert_report(
    order_id: int,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).latest_report(order_id, user_id)
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.get("/expert-orders/{order_id}/report/attachment")
async def download_report_attachment(
    order_id: int,
    user_id: int = Depends(auth_handler.auth_access_dependency),
    session: AsyncSession = Depends(get_session),
):
    order = await session.get(ExpertOrder, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    user = await session.get(User, user_id)
    profile = await session.get(ExpertProfile, order.expert_id)
    allowed = order.user_id == user_id or user.role == "admin" or (
        profile and profile.user_id == user_id
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="无权下载该报告")
    try:
        report = await ExpertRepository(session).latest_report(
            order_id, order.user_id
        )
    except ExpertDomainError as exc:
        _raise_domain(exc)
    if not report.attachment_key:
        raise HTTPException(status_code=404, detail="报告没有 PDF 附件")
    return FileResponse(
        private_file_path(report.attachment_key),
        media_type="application/pdf",
        filename=report.attachment_name or "expert-report.pdf",
    )


@router.get("/expert-workbench/orders", response_model=list[ExpertOrderOut])
async def expert_workbench_orders(
    user_id: int = Depends(auth_handler.expert_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).list_orders(user_id, expert=True)
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.post("/expert-workbench/orders/{order_id}/accept", response_model=ExpertOrderOut)
async def accept_order(
    order_id: int,
    user_id: int = Depends(auth_handler.expert_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).expert_accept(order_id, user_id, True)
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.post("/expert-workbench/orders/{order_id}/reject", response_model=ExpertOrderOut)
async def reject_order(
    order_id: int,
    user_id: int = Depends(auth_handler.expert_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).expert_accept(order_id, user_id, False)
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.post("/expert-workbench/orders/{order_id}/report", response_model=ExpertReportOut)
async def submit_expert_report(
    order_id: int,
    conclusion: str = Form(..., min_length=10, max_length=1000),
    analysis: str = Form(..., min_length=30, max_length=10000),
    suggestions: str = Form(..., min_length=10, max_length=5000),
    recommended_names: str | None = Form(default=None, max_length=5000),
    five_elements_analysis: str | None = Form(default=None, max_length=10000),
    final_reply: str | None = Form(default=None, max_length=10000),
    attachment: UploadFile | None = File(default=None),
    user_id: int = Depends(auth_handler.expert_dependency),
    session: AsyncSession = Depends(get_session),
):
    saved = await save_private_pdf(attachment, f"report_{order_id}") if attachment else None
    try:
        return await ExpertRepository(session).add_report(
            order_id,
            user_id,
            conclusion,
            analysis,
            suggestions,
            recommended_names,
            five_elements_analysis,
            final_reply,
            saved,
        )
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.post("/expert-workbench/orders/{order_id}/report-text", response_model=ExpertReportOut)
async def submit_expert_text_report(
    order_id: int,
    data: ExpertReportIn,
    user_id: int = Depends(auth_handler.expert_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).add_report(
            order_id,
            user_id,
            data.conclusion,
            data.analysis,
            data.suggestions,
            data.recommended_names,
            data.five_elements_analysis,
            data.final_reply,
            None,
        )
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.get("/expert-workbench/income", response_model=IncomeSummaryOut)
async def expert_income(
    user_id: int = Depends(auth_handler.expert_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).income_summary(user_id)
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.get("/expert-workbench/settlements", response_model=list[SettlementOut])
async def expert_settlements(
    user_id: int = Depends(auth_handler.expert_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).list_settlements(user_id)
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.post("/expert-workbench/settlements", response_model=SettlementOut)
async def create_expert_settlement(
    data: SettlementCreateIn,
    user_id: int = Depends(auth_handler.expert_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).create_settlement(
            user_id, data.amount, data.remark
        )
    except ExpertDomainError as exc:
        _raise_domain(exc)

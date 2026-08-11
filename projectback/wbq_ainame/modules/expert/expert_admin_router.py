from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.authtools import AuthHandler
from dependencies import get_session
from modules.expert.expert_repo import ExpertDomainError, ExpertRepository
from modules.expert.expert_schemas import (
    AdminDecisionIn,
    AdminDisputeIn,
    ExpertOrderOut,
    ExpertPackageOut,
    ExpertProfileOut,
    SettlementOut,
    SettlementProcessIn,
    ExpertApplicationOut,
)


router = APIRouter(prefix="/admin", tags=["admin-expert"])
auth_handler = AuthHandler()


def _raise_domain(exc: ExpertDomainError):
    raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/expert-applications", response_model=list[ExpertApplicationOut])
async def list_expert_applications(
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    return await ExpertRepository(session).admin_list_profiles()


@router.post("/expert-applications/{profile_id}/decision", response_model=ExpertProfileOut)
async def decide_expert_application(
    profile_id: int,
    data: AdminDecisionIn,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).admin_profile_decision(
            profile_id, data.decision, data.note, data.expert_level
        )
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.get("/expert-packages", response_model=list[ExpertPackageOut])
async def list_admin_expert_packages(
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    return await ExpertRepository(session).admin_list_packages()


@router.post("/expert-packages/{package_id}/decision", response_model=ExpertPackageOut)
async def decide_expert_package(
    package_id: int,
    data: AdminDecisionIn,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).admin_package_decision(
            package_id, data.decision, data.note
        )
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.get("/expert-orders", response_model=list[ExpertOrderOut])
async def list_admin_expert_orders(
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    return await ExpertRepository(session).admin_list_orders()


@router.post("/expert-orders/{order_id}/resolve", response_model=ExpertOrderOut)
async def resolve_expert_order(
    order_id: int,
    data: AdminDisputeIn,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).admin_resolve_dispute(
            order_id, data.resolution, data.note, data.refund_reference
        )
    except ExpertDomainError as exc:
        _raise_domain(exc)


@router.get("/expert-settlements", response_model=list[SettlementOut])
async def list_admin_expert_settlements(
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    return await ExpertRepository(session).admin_list_settlements()


@router.post("/expert-settlements/{request_id}/process", response_model=SettlementOut)
async def process_expert_settlement(
    request_id: int,
    data: SettlementProcessIn,
    admin_user_id: int = Depends(auth_handler.admin_dependency),
    session: AsyncSession = Depends(get_session),
):
    try:
        return await ExpertRepository(session).admin_process_settlement(
            request_id, data.decision, data.note, data.payment_reference
        )
    except ExpertDomainError as exc:
        _raise_domain(exc)

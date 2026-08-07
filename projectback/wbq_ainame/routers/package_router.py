from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies import get_session
from repository.package_repo import PackageRepository
from schemas.package_schemas import PackageOut

router = APIRouter(prefix="/packages", tags=["packages"])

@router.get("/list", response_model=list[PackageOut])
async def list_packages(session: AsyncSession = Depends(get_session)):
    package_repo =  PackageRepository(session)
    packages = await package_repo.get_all_packages()
    return packages
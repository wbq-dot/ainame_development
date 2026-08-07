from fastapi import APIRouter, HTTPException, Depends

from core.authtools import AuthHandler
from core.logo_tools import generate_company_logo
from schemas.logo_schemas import LogoGenerateIn, LogoGenerateOut


router = APIRouter(prefix="/logos", tags=["logos"])
auth_handler = AuthHandler()


@router.post("/generate", response_model=LogoGenerateOut)
def generate_logo(
    data: LogoGenerateIn,
    user_id: int = Depends(auth_handler.auth_access_dependency),
):
    company_name = data.company_name.strip()  # 企业名
    if not company_name:
        raise HTTPException(status_code=400, detail="请输入企业名称")
    # 执行生成 logo 的函数
    logo = generate_company_logo(
        company_name=company_name,
        style_feedback=data.style_feedback,
    )
    return {
        "company_name": company_name,
        **logo,  # 很多的字典参数进行解包，插入
    }

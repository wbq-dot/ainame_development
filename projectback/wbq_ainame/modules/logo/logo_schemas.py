from pydantic import BaseModel

# 客户传入的信息
class LogoGenerateIn(BaseModel):
    company_name: str    # 公司名
    style_feedback: str = "" #反馈意见

# 给客户输出的信息
class LogoGenerateOut(BaseModel):
    company_name: str
    logo_prompt: str   # logo 的提示词
    logo_url: str      # 访问地址
    logo_status: str   # logo 的状态
    credit_cost: int
    remaining_logo_balance: int

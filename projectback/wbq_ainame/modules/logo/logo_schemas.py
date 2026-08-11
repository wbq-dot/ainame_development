from pydantic import BaseModel, Field

# 客户传入的信息
class LogoGenerateIn(BaseModel):
    company_name: str = Field(min_length=1, max_length=100)
    slogan: str = Field(default="", max_length=100)
    industry: str = Field(default="", max_length=100)
    brand_personality: str = Field(default="", max_length=300)
    logo_style: str = Field(default="极简现代", max_length=100)
    primary_colors: str = Field(default="", max_length=100)
    graphic_elements: str = Field(default="", max_length=300)
    forbidden_elements: str = Field(default="", max_length=300)
    usage_scenes: str = Field(default="官网、App 图标、名片", max_length=300)
    style_feedback: str = Field(default="", max_length=1000)

# 给客户输出的信息
class LogoGenerateOut(BaseModel):
    company_name: str
    logo_prompt: str   # logo 的提示词
    logo_url: str      # 访问地址
    logo_status: str   # logo 的状态
    credit_cost: int
    remaining_logo_balance: int

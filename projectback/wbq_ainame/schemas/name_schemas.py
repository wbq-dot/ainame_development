from pydantic import BaseModel, Field,model_validator
from typing import Annotated, List,Literal

# 大模型输出的结构化模版
# 一条模型输出内容的模版
class NameSchema(BaseModel):
    name: Annotated[str, Field(..., description="姓名")]
    reference: Annotated[str, Field(..., description="出处")]
    moral: Annotated[str, Field(..., description="寓意")]
    # 输出加入两个字段 domain 域名  domain_status 域名状态，模型起完域名自己查询校验
    domain: str = Field(..., description="为该品牌设计的纯小写 .com 域名，例如: astar.com")
    domain_status: str = Field(default="正在查询...", description="域名的注册状态")  # default="正在查询..."  访问域名查询的网站出现问题，就返回正在查询...


# 将多条数据拼接成列表
class NameResultSchema(BaseModel):
    thread_id: str    # 这个 thread_id 对应那个用户的记忆
    names: List[NameSchema]


# 传入值时校验的模版
CategoryLiteral = Literal["人名", "企业名", "宠物名"]     # 名字的分类
class NameIn(BaseModel):
    category: Annotated[CategoryLiteral, Field("人名")]  # 分类默认是人名  Field(str) 不写默认是 str 内容   Field(...) 必须填写里面的内容
    surname: Annotated[str, Field("", description="姓氏")]  # 默认可以为空
    gender: Annotated[Literal["不限", "男", "女"], Field("不限", description="性别")]  # Literal 可选项
    length: Annotated[Literal["不限","一字", "两字", "三字","四字"], Field("不限", description="字数")]
    other: Annotated[str|None, Field("", description="其他要求")]
    exclude: Annotated[List[str], Field([], description="排除的名字")]

    # 当post 提交前我们对数据提前校验，起人名必须有姓
    @model_validator(mode="after")
    def validate_fields_by_category(self):
        if self.category == "人名" and not self.surname:
            raise ValueError("生成人名时，必须填姓氏")
        return self   # 把表单值返回输入到参数中


# 微调的输入模版
class FeedbackIn(BaseModel):
    thread_id: str = Field(..., description="前端回传的会话ID")
    category: Annotated[CategoryLiteral, Field("人名")]
    feedback: str = Field(..., description="用户的修改意见")

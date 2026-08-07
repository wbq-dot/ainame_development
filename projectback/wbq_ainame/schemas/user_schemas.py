from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from typing import Annotated

# 定义前端传入后端的数据模型，校验
RawPasswordStr = Annotated[str, Field(..., min_length=8, max_length=64)]
LoginPasswordStr = Annotated[str, Field(..., min_length=1, max_length=64)]

class RegisterIn(BaseModel):
    email: EmailStr
    username: Annotated[str, Field(...,min_length=3,max_length=8)]
    password: RawPasswordStr
    confirm_password: RawPasswordStr
    code: Annotated[str, Field(...,min_length=4,max_length=4)]

    # 当模型数据赋值完毕后自动调用这个函数
    @model_validator(mode="after")   # model_validator 数据传入模型的校验  ['wrap', 'before' 前, 'after' 后]
    # 确认密码和密码是否一致
    def password_validator(self):
        password = self.password
        confirm_password = self.confirm_password
        if password != confirm_password:
            raise ValueError("两次密码输入的内容不匹配")
        return self   # 没有问题将数据返回至模型本身

# 定义流转到数据库中数据格式的模型，校验
class UserCreateSchema(BaseModel):
    email: EmailStr
    password: RawPasswordStr
    username: Annotated[str, Field(min_length=3,max_length=8)]


# 登录的格式
class LoginIn(BaseModel):
    email: EmailStr
    # 登录暂时兼容历史6位密码；新注册密码必须为8至64位。
    password: LoginPasswordStr

class UserSchema(BaseModel):     # 基础的用户信息 email username
    id: int
    email: EmailStr
    username: Annotated[str, Field(min_length=3,max_length=8)]
    role: str
    status: str
    model_config = ConfigDict(from_attributes=True)

class LoginOutSchema(BaseModel):   # email username + access_token + refresh_token
    user:UserSchema
    access_token:str
    refresh_token:str


class RefreshOutSchema(BaseModel):
    access_token: str

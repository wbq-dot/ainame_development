from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, model_validator


CurrentPasswordStr = Annotated[str, Field(..., min_length=1, max_length=64)]
NewPasswordStr = Annotated[str, Field(..., min_length=8, max_length=64)]


class ChangePasswordIn(BaseModel):
    current_password: CurrentPasswordStr
    new_password: NewPasswordStr
    confirm_password: NewPasswordStr

    @model_validator(mode="after")
    def validate_passwords(self):
        if self.new_password != self.confirm_password:
            raise ValueError("两次输入的新密码不一致")
        if self.current_password == self.new_password:
            raise ValueError("新密码不能与原密码相同")
        return self


class SendEmailChangeCodeIn(BaseModel):
    new_email: EmailStr


class ChangeEmailIn(BaseModel):
    new_email: EmailStr
    code: Annotated[str, Field(..., pattern=r"^\d{6}$")]


class AccountMessageOut(BaseModel):
    message: str

from . import  Base         # 一旦导软件包 __init__.py 文件中的内容会全部自动导入执行
from sqlalchemy.orm import mapped_column,Mapped
from sqlalchemy import Integer, String, DateTime
from pwdlib import PasswordHash      # PasswordHash 密码加密包
from datetime import datetime
password_hash = PasswordHash.recommended()

class User(Base):
    __tablename__ = 'user'
    id:Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
    email:Mapped[str] = mapped_column(String(100),unique=True)
    username:Mapped[str] = mapped_column(String(100))
    _password:Mapped[str] = mapped_column(String(200))    # 加密处理
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 触发时机：当你通过类实例化创建一个新对象时，不能直接将密码的明文传入数据库，必须传入密文
    # *args 能接受所有按照位置传递的参数，形成一个列表， **kwargs 能接受所有名称绑定的参数， key = value ，形成一个字典
    def __init__(self, *args,**kwargs):
        password = kwargs.pop('password',None)   # dict.pop(key,None)  弹出字典中 key 的 value 值并删除此键值对，当字典中无此 key 时，弹出 None
        super().__init__(*args,**kwargs)   # 修改初始化实例属性的方法
        if password:
            # 预先将明文存入到普通对象属性中，如果没有这一步数据直接将明文传入数据库，因为这个属性没有和数据库进行映射绑定
            self.password = password
     # 通过 property 将普通属性转换为受保护属性
    @property    #将方法转换为属性
    def password(self):
        return self._password

    # 紧接着对 password 进行加密操作 PasswordHash.recommended().hash(密码)，返回数据库
    @password.setter
    def password(self,password):
       self._password =  password_hash.hash(password)

    # 下次登录时密码的校验工作   PasswordHash.recommended().verify(next_input_password,exist_hash_password)
    def check_password(self,password):
        return password_hash.verify(password,self._password)

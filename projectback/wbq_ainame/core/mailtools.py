from fastapi_mail import  ConnectionConfig,FastMail
from dotenv import load_dotenv
import os
load_dotenv()


def create_mail_instance() -> FastMail:
    conf = ConnectionConfig(    # 定义连接的配置
        # 前两个配置是网站的邮箱服务器密码和用户名(邮箱号)
        MAIL_USERNAME = os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD = os.getenv("MAIL_PASSWORD"),
        # 从哪个邮箱发送的邮箱号 xx@qq.com
        MAIL_FROM = os.getenv("MAIL_FROM"),
        # 邮箱服务器的端口号
        MAIL_PORT = os.getenv("MAIL_PORT"),
        # 邮箱服务器的域名  smtp.qq.com
        MAIL_SERVER = os.getenv("MAIL_SERVER"),
        # 以什么名义发送邮件
        MAIL_FROM_NAME= os.getenv("MAIL_FROM_NAME") ,
        # 显式加密
        MAIL_STARTTLS = os.getenv("MAIL_STARTTLS"),
        # 隐式加密
        MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS"),
        USE_CREDENTIALS = os.getenv("USE_CREDENTIALS"),
        VALIDATE_CERTS = os.getenv("VALIDATE_CERTS")
    )
    return FastMail(conf)   # 得到工具用来发邮箱

# 在qq邮箱的安全设置功能界面 ->  开启  POP3/IMAP/SMTP/Exchange/CardDAV 服务  -> 得到验证码(需要填入到MAIL_PASSWORD中) -> 可以实现通过后端实现邮件的发送和验证码的发送


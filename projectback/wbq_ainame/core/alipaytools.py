# 支付的工具

import os
import textwrap
from urllib.parse import urlsplit, urlunsplit
from alipay import AliPay
from dotenv import load_dotenv

load_dotenv()

# 格式化私钥
def format_private_key(key):
    key = key.replace(" ", "").replace("\n", "")  # 合并到一行
    key = "\n".join(textwrap.wrap(key, 64))  # 合并的一行，按照 64 个字符一行分割的列表，换行拼接成字符串
    return f"-----BEGIN RSA PRIVATE KEY-----\n{key}\n-----END RSA PRIVATE KEY-----"

# 格式化公钥
def format_public_key(key):
    key = key.replace(" ", "").replace("\n", "")
    key = "\n".join(textwrap.wrap(key, 64))
    return f"-----BEGIN PUBLIC KEY-----\n{key}\n-----END PUBLIC KEY-----"


# 配置Alipay 实现支付连接的生成工具
def create_alipay():
    return AliPay(
        appid=os.getenv("ALIPAY_APP_ID"),
        app_notify_url=os.getenv("ALIPAY_NOTIFY_URL") or None,
        app_private_key_string=format_private_key(os.getenv("ALIPAY_APP_PRIVATE_KEY")),
        alipay_public_key_string=format_public_key(os.getenv("ALIPAY_PUBLIC_KEY")),
        sign_type="RSA2",
        debug=True)

# 获取支付的路径
def get_alipay_gateway():
    return os.getenv("ALIPAY_GATEWAY")

# 返回给客户浏览器的路径
def get_return_url():
    return os.getenv("ALIPAY_RETURN_URL")

# 异步通知地址，返回到服务器通知
def get_notify_url():
    return os.getenv("ALIPAY_NOTIFY_URL") or None


def build_alipay_page_pay_url(
    *,
    out_trade_no: str,
    subject: str,
    total_amount: str,
    return_url: str,
    notify_url: str | None = None,
) -> str:
    """使用统一参数生成支付宝电脑网站支付链接。"""
    gateway = get_alipay_gateway()
    if not gateway:
        raise ValueError("支付宝网关尚未配置")
    if not return_url:
        raise ValueError("支付宝浏览器返回地址尚未配置")

    pay_kwargs = {
        "out_trade_no": out_trade_no,
        "subject": subject,
        "total_amount": total_amount,
        "timeout_express": "1h",
        "return_url": return_url,
    }
    if notify_url:
        pay_kwargs["notify_url"] = notify_url

    order_string = create_alipay().api_alipay_trade_page_pay(**pay_kwargs)
    return f"{gateway}?{order_string}"


def get_expert_return_url():
    return os.getenv("EXPERT_ALIPAY_RETURN_URL") or _derive_expert_url(
        get_return_url(), "/pay/success", "/expert-pay/return"
    )


def get_expert_notify_url():
    return os.getenv("EXPERT_ALIPAY_NOTIFY_URL") or _derive_expert_url(
        get_notify_url(), "/pay/paySuccess", "/expert-pay/notify"
    )


def _derive_expert_url(source_url: str | None, old_path: str, new_path: str):
    """优先保留现有反向代理路径，无法匹配时使用同域名根路径。"""
    if not source_url:
        return None
    parts = urlsplit(source_url)
    path = parts.path
    if path.endswith(old_path):
        path = f"{path[:-len(old_path)]}{new_path}"
    else:
        path = new_path
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))



'''
1. 安装支付宝 SDK  
pip install python-alipay-sdk  
2. FastAPI 读取表单数据需要安装
pip install python-multipart
3. 查看是否安装成功
pip freeze | findstr alipay 
4.开通支付宝沙箱功能 
支付宝开放平台 -> 登录 -> 补充基础信息 -> 控制台 -> 沙箱 -> 获取信息
'''


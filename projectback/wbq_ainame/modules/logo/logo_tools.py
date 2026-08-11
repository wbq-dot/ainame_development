from pathlib import Path
from uuid import uuid4

import httpx

import settings


BACKEND_DIR = Path(__file__).resolve().parents[2]
LOGO_DIR = BACKEND_DIR / "static" / "logos"
LOGO_DIR.mkdir(parents=True, exist_ok=True)

# 提示词函数
def build_logo_prompt(
    company_name: str,
    style_feedback: str = "",
    slogan: str = "",
    industry: str = "",
    brand_personality: str = "",
    logo_style: str = "极简现代",
    primary_colors: str = "",
    graphic_elements: str = "",
    forbidden_elements: str = "",
    usage_scenes: str = "官网、App 图标、名片",
) -> str:
    feedback = style_feedback.strip() or "首次生成，按企业名称设计。"
    brief = "\n".join(
        line
        for line in [
            f"品牌口号：{slogan.strip()}" if slogan.strip() else "",
            f"所属行业：{industry.strip()}" if industry.strip() else "",
            f"品牌气质：{brand_personality.strip()}" if brand_personality.strip() else "",
            f"视觉风格：{logo_style.strip()}" if logo_style.strip() else "",
            f"偏好颜色：{primary_colors.strip()}" if primary_colors.strip() else "",
            f"图形元素：{graphic_elements.strip()}" if graphic_elements.strip() else "",
            f"禁用元素：{forbidden_elements.strip()}" if forbidden_elements.strip() else "",
            f"使用场景：{usage_scenes.strip()}" if usage_scenes.strip() else "",
        ]
        if line
    )
    return f"""
为企业品牌“{company_name}”设计一枚专业 Logo 图形。

品牌创作简报：
{brief or "未补充，按品牌名称进行专业判断。"}

用户要求：{feedback}

设计要求：
1. 只生成独立 Logo 图形，不要生成中文、英文、字母或数字。
2. 极简、现代、扁平化、矢量图标风格。
3. 白色纯背景，主体居中。
4. 适合企业官网、App 图标、名片、宣传物料使用。
5. 不要水印、二维码、样机、纸张、墙面展示、复杂背景。
""".strip()

# 从阿里云返回的复杂字典里，找到图片地址并返回。data中含有图像地址信息
def pick_image_url(data: dict) -> str:
    for choice in data.get("output", {}).get("choices", []):
        for item in choice.get("message", {}).get("content", []):
            if item.get("image"):
                return item["image"]
    return ""


def generate_company_logo(
    company_name: str,
    style_feedback: str = "",
    user_id: int | None = None,
    **brief,
) -> dict:
    logo_prompt = build_logo_prompt(company_name, style_feedback, **brief)

    # 没有配置 api 不能调大模型
    if not settings.DASHSCOPE_API_KEY or not settings.DASHSCOPE_BASE_URL:
        return {
            "logo_prompt": logo_prompt,
            "logo_url": "",
            "logo_status": "未配置 DASHSCOPE_API_KEY 或 DASHSCOPE_BASE_URL",
        }

    # 访问调用阿里大模型的路由
    request_url = (
        f"{settings.DASHSCOPE_BASE_URL}"
        "/services/aigc/multimodal-generation/generation"
    )

    # 访问大模型输入信息的json串
    payload = {
        "model": settings.WANXIANG_MODEL,  # 大模型信息
        # 输入信息
        "input": {
            "messages": [
                {
                    "role": "user",  # 角色用户
                    "content": [{"text": logo_prompt}],  # 提示词数据
                }
            ]
        },
        # 图片的输出参数
        "parameters": {
            "prompt_extend": True,
            "watermark": False,
            "n": 1,  # 返回的数量
            "negative_prompt": "文字，字母，数字，水印，二维码，照片，名片样机，墙面样机，复杂背景，模糊，变形", # 需要排除的内容
            "size": "1280*1280", #格式大小
        },
    }
    # 请求头
    headers = {
        "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",  # 通过 APIkey 认证 JWT 令牌
        "Content-Type": "application/json",    # 返回 json 内容
    }

    try:
        with httpx.Client(timeout=180, follow_redirects=True) as client:  # 客户端的上下文管理
            response = client.post(request_url, headers=headers, json=payload)  # post 提交访问数据
            response.raise_for_status()  # response 含有异常状态
            data = response.json()      # 把 json 数据转成字典

            if data.get("code"):  # 只要有状态就说明有异常
                return {
                    "logo_prompt": logo_prompt,
                    "logo_url": "",
                    "logo_status": f"生成失败：{data.get('code')} - {data.get('message')}", # 打印异常
                }

            image_url = pick_image_url(data)  # 获得图像的 URL
            if not image_url:
                return {
                    "logo_prompt": logo_prompt,
                    "logo_url": "",
                    "logo_status": "生成失败：没有拿到图片地址",
                }

            image_response = client.get(image_url)  # 得到图片的二进制返回数据
            image_response.raise_for_status()

        owner_prefix = f"user_{user_id}_" if user_id is not None else ""
        file_name = f"{owner_prefix}{uuid4().hex}.png"  #图片的随机 ID 号
        file_path = LOGO_DIR / file_name  # 图片的位置
        file_path.write_bytes(image_response.content)  # 将图片的二进制数据转成 png 图片放入到指定位置中

        return {
            "logo_prompt": logo_prompt,
            "logo_url": f"{settings.APP_BASE_URL}/static/logos/{file_name}",  # 本地服务器存放的图片路由
            "logo_status": "生成成功",
            "logo_file_name": file_name,
        }

    # 超时的报错
    except httpx.TimeoutException:
        return {
            "logo_prompt": logo_prompt,
            "logo_url": "",
            "logo_status": "生成失败：请求超时",
        }
    # 状态异常
    except httpx.HTTPStatusError as exc:
        return {
            "logo_prompt": logo_prompt,
            "logo_url": "",
            "logo_status": f"生成失败：HTTP {exc.response.status_code} {exc.response.text[:200]}",
        }
    # 代码的异常
    except Exception as exc:
        return {
            "logo_prompt": logo_prompt,
            "logo_url": "",
            "logo_status": f"生成失败：{exc}",
        }

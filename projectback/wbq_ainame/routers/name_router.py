from fastapi import APIRouter, Depends,HTTPException

router = APIRouter(prefix="/name")
from schemas.name_schemas import NameIn
# from core.nametools import generate_name  单类型的起名接口
from schemas.name_schemas import NameResultSchema
from core.authtools import AuthHandler
from dependencies import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from repository.credit_repo import CreditRepository
from core.workflow import generate_naming
from schemas.name_schemas import FeedbackIn
from core.workflow import feedback_naming

# 进行JWT 的校验
auth_handler = AuthHandler()


# 用户第一起名或者不使用历史起过名字进行微调而是重新起名
@router.post("/generate", response_model=NameResultSchema)   # 输出结果的的模版
# NameIn 按照输入类型输入 {surname: ...}   .http 传入/ form 表单
async def get_names(data:NameIn,user_id:int = Depends(auth_handler.auth_access_dependency), # auth_handler.auth_access_dependency 通过传入的 Bearer，返回一个 user_id
        session:AsyncSession=Depends(get_session)):

        creditRepository = CreditRepository(session)
        balance = await creditRepository.get_balance(user_id)    # 查询余额
        # 1.先查询剩余的起名次数，如果有，调用起名工具，如果没有，告诉用户充值
        if balance <= 0:
            raise HTTPException(status_code=400, detail="余额不足，请充值后使用")

        # 2.调用起名接口
        name_result = await generate_naming(data,user_id)   # 加上 user_id 传入到后续的 rag 个人知识库的调用接口使用

        # 3.起名后，在账户中次数减1，日志中添加一条数据，消费成功
        await creditRepository.consume_name_credit(user_id)

        thread_id = name_result.get("thread_id")   # 记忆的 id
        final_output = name_result.get("final_output")  # 起名结果

        try:
            # print(name_result)         # {'thread_id': 'e1d82af2-2fe5-4ffc-8e27-9a19ad0cc1c1', 'final_output': {'thread_id': 'thread_123', 'names': [{'name': '熠芯辉', 'reference': '《诗经·豳风》"熠熠宵行"，熠为火部，光芒闪耀；芯为芯片之核；辉为光辉',...}]}} 内部的结构，跟我们返回的 NameResultSchema 类型不一致，所有要重新整合
            return NameResultSchema(thread_id=thread_id, names=final_output["names"])

        except Exception as e:
            print(e)






# @router.post("/get_names", response_model=NameResultSchema)   # 输出结果的的模版
# # NameIn 按照输入类型输入 {surname: ...}   .http 传入/ form 表单
# async def get_names(data:NameIn,user_id:int = Depends(auth_handler.auth_access_dependency), # auth_handler.auth_access_dependency 通过传入的 Bearer，返回一个 user_id
#         session:AsyncSession=Depends(get_session)):
#         print(user_id)  # 如果有任何令牌相关问题内部可以解决 authtools 工具
#
#         creditRepository = CreditRepository(session)
#         balance = await creditRepository.get_balance(user_id)    # 查询余额
#         # 1.先查询剩余的起名次数，如果有，调用起名工具，如果没有，告诉用户充值
#         if balance <= 0:
#             raise HTTPException(status_code=400, detail="余额不足，请充值后使用")
#
#         # 2.调用起名接口
#         # name_result = await generate_name(data)
#         name_result = await generate_naming(data,user_id)   # 将单一分类的起名节口换成多分类的起名节口
#
#         # 3.起名后，在账户中次数减1，日志中添加一条数据，消费成功
#         await creditRepository.consume_name_credit(user_id)
#
#
#         return name_result



# 第n次，n>=2 微调大模型生成的名字
@router.post("/feedback", response_model=NameResultSchema)
async def take_names_feedback(data:FeedbackIn    # 拿到客户的反馈意见和 thread_id
                              ,user_id:int=Depends(auth_handler.auth_access_dependency)
                              ,session:AsyncSession=Depends(get_session)):
      creditRepository = CreditRepository(session)
      balance = await creditRepository.get_balance(user_id)
      # 1.先查询剩余的起名次数，如果有，调用起名工具，如果没有，告诉用户充值
      if balance <= 0:
            raise HTTPException(status_code=400, detail="余额不足，请充值后使用")

      # 2.调用微调起名接口
      name_result = await feedback_naming(data, user_id)


      # 3.起名后，在账户中次数减1，日志中添加一条数据，消费成功
      await creditRepository.consume_name_credit(user_id=user_id)


      thread_id = name_result.get("thread_id")
      final_output = name_result.get("final_output")

      try:
          return NameResultSchema(thread_id=thread_id, names=final_output["names"])

      except Exception as e:
          print(e)

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
from core.workflow import (
    WorkflowSessionAccessError,
    WorkflowSessionCategoryError,
    WorkflowSessionNotFoundError,
    feedback_naming,
)
from core.rag_service import KnowledgeRetrievalUnavailableError

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
        try:
            name_result = await generate_naming(data,user_id)   # 加上 user_id 传入到后续的 rag 个人知识库的调用接口使用
        except KnowledgeRetrievalUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        # 3.起名后，在账户中次数减1，日志中添加一条数据，消费成功
        await creditRepository.consume_name_credit(user_id)

        thread_id = name_result.get("thread_id")   # 记忆的 id
        final_output = name_result.get("final_output")  # 起名结果

        if not final_output or "names" not in final_output:
            raise HTTPException(status_code=502, detail="模型没有返回有效的候选名字")
        return NameResultSchema(thread_id=thread_id, names=final_output["names"])






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
      try:
          name_result = await feedback_naming(data, user_id)
      except WorkflowSessionNotFoundError as exc:
          raise HTTPException(status_code=404, detail=str(exc)) from exc
      except WorkflowSessionAccessError as exc:
          raise HTTPException(status_code=403, detail=str(exc)) from exc
      except WorkflowSessionCategoryError as exc:
          raise HTTPException(status_code=400, detail=str(exc)) from exc
      except KnowledgeRetrievalUnavailableError as exc:
          raise HTTPException(status_code=503, detail=str(exc)) from exc


      # 3.起名后，在账户中次数减1，日志中添加一条数据，消费成功
      await creditRepository.consume_name_credit(user_id=user_id)


      thread_id = name_result.get("thread_id")
      final_output = name_result.get("final_output")

      if not final_output or "names" not in final_output:
          raise HTTPException(status_code=502, detail="模型没有返回有效的候选名字")
      return NameResultSchema(thread_id=thread_id, names=final_output["names"])

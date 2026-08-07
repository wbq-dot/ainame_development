from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.package import Package


class PackageRepository:

    # 建立连接
    def __init__(self, session: AsyncSession):
        self.session = session

    # 获取套餐的全部信息
    async def get_all_packages(self) -> list[Package]:

        async with self.session.begin():
            # scalars 获取全部的结果   数据库存 1 == True  存0 == False
            result = await self.session.scalars(select(Package).where(Package.is_active == True))
            return list(result.all())   # result.all() 筛出来的所有数据，返回一个 json 列表

    # 获取传入的 ID 的套餐，创建订单
    async def get_by_id(self, package_id: int) -> Package | None:

        async with self.session.begin():
            # where(A,B) == where A and B
            result = await self.session.scalar(select(Package).where( Package.id == package_id,Package.is_active == True))
            return result
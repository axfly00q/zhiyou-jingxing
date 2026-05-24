"""清理 message 表中包含问号的脏测试数据（含中文乱码 ?）。"""
import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as s:
        r = await s.execute(text(
            "DELETE FROM message WHERE role = 'user' AND content ~ '\\?\\?+'"
        ))
        await s.commit()
        print("deleted rows:", r.rowcount)


if __name__ == "__main__":
    asyncio.run(main())

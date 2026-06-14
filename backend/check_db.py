import asyncpg, asyncio

async def test():
    try:
        conn = await asyncpg.connect("postgresql://postgres:Qwerty%40123@localhost:5432/sqs_db")
        ver = await conn.fetchval("SELECT version()")
        print("DB OK:", ver[:50])
        tables = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        print("Tables:", [r['tablename'] for r in tables])
        await conn.close()
    except Exception as e:
        print("DB ERROR:", e)

asyncio.run(test())

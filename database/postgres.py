import asyncpg

class Database:
    def __init__(self, cfg):
        self.user = cfg.postgres_user
        self.password = cfg.postgres_password
        self.database = cfg.postgres_db
        self.host = cfg.postgres_host
        self.port = cfg.postgres_port
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            user=self.user,
            password=self.password,
            database=self.database,
            host=self.host,
            port=self.port
        )

    async def close(self):
        await self.pool.close()

    async def execute(self, query, *args):
        async with self.pool.acquire() as connection:
            return await connection.execute(query, *args)

    async def fetch(self, query, *args):
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)
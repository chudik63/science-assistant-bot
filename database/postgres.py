import asyncpg
import psycopg

class Database:
    def __init__(self, dbname, user, password, host, port):
        self.connection = psycopg.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port
        )

        self.cursor = self.connection.cursor()

    async def close(self):
        await self.cursor.close()

    async def execute(self, query, *args):
        self.cursor.execute(query)
        return self.cursor.fetchall()

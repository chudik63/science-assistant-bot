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

    def close(self):
        self.cursor.close()
        self.connection.close()

    def execute(self, query, *args):
        self.cursor.execute(query, args)
        try:
            res = self.cursor.fetchall()
        except psycopg.ProgrammingError:
            self.connection.commit()
            return None

        return res
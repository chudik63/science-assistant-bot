from database.postgres import Database

class Repository:
	def __init__(self, db: Database):
		self.db = db
	def get_user_by_id(self, id):
		query = """
        SELECT * FROM users WHERE id = %s
        """
		res = self.db.execute(query, id)
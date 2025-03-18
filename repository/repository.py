from database.postgres import Database
from models.models import User

class Repository:
	def __init__(self, db: Database):
		self.db = db

	def get_user_by_id(self, id) -> list:
		query = """
        SELECT * FROM users WHERE id = %s
        """
		return self.db.execute(query, id)
	
	def add_user(self, user: User):
		query = """
		INSERT INTO users (id, name, email, timezone) VALUES(%s, %s, %s, %s)
		"""

		self.db.execute(query, user.id, user.name, user.email, user.timezone)
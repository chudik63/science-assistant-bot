from database.postgres import Database
from models.Classes_for_db import User, FilterSettings

class Repository:
	def __init__(self, db: Database):
		self.db = db

	def get_user_by_id(self, id) -> User:
		query = """
		SELECT * FROM users WHERE id = %s
		"""

		res = self.db.execute(query, id)
		if len(res) == 0:
			return None
		else:
			res = res[0]
	
		user = User(res[0], res[1], res[2], res[3])
		return user
	
	def add_user(self, user: User):
		query = """
		INSERT INTO users (id, name, email, timezone) VALUES(%s, %s, %s, %s)
		"""

		self.db.execute(query, user.id, user.name, user.email, user.timezone)
	
	def add_filter_settings(self, settings: FilterSettings):
		query = """
		INSERT INTO user_filter_settings (user_id, authors, topics, types, sources, links) 
		VALUES(%s, %s, %s, %s, %s, %s)
		"""

		self.db.execute(query, settings.user_id, settings.authors, settings.topics, settings.types, settings.sources, settings.links)

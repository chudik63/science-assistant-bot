class User:
    def __init__(self, id: int, name: str, email: str, timezone: str):
        self.id = id
        self.name = name
        self.email = email
        self.timezone = timezone

class FilterSettings:
    def __init__(self, user_id: str, keywords: str, authors: str, topics: str, types: str, time_interval: int, sources: str):
        self.user_id = user_id
        self.keywords = keywords
        self.authors = authors
        self.topics = topics
        self.types = types
        self.time_interval = time_interval
        self.sources = sources
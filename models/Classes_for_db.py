from typing import List


class User:
    def __init__(self, id: int, name: str, email: str, timezone: str):
        self.id = id
        self.name = name
        self.email = email
        self.timezone = timezone

class FilterSettings:
    def __init__(self, user_id: int, authors: str, topics: str, types: str, sources: str, links: List[str]):
        self.user_id = user_id
        self.authors = authors
        self.topics = topics
        self.types = types
        self.sources = sources
        self.links = links
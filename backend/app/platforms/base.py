from abc import ABC, abstractmethod
from app.models.blogger import BloggerProfile, BloggerPost, Comment

class BaseCollector(ABC):
    @abstractmethod
    async def get_blogger_profile(self, blogger_url: str, task_id: str = None) -> BloggerProfile:
        """
        Retrieve a blogger's profile.
        """
        pass

    @abstractmethod
    async def get_blogger_posts(self, blogger_uid: str, count: int, task_id: str = None) -> list[BloggerPost]:
        """
        Retrieve blogger's recent posts.
        """
        pass

    @abstractmethod
    async def collect_comments(self, post_id: str, count: int, task_id: str = None) -> list[Comment]:
        """
        Retrieve comments of a post.
        """
        pass

    @abstractmethod
    def select_posts(self, posts: list[dict], config: dict) -> list[dict]:
        """
        Select posts using Top N + Recent N sorting and deduplication.
        """
        pass

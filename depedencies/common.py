from services.buddy_service import BuddyClient
from core.config import settings


def get_buddy_service() -> BuddyClient:
    return BuddyClient(
        api_url=settings.API_URL,
        api_key=settings.API_KEY,
        client_name=settings.CLIENT_NAME
    )

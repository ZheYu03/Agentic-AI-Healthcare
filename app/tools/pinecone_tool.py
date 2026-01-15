from functools import lru_cache

from pinecone import Pinecone

from app.core.config import Settings, get_settings


@lru_cache(maxsize=1)
def get_pinecone_index(settings: Settings | None = None):
    """
    Return a Pinecone index client using project settings.

    Uses VECTOR_STORE_MODE to keep alignment with the rest of the app.
    """
    settings = settings or get_settings()
    if settings.vector_store_mode != "cloud":
        raise ValueError("Pinecone is disabled because VECTOR_STORE_MODE is not 'cloud'")

    pc = Pinecone(api_key=settings.pinecone_api_key, environment=settings.pinecone_environment)
    return pc.Index(settings.pinecone_index_name)

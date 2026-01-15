from functools import lru_cache

from supabase import Client, create_client

from app.core.config import Settings, get_settings


@lru_cache(maxsize=1)
def get_supabase_client(settings: Settings | None = None) -> Client:
    """
    Return a Supabase client using service role credentials for full access.

    Use the anon key instead if you need read-only user-side access.
    """
    settings = settings or get_settings()
    url = settings.supabase_url if settings.supabase_url.endswith("/") else f"{settings.supabase_url}/"
    return create_client(url, settings.supabase_service_role_key)

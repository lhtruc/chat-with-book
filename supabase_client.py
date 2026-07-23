"""
Supabase client singleton for vector operations and database queries.
"""
from typing import Optional
from supabase import create_client, Client
import config

_supabase_client: Optional[Client] = None
_supabase_admin_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """Lấy Supabase client chính (sử dụng SUPABASE_SERVICE_KEY hoặc SUPABASE_KEY)."""
    global _supabase_client
    if _supabase_client is None:
        url = config.SUPABASE_URL
        key = config.SUPABASE_SERVICE_KEY or config.SUPABASE_KEY
        if url and key:
            try:
                _supabase_client = create_client(url, key)
            except Exception as e:
                print(f"⚠️ Không thể khởi tạo Supabase client: {e}")
                return None
    return _supabase_client


def get_supabase_admin_client() -> Optional[Client]:
    """Lấy Supabase admin client (sử dụng SUPABASE_SERVICE_KEY cho data upload/ingestion)."""
    global _supabase_admin_client
    if _supabase_admin_client is None:
        url = config.SUPABASE_URL
        key = config.SUPABASE_SERVICE_KEY or config.SUPABASE_KEY
        if url and key:
            try:
                _supabase_admin_client = create_client(url, key)
            except Exception as e:
                print(f"⚠️ Không thể khởi tạo Supabase Admin client: {e}")
                return None
    return _supabase_admin_client

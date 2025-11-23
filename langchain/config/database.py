"""
Database configuration and cache manager for Supabase
Handles connection, caching, and realtime updates
"""

import logging
import time
from typing import Dict, List, Optional
from datetime import datetime
from supabase import create_client, Client as SupabaseClient
import os

logger = logging.getLogger(__name__)


class MenuCacheManager:
    """
    Mengelola caching menu data dari Supabase
    - Load semua data saat startup
    - Listen realtime changes untuk update cache (sync client - simplified)
    """
    
    def __init__(self, supabase_client: SupabaseClient):
        self.supabase = supabase_client
        self.cache: Dict[str, List[dict]] = {}
        self.last_updated: Optional[datetime] = None
        self.channel = None
        logger.info("✅ MenuCacheManager initialized")
    
    def initialize_cache(self) -> Dict[str, List[dict]]:
        """Load semua data dari Supabase ke memory"""
        logger.info("🔄 Loading all menu data from Supabase...")
        start_time = time.time()
        
        try:
            # Fetch semua data menu dari Supabase
            response = self.supabase.table('menu_items').select('*').execute()
            
            # Grouping data berdasarkan kategori
            self.cache.clear()
            for item in response.data:
                category = item.get('category')
                if category not in self.cache:
                    self.cache[category] = []
                
                self.cache[category].append({
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'harga': item.get('harga'),
                    'is_available': item.get('is_available', True)
                })
            
            self.last_updated = datetime.now()
            elapsed = time.time() - start_time
            total_items = sum(len(items) for items in self.cache.values())
            
            logger.info(f"✅ Cache loaded: {len(self.cache)} categories, {total_items} items ({elapsed:.2f}s)")
            return self.cache
            
        except Exception as e:
            logger.error(f"❌ Error loading cache from Supabase: {e}")
            raise
    
    def setup_realtime_listener(self):
        """
        Setup listener untuk realtime updates dari Supabase
        NOTE: Sync client tidak support realtime, ini placeholder
        Untuk production, gunakan async client atau polling
        """
        logger.info("⚠️  Realtime listener disabled (sync client limitation)")
        logger.info("💡 Cache will be refreshed on restart or manual refresh")
    
    def refresh_cache(self) -> Dict[str, List[dict]]:
        """Manual refresh cache dari database"""
        logger.info("🔄 Manual cache refresh triggered")
        return self.initialize_cache()
    
    def get_menu_data(self) -> Dict[str, List[dict]]:
        """Ambil data menu dari cache"""
        return self.cache
    
    def get_category_data(self, category: str) -> List[dict]:
        """Ambil data menu untuk kategori tertentu"""
        return self.cache.get(category, [])
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cache cleanup completed")


def get_supabase_client() -> SupabaseClient:
    """
    Initialize and return Supabase client
    Reads credentials from environment variables
    """
    from dotenv import load_dotenv
    
    # Load .env from root directory
    load_dotenv()
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        raise ValueError(
            "Missing Supabase credentials. "
            "Please set SUPABASE_URL and SUPABASE_KEY in .env file"
        )
    
    if supabase_url == "your-supabase-url":
        raise ValueError(
            "Please update SUPABASE_URL in .env with your actual Supabase URL"
        )
    
    logger.info("🔌 Initializing Supabase client...")
    client = create_client(supabase_url, supabase_key)
    logger.info("✅ Supabase client initialized")
    
    return client

# services/menu_service.py
"""
Menu Service Layer - Simplified
Uses existing MenuCacheManager from config/database.py
"""
import logging
from typing import List, Dict
from datetime import datetime
from supabase import Client as SupabaseClient

logger = logging.getLogger(__name__)

class MenuService:
    """Service layer for menu operations"""
    
    def __init__(self, supabase: SupabaseClient, cache_manager=None):
        self.supabase = supabase
        self.table = "menu_items"
        self.cache_manager = cache_manager  # MenuCacheManager instance
    
    async def create_item(self, item_data: Dict) -> Dict:
        """
        Create new menu item
        
        Args:
            item_data: {category, name, harga, is_available (optional)}
            
        Returns:
            Created item
        """
        try:
            # Set default availability
            if 'is_available' not in item_data:
                item_data['is_available'] = True
            
            # Insert to database
            response = self.supabase.table(self.table).insert(item_data).execute()
            
            if response.data:
                created_item = response.data[0]
                logger.info(f"✅ Created: {created_item['name']} - {created_item['harga']} EGP")
                
                # Refresh cache menggunakan method yang sudah ada
                if self.cache_manager:
                    self.cache_manager.refresh_cache()
                    logger.info("🔄 Cache auto-refreshed after create")
                
                return created_item
            else:
                raise Exception("No data returned from insert")
                
        except Exception as e:
            logger.error(f"❌ Error creating menu item: {e}")
            raise
    
    async def get_all_items(self) -> List[Dict]:
        """
        Get ALL menu items with cache-first strategy
        
        Uses MenuCacheManager.get_menu_data() which returns Dict[category, items]
        Converts to flat list for API response
        """
        try:
            # 🚀 Try cache first (menggunakan method yang sudah ada)
            if self.cache_manager:
                cache_data = self.cache_manager.get_menu_data()
                
                if cache_data:
                    # Convert Dict[category, items] to flat list
                    all_items = []
                    for category, items in cache_data.items():
                        all_items.extend(items)
                    
                    if all_items:
                        logger.info(f"⚡ Cache HIT: {len(all_items)} items from cache")
                        return all_items
                    else:
                        logger.warning("⚠️ Cache empty, querying database")
            
            # 🔄 Cache miss - query database
            logger.info("📊 Cache MISS: Querying database...")
            response = self.supabase.table(self.table)\
                .select("*")\
                .order("category")\
                .order("name")\
                .execute()
            
            # Refresh cache jika ada data
            if self.cache_manager and response.data:
                self.cache_manager.refresh_cache()
                logger.info("🔄 Cache refreshed from database")
            
            logger.info(f"📋 Retrieved {len(response.data)} items from database")
            return response.data
            
        except Exception as e:
            logger.error(f"❌ Error getting items: {e}")
            raise
    
    async def update_availability(self, item_id: int, is_available: bool) -> Dict:
        """
        Update item availability only
        
        Args:
            item_id: Item ID
            is_available: True (available) or False (sold out)
        """
        try:
            update_data = {
                'is_available': is_available,
                'updated_at': datetime.now().isoformat()
            }
            
            # Update database
            response = self.supabase.table(self.table)\
                .update(update_data)\
                .eq("id", item_id)\
                .execute()
            
            if response.data:
                updated_item = response.data[0]
                status = "AVAILABLE ✅" if is_available else "SOLD OUT ❌"
                logger.info(f"🔄 Updated ID {item_id}: {status}")
                
                # Refresh cache menggunakan method yang sudah ada
                if self.cache_manager:
                    self.cache_manager.refresh_cache()
                    logger.info("🔄 Cache auto-refreshed after update")
                
                return updated_item
            else:
                raise Exception(f"Item with ID {item_id} not found")
                
        except Exception as e:
            logger.error(f"❌ Error updating availability: {e}")
            raise

    
    async def bulk_update_availability(self, item_ids: list[int], is_available: bool) -> list[Dict]:
        """
        Bulk update availability for multiple items
        
        Args:
            item_ids: List of item IDs to update
            is_available: True (available) or False (sold out)
        
        Returns:
            List of updated items
        """
        try:
            update_data = {
                'is_available': is_available,
                'updated_at': datetime.now().isoformat()
            }
            
            # Update all items in database
            response = self.supabase.table(self.table)\
                .update(update_data)\
                .in_("id", item_ids)\
                .execute()
            
            if response.data:
                status = "AVAILABLE ✅" if is_available else "SOLD OUT ❌"
                logger.info(f"🔄 Bulk updated {len(response.data)} items: {status}")
                logger.info(f"   Updated IDs: {item_ids}")
                
                # Refresh cache after bulk update
                if self.cache_manager:
                    self.cache_manager.refresh_cache()
                    logger.info("🔄 Cache auto-refreshed after bulk update")
                
                return response.data
            else:
                logger.warning(f"⚠️ No items found for IDs: {item_ids}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error bulk updating availability: {e}")
            raise
        
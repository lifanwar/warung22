# events/menu_crud.py
"""
Menu CRUD API Router - Simplified with Cache-First
"""
import logging
import os
from typing import List
from fastapi import APIRouter, HTTPException, Depends, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, field_validator


from config.database import get_supabase_client
from services.menu_service import MenuService


logger = logging.getLogger(__name__)


# ============ API KEY SECURITY ============


API_KEY = os.getenv("API_KEY", "default-insecure-key")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key from header"""
    if api_key != API_KEY:
        logger.warning(f"⚠️ Invalid API key attempt: {api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )
    return api_key


# ============ MODELS ============


class MenuItemCreate(BaseModel):
    """Model for creating menu item"""
    category: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    harga: int = Field(..., gt=0, description="Price in EGP")
    is_available: bool = True
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid_categories = [
            'protein_ayam', 'ati_ampela', 'protein_ikan', 
            'protein_ringan', 'karbo', 'paket_hemat',
            'menu_kuah', 'minum_cold', 'minum_hot',
            'jajanan'
        ]
        if v not in valid_categories:
            raise ValueError(f"Category must be one of: {', '.join(valid_categories)}")
        return v


class AvailabilityUpdate(BaseModel):
    """Model for updating availability"""
    is_available: bool = Field(..., description="True = available, False = sold out")


class MenuItemResponse(BaseModel):
    """Response model"""
    id: int
    category: str
    name: str
    harga: int
    is_available: bool
    created_at: str
    updated_at: str

class BulkAvailabilityUpdate(BaseModel):
    """Model for bulk updating availability"""
    item_ids: list[int] = Field(..., min_length=1, description="List of item IDs to update")
    is_available: bool = Field(..., description="True = available, False = sold out")

# ============ DEPENDENCY INJECTION ============


def get_cache_manager():
    """Get cache_manager from fastapiapp"""
    from events.fastapi_app import cache_manager
    return cache_manager


def get_menu_service(cache_mgr=Depends(get_cache_manager)) -> MenuService:
    """Dependency injection for MenuService with cache"""
    supabase = get_supabase_client()
    return MenuService(supabase, cache_manager=cache_mgr)


# ============ ROUTER ============


router = APIRouter(
    prefix="/menu",
    tags=["Menu CRUD"],
    dependencies=[Depends(verify_api_key)]
)


# ============ ENDPOINTS ============


@router.post("/", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    item: MenuItemCreate,
    service: MenuService = Depends(get_menu_service)
):
    """➕ Create new menu item"""
    try:
        result = await service.create_item(item.model_dump())
        return result
    except Exception as e:
        logger.error(f"❌ Create endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create item: {str(e)}"
        )


@router.get("/", response_model=List[MenuItemResponse])
async def get_all_menu_items(
    service: MenuService = Depends(get_menu_service)
):
    """📋 Get ALL menu items (Cache-First Strategy)"""
    try:
        results = await service.get_all_items()
        return results
    except Exception as e:
        logger.error(f"❌ Get all endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get items: {str(e)}"
        )

@router.patch("/bulk/availability", response_model=list[MenuItemResponse])
async def bulk_update_availability(
    update: BulkAvailabilityUpdate,
    service: MenuService = Depends(get_menu_service)
):
    """
    🔄 Bulk update menu items availability
    
    **Requires**: X-API-Key header
    
    Update multiple items at once (e.g., mark all sold out items)
    
    **Example:**
    ```
    {
        "item_ids":,[1]
        "is_available": false
    }
    ```
    """
    try:
        results = await service.bulk_update_availability(update.item_ids, update.is_available)
        return results
    except Exception as e:
        logger.error(f"❌ Bulk update availability error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk update availability: {str(e)}"
        )
    
    
@router.patch("/{item_id}/availability", response_model=MenuItemResponse)
async def update_item_availability(
    item_id: int,
    update: AvailabilityUpdate,
    service: MenuService = Depends(get_menu_service)
):
    """🔄 Update menu item availability"""
    try:
        result = await service.update_availability(item_id, update.is_available)
        return result
    except Exception as e:
        logger.error(f"❌ Update availability endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update availability: {str(e)}"
        )
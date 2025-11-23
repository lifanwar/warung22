"""
FastAPI application for menu chatbot API
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from config.cookies import perplexity_cookies
from config.database import get_supabase_client, MenuCacheManager
from core.agent import create_menu_agent
from core.llm import PerplexityCustomLLM
from perplexity_async import Client

logger = logging.getLogger(__name__)

# Global variables
cache_manager = None
agent_graph = None
API_KEY = os.getenv("API_KEY", "default-insecure-key")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


class QuestionRequest(BaseModel):
    """Request model for question endpoint"""
    question: str = Field(..., min_length=1, max_length=500, description="User question about menu")


class AnswerResponse(BaseModel):
    """Response model for answer"""
    question: str
    answer: str
    category: str
    success: bool = True


class RefreshResponse(BaseModel):
    """Response model for cache refresh"""
    message: str
    categories_count: int
    items_count: int
    success: bool = True


def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key from header"""
    if api_key != API_KEY:
        logger.warning(f"⚠️ Invalid API key attempt: {api_key[:10]}...")
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - startup and shutdown"""
    global cache_manager, agent_graph
    
    logger.info("🚀 Starting Warung22 Menu API...")
    
    try:
        # Initialize Supabase
        supabase = get_supabase_client()
        
        # Initialize cache manager
        cache_manager = MenuCacheManager(supabase)
        cache_manager.initialize_cache()
        cache_manager.setup_realtime_listener()
        
        # Initialize Perplexity client
        logger.info("🔌 Initializing Perplexity client...")
        
        perplexity_cli = await Client(perplexity_cookies.perplexity_cookies)
        logger.info("✅ Perplexity client initialized")
        
        # Create LLM and agent
        llm = PerplexityCustomLLM(client=perplexity_cli)
        agent_graph = create_menu_agent(llm, cache_manager)
        
        logger.info("✅ API ready to serve requests")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down API...")
    if cache_manager:
        cache_manager.cleanup()
    logger.info("✅ Shutdown complete")


app = FastAPI(
    title="Warung22 Menu API",
    description="AI-powered menu chatbot API using LangGraph and Perplexity",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Warung22 Menu API",
        "status": "running",
        "version": "1.0.0"
    }


@app.post("/ask", response_model=AnswerResponse)
async def ask_question(
    request: QuestionRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Process question and return answer
    
    Requires X-API-Key header for authentication
    """
    logger.info(f"📥 API Request: '{request.question}'")
    
    try:
        result = await agent_graph.ainvoke({"input": request.question})
        
        logger.info(f"✅ API Response generated for: '{request.question}'")
        
        return AnswerResponse(
            question=request.question,
            answer=result["answer"],
            category=result.get("category", "unknown"),
            success=True
        )
    
    except Exception as e:
        logger.error(f"❌ Error processing question: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


@app.post("/refresh", response_model=RefreshResponse)
async def refresh_cache(api_key: str = Depends(verify_api_key)):
    """
    Manually refresh menu cache from database
    
    Requires X-API-Key header for authentication
    """
    logger.info("🔄 Manual cache refresh requested via API")
    
    try:
        cache_data = cache_manager.refresh_cache()
        categories_count = len(cache_data)
        items_count = sum(len(items) for items in cache_data.values())
        
        logger.info(f"✅ Cache refreshed: {categories_count} categories, {items_count} items")
        
        return RefreshResponse(
            message="Cache successfully refreshed",
            categories_count=categories_count,
            items_count=items_count,
            success=True
        )
    
    except Exception as e:
        logger.error(f"❌ Error refreshing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Error refreshing cache: {str(e)}")


@app.get("/cache/stats")
async def cache_stats(api_key: str = Depends(verify_api_key)):
    """
    Get cache statistics
    
    Requires X-API-Key header for authentication
    """
    cache_data = cache_manager.get_menu_data()
    
    stats = {
        "categories": list(cache_data.keys()),
        "categories_count": len(cache_data),
        "items_count": sum(len(items) for items in cache_data.values()),
        "last_updated": cache_manager.last_updated.isoformat() if cache_manager.last_updated else None,
        "items_by_category": {
            category: len(items) for category, items in cache_data.items()
        }
    }
    
    return stats

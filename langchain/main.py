"""
Warung22 Menu Agent - Main Entry Point
Choose mode: CLI or API Server
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv
from config.cookies.perplexity_cookies import perplexity_cookies

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)


def print_banner():
    """Print application banner"""
    print("\n" + "=" * 60)
    print("🤖 WARUNG22 MENU AGENT")
    print("=" * 60)
    print("Mode Options:")
    print("  1. CLI Mode - Interactive terminal chatbot")
    print("  2. API Mode - FastAPI REST server")
    print("=" * 60 + "\n")


async def run_cli_mode():
    """Run in CLI interactive mode"""
    from config.database import get_supabase_client, MenuCacheManager
    from core.agent import create_menu_agent
    from core.llm import PerplexityCustomLLM
    from perplexity_async import Client
    
    print("\n🤖 AGEN MENU Warung22 - CLI MODE")
    print("=" * 60)
    print("Commands:")
    print("  .menu - Show all menu")
    print("  .refresh - Refresh cache from database")
    print("  exit - Exit application")
    print("=" * 60 + "\n")
    
    # Initialize
    try:
        supabase = get_supabase_client()
    except ValueError as e:
        logger.error(f"❌ {e}")
        return
    
    cache_manager = MenuCacheManager(supabase)
    cache_manager.initialize_cache()
    cache_manager.setup_realtime_listener()
    
    try:
        logger.info("🔌 Initializing Perplexity client...")
        perplexity_cli = await Client(perplexity_cookies)
        logger.info("✅ Perplexity client initialized\n")
        logger.info(f"Cookies:{perplexity_cli}\n")
    except Exception as e:
        logger.error(f"❌ Error init client: {e}")
        return
    
    llm = PerplexityCustomLLM(client=perplexity_cli)
    agent_graph = create_menu_agent(llm, cache_manager)
    
    try:
        while True:
            user_input = input("\n👤 Customer: ").strip()
            
            if user_input.lower() == "exit":
                print("\n👋 Terima kasih sudah berkunjung!\n")
                break
            
            if user_input.lower() == ".refresh":
                cache_manager.refresh_cache()
                print("✅ Cache updated from database")
                continue
            
            if not user_input:
                continue
            
            try:
                result = await agent_graph.ainvoke({"input": user_input})
                print(f"\n🤖 Bot: {result['answer']}")
            except Exception as e:
                logger.error(f"❌ Error: {e}")
                print(f"\n❌ Error: {e}\n")
    
    finally:
        cache_manager.cleanup()
        logger.info("🧹 Cleanup completed")


def run_api_mode():
    """Run in API server mode (production)"""
    import uvicorn
    from events.fastapi_app import app
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"🌐 Starting API server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


def run_api_mode_reload():
    """Run in API server mode with auto-reload (development)"""
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"🌐 Starting API server on {host}:{port} (with auto-reload)")
    
    # Gunakan string format untuk reload
    uvicorn.run(
        "events.fastapi_app:app",  # Format: module_name:app_variable
        host=host,
        port=port,
        log_level="info",
        reload=True
    )


def main():
    """Main entry point"""
    print_banner()
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        mode = input("Choose mode (cli/api): ").strip().lower()
    
    if mode == "cli":
        asyncio.run(run_cli_mode())
    elif mode == "api":
        if len(sys.argv) > 2 and sys.argv[2] == "--reload":
            run_api_mode_reload()
        else:
            run_api_mode()
    else:
        print("❌ Invalid mode. Choose 'cli' or 'api'")
        sys.exit(1)


if __name__ == "__main__":
    main()

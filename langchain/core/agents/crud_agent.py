# core/agents/crud_agent.py
"""
CRUD Agent - Natural language to menu availability updates
"""

import logging
import time
import json
import re
from typing import TypedDict, List, Dict, Any, Optional, Union
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END

from core.llm import PerplexityCustomLLM
from core.deepseek_llm import DeepSeekCustomLLM
from core.utils import menu_to_toon, category_to_toon
from config.database import MenuCacheManager, get_supabase_client
from services.menu_service import MenuService

logger = logging.getLogger(__name__)


class CRUDState(TypedDict):
    """LangGraph state for CRUD operations"""
    input: str
    categories: List[str]
    menu_data: str
    parsed_ids: Optional[List[int]]
    target_status: Optional[bool]
    updated_items: Optional[List[Dict[str, Any]]]
    error: Optional[str]
    result: str


class CRUDAgent:
    """AI agent for menu CRUD operations"""
    
    def __init__(self, llm: Union[PerplexityCustomLLM, DeepSeekCustomLLM], cache_manager: MenuCacheManager, temperature_routing: float = 1.0, temperature_answer: float = 1.3):
        self.llm = llm
        self.cache_manager = cache_manager
        # Temperatur Config
        self.temperature_routing, self.temperature_answer = temperature_routing, 
        logger.info("✅ CRUDAgent initialized")
    
    async def route_categories(self, state: CRUDState):
        """Node 1: Detect category"""
        logger.info("=" * 60)
        logger.info(f"📥 [CRUD-ROUTE] Input: '{state['input']}'")
        start_time = time.time()
        
        routing_prompt = ChatPromptTemplate.from_template(
            ("system", """
             Deteksi kategori. Return JSON array.

MAPPING:
- ayam/chicken/geprek/crispy/bakar/rica/goreng/jumbo → protein_ayam
- ati/ampela/jeroan → ati_ampela
- ikan/fish → protein_ikan
- tahu/tempe/telur/egg → protein_ringan
- nasi goreng/kwetiaw/pempek/batagor/ketoprak/nasi → karbo
- paket → paket_hemat
- soto/sop/kuah → menu_kuah
- minuman/minum dingin/cold/es/ice → minum_cold
- minuman/minum hangat/hot/panas → minum_hot
- .menu/semua/all/lengkap → all

ATURAN OUTPUT:
- Jawab HANYA JSON array, tanpa penjelasan
- Contoh valid: ["protein_ayam"], ["menu_kuah", "minum_cold"], ["all"]
- Jika tidak yakin, return ["all"]:
             """),
            ("user", "PERTANYAAN: {input}")
        )
        
        try:
            chain = routing_prompt | self.llm | StrOutputParser()
            try:
                response = await chain.ainvoke(
                    {"input": state["input"]},
                    config={"temperature": self.temperature_routing}
                )
            except (TypeError, KeyError):
                logger.debug("Temperature not supported, using default")
                response = await chain.ainvoke({"input": state["input"]})
            
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1].split("\n", 1)[-1]
            
            categories = json.loads(cleaned.strip())
            if not isinstance(categories, list):
                categories = ["all"]
            
            valid = ["protein_ayam", "ati_ampela", "protein_ikan", "protein_ringan",
                    "karbo", "paket_hemat", "menu_kuah", "minum_cold", "minum_hot", "all"]
            
            categories = [c for c in categories if c in valid] or ["all"]
            
            elapsed = time.time() - start_time
            logger.info(f"✅ [CRUD-ROUTE] Categories: {categories} ({elapsed:.2f}s)")
            
            return {"categories": categories}
            
        except Exception as e:
            logger.error(f"❌ [CRUD-ROUTE] Error: {e}, fallback to 'all'")
            return {"categories": ["all"]}
    
    def load_menu_data(self, state: CRUDState):
        """Node 2: Load menu by category"""
        categories = state["categories"]
        logger.info(f"🔍 [CRUD-LOAD] Loading: {categories}")
        start_time = time.time()
        
        menu_data = self.cache_manager.get_menu_data()
        
        # Jika "all", kirim semua data
        if "all" in categories:
            all_items = [item for items in menu_data.values() for item in items]
        else:
            all_items = []
            for cat in categories:
                items = self.cache_manager.get_category_data(cat)
                if items:
                    all_items.extend(items)
            
            # Fallback ke ALL jika kategori kosong
            if not all_items:
                logger.warning(f"⚠️ No data for {categories}, loading ALL")
                all_items = [item for items in menu_data.values() for item in items]
        
        # Format simple: ID,Name
        simple_toon = "\n".join([f"{item['id']},{item['name']}" for item in all_items])
        
        elapsed = time.time() - start_time
        logger.info(f"✅ [CRUD-LOAD] Loaded {len(all_items)} items ({elapsed:.4f}s)")
        
        return {"menu_data": simple_toon}
    
    async def extract_ids(self, state: CRUDState):
        """Node 3: Extract IDs with clarification check"""
        logger.info(f"🤖 [CRUD-EXTRACT] Extracting IDs...")
        start_time = time.time()
        
        extract_prompt = ChatPromptTemplate.from_messages([
    ("system", """Extract menu IDs Warung22.

Logic:
- Generic ("ikan habis") → CLARIFY:Ikan apa?
- Specific ("ikan goreng") → Return ID only
- + "semua" → Return ALL matching
- "semua" alone → Return ALL

Format: "id1,id2,status" OR "CLARIFY:Question?"
Status: habis=false, ada=true"""),
    
    ("user", "DATA: {menu_data}\nREQUEST: {input}")
])
        
        try:
            chain = extract_prompt | self.llm | StrOutputParser()
            try:
                response = await chain.ainvoke(
                    {
                        "menu_data": state["menu_data"],
                        "input": state["input"]
                    },
                    config={"temperature": self.temperature_routing}  # ✅ Pakai temperature_answer!
                )
            except (TypeError, KeyError, AttributeError):
                logger.debug("Temperature not supported, using default")
                response = await chain.ainvoke({
                    "menu_data": state["menu_data"],
                    "input": state["input"]
                })
            
            logger.info(f"📤 [CRUD-EXTRACT] Response: '{response}'")
            
            # Check if AI asks for clarification
            if response.startswith("CLARIFY:"):
                clarification = response.replace("CLARIFY:", "").strip()
                return {
                    "parsed_ids": None,
                    "target_status": None,
                    "error": "need_clarification",
                    "result": f"❓ {clarification}"
                }
            
            # Parse IDs
            pattern = r'(\d+(?:,\d+)*),(true|false)'
            match = re.search(pattern, response, re.IGNORECASE)
            
            if not match:
                return {
                    "parsed_ids": None,
                    "target_status": None,
                    "error": "parse_failed",
                    "result": f"❌ Parse gagal: {response[:100]}"
                }
            
            ids_str, status_str = match.groups()
            item_ids = [int(x.strip()) for x in ids_str.split(',')]
            is_available = (status_str.lower() == 'true')
            
            logger.info(f"✅ [CRUD-EXTRACT] {len(item_ids)} items, Status: {'TERSEDIA' if is_available else 'HABIS'}")
            
            return {
                "parsed_ids": item_ids,
                "target_status": is_available
            }
            
        except Exception as e:
            logger.error(f"❌ [CRUD-EXTRACT] Error: {e}")
            return {
                "parsed_ids": None,
                "target_status": None,
                "error": str(e),
                "result": f"❌ Error: {str(e)}"
            }
    
    async def execute_update(self, state: CRUDState):
        """Node 4: Update database"""
        logger.info(f"⚙️ [CRUD-EXECUTE] Updating database...")
        
        if not state.get("parsed_ids") or state.get("target_status") is None:
            error_msg = state.get("result", "❌ No data to update")
            logger.warning(f"⚠️ [CRUD-EXECUTE] Skipped: {state.get('error')}")
            return {"result": error_msg}
        
        try:
            supabase = get_supabase_client()
            service = MenuService(supabase, cache_manager=self.cache_manager)
            
            updated_items = await service.bulk_update_availability(
                state["parsed_ids"],
                state["target_status"]
            )
            
            if not updated_items:
                return {
                    "updated_items": [],
                    "error": "update_failed",
                    "result": "❌ Update gagal"
                }
            
            logger.info(f"✅ [CRUD-EXECUTE] Updated {len(updated_items)} items")
            for item in updated_items:
                icon = "✅" if item['is_available'] else "❌"
                logger.info(f"   {icon} [{item['id']}] {item['name']}")
            
            return {"updated_items": updated_items}
            
        except Exception as e:
            logger.error(f"❌ [CRUD-EXECUTE] Error: {e}")
            return {
                "updated_items": [],
                "error": str(e),
                "result": f"❌ DB Error: {str(e)}"
            }
    
    async def generate_message(self, state: CRUDState):
        """Node 5: Generate response"""
        updated_items = state.get("updated_items", [])
        
        if not updated_items:
            return {"result": state.get("result", "❌ Update gagal")}
        
        status_text = "tersedia" if updated_items[0]['is_available'] else "habis"
        msg = f"✅ Berhasil update {len(updated_items)} menu jadi {status_text}:\n"
        msg += "\n".join([f"- {item['name']}" for item in updated_items])
        
        logger.info(f"✅ [CRUD-MESSAGE] Generated message")
        return {"result": msg}


def create_crud_agent(llm: PerplexityCustomLLM, cache_manager: MenuCacheManager):
    """Build CRUD workflow"""
    logger.info("🔧 Building CRUD Agent...")
    
    agent = CRUDAgent(llm, cache_manager)
    workflow = StateGraph(CRUDState)
    
    workflow.add_node("route", agent.route_categories)
    workflow.add_node("load", agent.load_menu_data)
    workflow.add_node("extract", agent.extract_ids)
    workflow.add_node("execute", agent.execute_update)
    workflow.add_node("message", agent.generate_message)
    
    workflow.add_edge(START, "route")
    workflow.add_edge("route", "load")
    workflow.add_edge("load", "extract")
    workflow.add_edge("extract", "execute")
    workflow.add_edge("execute", "message")
    workflow.add_edge("message", END)
    
    logger.info("✅ CRUD Agent compiled")
    return workflow.compile()

# core/agents/crud_agent.py
"""
CRUD Agent - Natural language to menu availability updates
Handles AI-powered bulk menu status changes
"""

import logging
import time
import json
import re
from typing import TypedDict, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END

from core.llm import PerplexityCustomLLM
from core.utils import menu_to_toon, category_to_toon
from config.database import MenuCacheManager, get_supabase_client
from services.menu_service import MenuService

logger = logging.getLogger(__name__)


class CRUDState(TypedDict):
    """LangGraph state for CRUD operations"""
    input: str
    categories: List[str]
    relevant_data: str
    formatted_ids: str
    updated_toon: str  # 🔥 Added: TOON dari hasil update
    result: str


class CRUDAgent:
    """AI agent for menu CRUD operations via natural language"""
    
    def __init__(self, llm: PerplexityCustomLLM, cache_manager: MenuCacheManager):
        self.llm = llm
        self.cache_manager = cache_manager
        logger.info("✅ CRUDAgent initialized")
    
    async def route_categories(self, state: CRUDState):
        """Node 1: Detect categories"""
        logger.info("=" * 60)
        logger.info(f"📥 [CRUD-ROUTE] Input: '{state['input']}'")
        start_time = time.time()
        
        routing_prompt = ChatPromptTemplate.from_template(
            """Identifikasi SEMUA kategori menu yang disebutkan dalam permintaan user.
Jawab dengan JSON array berisi kategori yang terdeteksi.

MAPPING KATA KUNCI:
- ayam/chicken/geprek/crispy/bakar/rica/goreng/jumbo → protein_ayam
- ati/ampela/jeroan → ati_ampela
- ikan/fish → protein_ikan
- tahu/tempe/telur/egg → protein_ringan
- nasi goreng/kwetiaw/pempek/batagor/ketoprak/nasi → karbo
- paket → paket_hemat
- soto/sop/kuah → menu_kuah
- minuman/minum dingin/cold/es/ice → minum_cold
- minuman/minum hangat/hot/panas → minum_hot
- semua/all/lengkap → all

PERMINTAAN USER: {input}

Jawab HANYA JSON array. Contoh valid:
- ["protein_ayam", "protein_ringan"]
- ["menu_kuah", "minum_cold"]
- ["all"]

KATEGORI:"""
        )
        
        chain = routing_prompt | self.llm | StrOutputParser()
        response = await chain.ainvoke({"input": state["input"]})
        
        try:
            cleaned = response.strip()
            
            if cleaned.startswith("```"):
                parts = cleaned.split("```")
                if len(parts) >= 3:
                    cleaned = parts[1]
                    lines = cleaned.strip().split("\n")
                    if lines[0].strip().lower() in ["json", "python", "text"]:
                        cleaned = "\n".join(lines[1:])
            
            cleaned = cleaned.strip()
            categories = json.loads(cleaned)
            
            if not isinstance(categories, list):
                logger.warning(f"⚠️ Response not a list: {response}")
                categories = ["all"]
                
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning(f"⚠️ JSON parse failed ({e}), fallback to 'all'")
            categories = ["all"]
        
        valid_categories = [
            "protein_ayam", "ati_ampela", "protein_ikan", "protein_ringan",
            "karbo", "paket_hemat", "menu_kuah", "minum_cold", "minum_hot", "all"
        ]
        
        categories = [c for c in categories if c in valid_categories]
        
        if not categories:
            logger.warning(f"⚠️ No valid categories found, fallback to 'all'")
            categories = ["all"]
        
        elapsed = time.time() - start_time
        logger.info(f"✅ [CRUD-ROUTE] Detected {len(categories)} categories: {categories} ({elapsed:.2f}s)")
        
        return {"categories": categories}
    
    def filter_menu_data(self, state: CRUDState):
        """Node 2: Filter menu data by categories"""
        categories = state["categories"]
        logger.info(f"🔍 [CRUD-FILTER] Processing {len(categories)} categories: {categories}")
        start_time = time.time()
        
        menu_data = self.cache_manager.get_menu_data()
        
        if "all" in categories:
            toon_data = menu_to_toon(menu_data)
            total_items = sum(len(items) for items in menu_data.values())
            logger.info(f"📊 [CRUD-FILTER] ALL menu ({total_items} items) from cache")
        else:
            aggregated_data = {}
            total_items = 0
            
            for category in categories:
                items = self.cache_manager.get_category_data(category)
                if items:
                    aggregated_data[category] = items
                    total_items += len(items)
                    logger.info(f"  ├─ {category}: {len(items)} items")
            
            if not aggregated_data:
                logger.warning(f"⚠️ No data found for categories: {categories}")
                toon_data = "# No menu data available"
            else:
                toon_parts = []
                for category, items in aggregated_data.items():
                    toon_parts.append(category_to_toon(category, items))
                
                toon_data = "\n\n".join(toon_parts)
                logger.info(f"📊 [CRUD-FILTER] Aggregated {total_items} items from {len(categories)} categories")
        
        elapsed = time.time() - start_time
        logger.info(f"✅ [CRUD-FILTER] Converted to TOON ({elapsed:.4f}s)")
        
        return {"relevant_data": toon_data}
    
    async def extract_ids(self, state: CRUDState):
        """Node 3: Extract IDs (simple format)"""
        logger.info(f"🤖 [CRUD-EXTRACT] Extracting IDs...")
        start_time = time.time()
        
        if state["relevant_data"] == "# No menu data available":
            return {"formatted_ids": "", "result": "Menu tidak tersedia."}
        
        extract_prompt = ChatPromptTemplate.from_template(
            """Extract menu IDs.
    
    DATA:
    {menu_data}
    
    REQUEST: {input}
    
    RULES:
    1. Find items matching the request keyword
    2. "ikan" → ONLY items with "Ikan" in name
    3. "ayam" → ONLY items with "Ayam" in name
    4. "jumbo" → ONLY items with "Jumbo" in name
    5. Status: "habis"/"sold"/"kosong"=false, "ada"/"ready"/"tersedia"=true
    
    EXAMPLES:
    Data: 14,Ikan Goreng | 15,Ikan Bakar | 1,Ayam Crispy
    Request: ikan ada → 14,15,true (NOT 1!)
    
    Data: 1,Ayam Jumbo | 2,Geprek Jumbo | 3,Crispy
    Request: jumbo habis → 1,2,false (NOT 3!)
    
    CRITICAL: Extract ONLY items matching the keyword!
    
    OUTPUT (IDs,status):"""
        )
        
        try:
            chain = extract_prompt | self.llm | StrOutputParser()
            response = await chain.ainvoke({
                "menu_data": state["relevant_data"],
                "input": state["input"]
            })
            
            elapsed_ai = time.time() - start_time
            logger.info(f"⏱️ [CRUD-EXTRACT] AI: {elapsed_ai:.2f}s")
            logger.info(f"📤 [CRUD-EXTRACT] Response: '{response}'")
            
            # Parse format: "14,15,16,17,false"
            pattern = r'(\d+(?:,\d+)*),(true|false)'
            match = re.search(pattern, response, re.IGNORECASE)
            
            if match:
                ids_str = match.group(1)
                status_str = match.group(2).lower()
                
                item_ids = [int(x.strip()) for x in ids_str.split(',')]
                is_available = (status_str == 'true')
                
                logger.info(f"✅ [CRUD-EXTRACT] Parsed: IDs={item_ids}, Available={is_available}")
                
                supabase = get_supabase_client()
                service = MenuService(supabase, cache_manager=self.cache_manager)
                updated_items = await service.bulk_update_availability(item_ids, is_available)
                
                if updated_items:
                    toon_lines = []
                    for item in updated_items:
                        status = "1" if item['is_available'] else "0"
                        toon_lines.append(f"{item['id']},{item['name']},{status}")
                    
                    logger.info(f"✅ [CRUD-EXTRACT] Updated {len(updated_items)} items")
                    return {"formatted_ids": "success", "updated_toon": "\n".join(toon_lines)}
                else:
                    return {"formatted_ids": "", "result": "Update gagal."}
            else:
                logger.error(f"❌ Parse failed: '{response}'")
                return {"formatted_ids": "", "result": f"Format tidak valid: {response}"}
        
        except Exception as e:
            logger.error(f"❌ [CRUD-EXTRACT] Error: {e}")
            return {"formatted_ids": "", "result": f"Error: {str(e)}"}
    


    
    async def execute_update(self, state: CRUDState):
        """Node 4: Execute bulk update to database"""
        formatted_ids = state.get("formatted_ids", "")
        
        if not formatted_ids:
            return {"result": state.get("result", "Menu tidak ditemukan.")}
        
        logger.info(f"⚙️ [CRUD-EXECUTE] Executing update: {formatted_ids}")
        
        try:
            match = re.match(r'\[([0-9,]+)\],([01])', formatted_ids)
            if not match:
                logger.error(f"❌ [CRUD-EXECUTE] Invalid format: {formatted_ids}")
                return {"result": "Format parsing gagal."}
            
            item_ids = [int(id_) for id_ in match.group(1).split(',')]
            is_available = (match.group(2) == '1')
            
            logger.info(f"📊 [CRUD-EXECUTE] IDs={item_ids}, Available={is_available}")
            
            supabase = get_supabase_client()
            service = MenuService(supabase, cache_manager=self.cache_manager)
            
            updated_items = await service.bulk_update_availability(item_ids, is_available)
            
            if updated_items:
                # 🔥 Convert hasil update ke TOON (hanya id, name, is_available)
                toon_lines = []
                for item in updated_items:
                    status = "1" if item['is_available'] else "0"
                    toon_lines.append(f"{item['id']},{item['name']},{status}")
                
                updated_toon = "\n".join(toon_lines)
                
                logger.info(f"✅ [CRUD-EXECUTE] Success: {len(updated_items)} items updated")
                logger.info(f"📋 [CRUD-EXECUTE] Updated TOON:\n{updated_toon}")
                
                return {"updated_toon": updated_toon}
            else:
                logger.warning("⚠️ [CRUD-EXECUTE] No items updated")
                return {"result": "Ada masalah ketika update data."}
        
        except Exception as e:
            logger.error(f"❌ [CRUD-EXECUTE] Error: {e}")
            return {"result": f"Error saat update: {str(e)}"}
    
    async def generate_message(self, state: CRUDState):
        """Node 5: AI generate natural message from update result"""
        updated_toon = state.get("updated_toon", "")
        
        if not updated_toon:
            # Jika tidak ada updated_toon, return result yang sudah ada
            return {"result": state.get("result", "Update gagal.")}
        
        logger.info(f"💬 [CRUD-MESSAGE] Generating natural message...")
        start_time = time.time()
        
        message_prompt = ChatPromptTemplate.from_template(
            """Anda adalah sistem notifikasi update menu.

DATA HASIL UPDATE (TOON):
{updated_data}

FORMAT:
- id,nama_menu,status
- Status: 1 = tersedia, 0 = habis

USER REQUEST: {input}

TASK:
Buat pesan natural bahwa menu sudah di-update.

TEMPLATE:
✅ Berhasil update [jumlah] menu jadi [status]:
 - [Nama Menu 1]
 - [Nama Menu 2]
 - ...

ATURAN:
- Status "1" → "tersedia"
- Status "0" → "habis"
- List semua nama menu (tanpa ID)
- Bahasa Indonesia, ramah

OUTPUT:"""
        )
        
        chain = message_prompt | self.llm | StrOutputParser()
        response = await chain.ainvoke({
            "updated_data": updated_toon,
            "input": state["input"]
        })
        
        elapsed = time.time() - start_time
        logger.info(f"⏱️ [CRUD-MESSAGE] Message generated ({elapsed:.2f}s)")
        
        return {"result": response.strip()}


def create_crud_agent(llm: PerplexityCustomLLM, cache_manager: MenuCacheManager):
    """Build and compile LangGraph workflow for CRUD agent"""
    logger.info("🔧 Building CRUD Agent workflow...")
    
    agent = CRUDAgent(llm, cache_manager)
    workflow = StateGraph(CRUDState)
    
    workflow.add_node("route", agent.route_categories)
    workflow.add_node("filter", agent.filter_menu_data)
    workflow.add_node("extract", agent.extract_ids)
    workflow.add_node("execute", agent.execute_update)
    workflow.add_node("message", agent.generate_message)  # 🔥 Added
    
    workflow.add_edge(START, "route")
    workflow.add_edge("route", "filter")
    workflow.add_edge("filter", "extract")
    workflow.add_edge("extract", "execute")
    workflow.add_edge("execute", "message")  # 🔥 Added
    workflow.add_edge("message", END)  # 🔥 Changed
    
    logger.info("✅ CRUD Agent workflow compiled")
    return workflow.compile()

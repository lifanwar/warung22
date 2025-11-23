"""
Core Menu Agent - LangGraph workflow orchestrator
"""

import logging
import time
import json
from typing import TypedDict, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, START, END

from core.llm import PerplexityCustomLLM
from core.utils import menu_to_toon, category_to_toon
from config.database import MenuCacheManager

logger = logging.getLogger(__name__)


class State(TypedDict):
    """LangGraph state definition"""
    input: str
    categories: List[str]  # ✅ CHANGED: singular -> plural
    relevant_data: str
    answer: str
    llm_input_tokens: int
    llm_output_tokens: int


class MenuAgent:
    """Main agent orchestrator"""
    
    def __init__(self, llm: PerplexityCustomLLM, cache_manager: MenuCacheManager):
        self.llm = llm
        self.cache_manager = cache_manager
        self.current_input_tokens = 0
        self.current_output_tokens = 0
        logger.info("✅ MenuAgent initialized")
    
    async def route_query(self, state: State):
        """Node 1: Detect multiple categories from query"""
        logger.info("=" * 60)
        logger.info(f"📥 [ROUTE] Input: '{state['input']}'")
        start_time = time.time()
        
        routing_prompt = ChatPromptTemplate.from_template(
            """Identifikasi SEMUA kategori menu yang disebutkan dalam pertanyaan user.
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
    - .menu/semua/all/lengkap → all
    
    PERTANYAAN USER: {input}
    
    Jawab HANYA JSON array. Contoh valid:
    - ["protein_ayam", "protein_ringan"]
    - ["menu_kuah", "minum_cold"]
    - ["all"]
    
    KATEGORI:"""
        )
        
        chain = routing_prompt | self.llm | StrOutputParser()
        response = await chain.ainvoke({"input": state["input"]})
        
        # Parse JSON with error handling
        try:
            # Clean response (remove markdown code blocks if any)
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
            logger.debug(f"Raw response: {response}")
            categories = ["all"]
        
        # Validate categories
        valid_categories = [
            "protein_ayam", "ati_ampela", "protein_ikan", "protein_ringan",
            "karbo", "paket_hemat", "menu_kuah", "minum_cold", "minum_hot", "all"
        ]
        
        categories = [c for c in categories if c in valid_categories]
        
        if not categories:
            logger.warning(f"⚠️ No valid categories found, fallback to 'all'")
            categories = ["all"]
        
        elapsed = time.time() - start_time
        logger.info(f"✅ [ROUTE] Detected {len(categories)} categories: {categories} ({elapsed:.2f}s)")
        
        return {"categories": categories}
    
    
    def filter_data(self, state: State):
        """Node 2: Filter and aggregate data from multiple categories"""
        categories = state["categories"]  # ✅ FIXED: Access plural key
        logger.info(f"🔍 [FILTER] Processing {len(categories)} categories: {categories}")
        start_time = time.time()
        
        menu_data = self.cache_manager.get_menu_data()
        
        if "all" in categories:
            toon_data = menu_to_toon(menu_data)
            total_items = sum(len(items) for items in menu_data.values())
            logger.info(f"📊 [FILTER] ALL menu ({total_items} items) from cache")
        else:
            # Aggregate data from multiple categories
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
                # Convert each category to TOON and combine
                toon_parts = []
                for category, items in aggregated_data.items():
                    toon_parts.append(category_to_toon(category, items))
                
                toon_data = "\n\n".join(toon_parts)
                logger.info(f"📊 [FILTER] Aggregated {total_items} items from {len(categories)} categories")
        
        elapsed = time.time() - start_time
        logger.info(f"✅ [FILTER] Converted to TOON ({elapsed:.4f}s)")
        
        return {"relevant_data": toon_data}
    
    async def generate_answer(self, state: State):
        """Node 3: Generate natural language answer for multiple items"""
        categories = state["categories"]  # ✅ FIXED: Access plural key
        logger.info(f"💬 [ANSWER] Generating response for {len(categories)} categories...")
        start_time = time.time()
        
        prompt_template = """Anda adalah pelayan ramah Warung22 di Mesir.

DATA MENU (FORMAT TOON):
{menu_data}

CARA BACA FORMAT TOON:
- category[count]{{field1,field2,field3}}: → kategori dengan jumlah item dan struktur field
- Setiap baris data: nama,harga,status
- Status: 1 = tersedia, 0 = sedang habis

PERTANYAAN USER: {input}

ATURAN PENTING:
- Jawab dengan bahasa ramah dan natural
- Semua harga WAJIB format: [angka] EGP (contoh: 90 EGP, 45 EGP, 15 EGP)
- JANGAN gunakan "Rp" atau mata uang lain
- Status 0 berarti "sedang habis", Status 1 berarti "tersedia"
- Jika item tidak ada di data, katakan "tidak tersedia di menu kami"
- Untuk ".menu", tampilkan semua dengan format rapi per kategori

CONTOH JAWABAN BENAR:
"Geprek Jumbo tersedia dengan harga 90 EGP."
"Telur Ceplok sedang habis saat ini."

CONTOH JAWABAN SALAH:
"Geprek Jumbo tersedia dengan harga Rp90." ❌

JAWABAN:"""



        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        chain = prompt | self.llm | StrOutputParser()
        
        answer = await chain.ainvoke({
            "menu_data": state["relevant_data"],
            "input": state["input"]
        })
        
        elapsed = time.time() - start_time
        logger.info(f"✅ [ANSWER] Response generated ({elapsed:.2f}s)")
        
        return {"answer": answer}


def create_menu_agent(llm: PerplexityCustomLLM, cache_manager: MenuCacheManager):
    """Build and compile LangGraph workflow"""
    logger.info("🔧 Building LangGraph workflow...")
    
    agent = MenuAgent(llm, cache_manager)
    workflow = StateGraph(State)
    
    workflow.add_node("route", agent.route_query)
    workflow.add_node("filter", agent.filter_data)
    workflow.add_node("answer", agent.generate_answer)
    
    workflow.add_edge(START, "route")
    workflow.add_edge("route", "filter")
    workflow.add_edge("filter", "answer")
    workflow.add_edge("answer", END)
    
    logger.info("✅ LangGraph workflow compiled")
    return workflow.compile()

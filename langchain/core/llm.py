"""
Custom LLM wrapper for Perplexity API
"""

import logging
import time
from typing import Any, Optional, List
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun

from core.utils import estimate_tokens, extract_answer_from_response

logger = logging.getLogger(__name__)


class PerplexityCustomLLM(LLM):
    """LangChain wrapper for Perplexity API with auto-fallback"""
    client: Any = None
    use_pro_mode: bool = True  # Track if pro mode is available
    
    def __init__(self, client, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.use_pro_mode = True
        logger.info("✅ PerplexityCustomLLM initialized")
    
    @property
    def _llm_type(self) -> str:
        return "perplexity_custom_auto"
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> str:
        raise NotImplementedError("Gunakan method async (ainvoke).")
    
    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> str:
        start_time = time.time()
        input_chars = len(prompt)
        input_tokens = estimate_tokens(prompt)

        if isinstance(prompt, list):
                # Format messages dari ChatPromptTemplate.from_messages
                # Gabung system + user jadi satu string (Perplexity tidak support messages array)
                prompt_parts = []
                for msg in prompt:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "system":
                        prompt_parts.append(f"SYSTEM INSTRUCTION:\n{content}\n")
                    elif role == "user":
                        prompt_parts.append(f"USER QUERY:\n{content}")
                prompt_str = "\n".join(prompt_parts)
        else:
            # Sudah string biasa
            prompt_str = prompt
        
        logger.info(f"📤 [LLM INPUT] {input_chars} chars | ~{input_tokens} tokens")
        logger.debug(f"📝 Prompt preview: {prompt[:200]}...")
        
        # Try Pro mode first if still available
        if self.use_pro_mode:
            try:
                logger.debug("🔷 Attempting Pro mode (grok-4)...")
                resp = await self.client.search(
                    prompt_str,
                    mode='pro',
                    model='grok-4',
                    sources=['web'],
                    stream=False,
                    follow_up=None,
                    incognito=True
                )
                
                elapsed = time.time() - start_time
                result = extract_answer_from_response(resp)
                output_chars = len(result)
                output_tokens = estimate_tokens(result)
                
                logger.info(f"📥 [LLM OUTPUT - PRO] {output_chars} chars | ~{output_tokens} tokens | {elapsed:.2f}s")
                logger.debug(f"💬 Answer preview: {result[:150]}...")
                
                return result
            
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check if error is about quota/pro queries
                if 'enhanced' in error_msg or 'pro' in error_msg or 'quota' in error_msg or 'limit' in error_msg:
                    logger.warning(f"⚠️ Pro mode quota exhausted: {str(e)}")
                    logger.info("🔄 Switching to Auto mode permanently for this session")
                    self.use_pro_mode = False  # Disable pro mode for remaining requests
                    
                    # Fall through to auto mode below
                else:
                    # Other errors, return error message
                    elapsed = time.time() - start_time
                    logger.error(f"❌ Perplexity API error in Pro mode ({elapsed:.2f}s): {str(e)}")
                    return f"Error from Perplexity: {str(e)}"
        
        # Use Auto mode (fallback or default after pro exhausted)
        try:
            mode_label = "AUTO (fallback)" if not self.use_pro_mode else "AUTO"
            logger.debug(f"🔶 Using Auto mode...")
            
            resp = await self.client.search(
                prompt_str,
                mode='auto',
                model=None,
                sources=['web'],
                stream=False,
                follow_up=None,
                incognito=True
            )
            
            elapsed = time.time() - start_time
            result = extract_answer_from_response(resp)
            output_chars = len(result)
            output_tokens = estimate_tokens(result)
            
            logger.info(f"📥 [LLM OUTPUT - {mode_label}] {output_chars} chars | ~{output_tokens} tokens | {elapsed:.2f}s")
            logger.debug(f"💬 Answer preview: {result[:150]}...")
            
            return result
        
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ Perplexity API error in Auto mode ({elapsed:.2f}s): {str(e)}")
            return f"Error from Perplexity: {str(e)}"

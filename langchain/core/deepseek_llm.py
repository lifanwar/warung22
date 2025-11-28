"""
DeepSeek LLM - Support system role
"""

import logging
from typing import Optional, List
from langchain_core.language_models.llms import LLM
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class DeepSeekCustomLLM(LLM):
    client: object = None
    api_key: str = ""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        logger.info("✅ DeepSeek initialized")
    
    @property
    def _llm_type(self) -> str:
        return "deepseek"
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> str:
        raise NotImplementedError("Use ainvoke()")
    
    async def _acall(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> str:
        try:
            # ✅ HANDLE: Deteksi format prompt
            if isinstance(prompt, list):
                # Sudah format messages dari ChatPromptTemplate.from_messages
                # Format: [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
                messages = prompt
            elif isinstance(prompt, str):
                # String biasa dari ChatPromptTemplate.from_template
                messages = [{"role": "user", "content": prompt}]
            else:
                messages = [{"role": "user", "content": str(prompt)}]
            
            # Kirim ke DeepSeek (format sudah sesuai dokumentasi!)
            resp = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,  # ✅ Bisa system+user atau cuma user
                temperature=0.7,
                max_tokens=2000
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"DeepSeek error: {e}")
            return f"Error: {e}"

"""
DeepSeek LLM - Support system role & dynamic temperature
"""

import logging
from typing import Optional, List
from langchain_core.language_models.llms import LLM
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class DeepSeekCustomLLM(LLM):
    client: object = None
    api_key: str = ""
    default_temperature: float = 1.0
    
    def __init__(self, api_key: str, default_temperature: float = 1.0, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.default_temperature = default_temperature
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        logger.info(f"✅ DeepSeek initialized (default temp: {default_temperature})")
    
    @property
    def _llm_type(self) -> str:
        return "deepseek"
    
    def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> str:
        raise NotImplementedError("Use ainvoke()")
    
    async def _acall(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> str:
        try:
            # ✅ Get temperature dari kwargs atau pakai default
            temperature = kwargs.get('temperature', self.default_temperature)
            
            # Handle format prompt
            if isinstance(prompt, list):
                # Format messages dari ChatPromptTemplate.from_messages
                messages = prompt
            elif isinstance(prompt, str):
                # String biasa dari ChatPromptTemplate.from_template
                messages = [{"role": "user", "content": prompt}]
            else:
                messages = [{"role": "user", "content": str(prompt)}]
            
            logger.debug(f"🌡️  Using temperature: {temperature}")
            
            # Kirim ke DeepSeek
            resp = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=temperature,  # ✅ Dynamic temperature dari kwargs
                max_tokens=2000
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"DeepSeek error: {e}")
            return f"Error: {e}"

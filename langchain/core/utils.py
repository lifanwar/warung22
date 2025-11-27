"""
Utility functions for TOON format and token estimation
"""

import json
import logging

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """Rough token estimation"""
    return len(text) // 3


def menu_to_toon(menu_data: dict) -> str:
    """Convert full menu dict to TOON format"""
    toon_lines = []
    for category, items in menu_data.items():
        if not items:
            continue
        
        count = len(items)
        header = f"{category}[{count}]{{id,name,harga,is_available}}:"
        toon_lines.append(header)
        
        for item in items:
            status = "1" if item.get("is_available", True) else "0"
            line = f"  {item['id']},{item['name']},{item['harga']},{status}"
            toon_lines.append(line)
    
    return "\n".join(toon_lines)


def category_to_toon(category_name: str, items: list) -> str:
    """Convert single category to TOON format"""
    if not items:
        return f"{category_name}[0]{{id,name,harga,is_available}}:"
    
    count = len(items)
    lines = [f"{category_name}[{count}]{{id,name,harga,is_available}}:"]
    
    for item in items:
        status = "1" if item.get("is_available", True) else "0"
        lines.append(f"  {item['id']},{item['name']},{item['harga']},{status}")
    
    return "\n".join(lines)


def extract_answer_from_response(resp):
    """Extract answer from Perplexity API response"""
    logger.debug("🔍 Extracting answer from API response")
    
    if not resp:
        logger.error("❌ No response from API")
        return "Error: No response from API"
    
    if 'text' not in resp:
        logger.error(f"❌ Missing 'text' field. Keys: {list(resp.keys())}")
        return f"Error: Missing 'text' field. Keys: {list(resp.keys())}"
    
    text_content = resp['text']
    
    if isinstance(text_content, list):
        try:
            final_step = next(
                (step for step in text_content 
                 if isinstance(step, dict) and step.get('step_type') == 'FINAL'), 
                None
            )
            
            if final_step and 'content' in final_step:
                content = final_step['content']
                
                if isinstance(content, dict) and 'answer' in content:
                    if isinstance(content['answer'], str):
                        try:
                            answer_json = json.loads(content['answer'])
                            result = answer_json.get('answer', str(answer_json))
                            logger.debug(f"✅ Extracted answer (JSON): {result[:100]}...")
                            return result
                        except json.JSONDecodeError:
                            logger.debug(f"✅ Extracted answer (string): {content['answer'][:100]}...")
                            return content['answer']
                    elif isinstance(content['answer'], dict):
                        result = content['answer'].get('answer', str(content['answer']))
                        logger.debug(f"✅ Extracted answer (dict): {result[:100]}...")
                        return result
                    else:
                        result = str(content['answer'])
                        logger.debug(f"✅ Extracted answer (other): {result[:100]}...")
                        return result
                
                return str(content)
            
            elif text_content:
                last_step = text_content[-1]
                if isinstance(last_step, dict) and 'content' in last_step:
                    return str(last_step['content'])
                return str(last_step)
            
            return "Error: Empty steps list"
        
        except Exception as e:
            logger.error(f"❌ Error parsing steps: {str(e)}")
            return f"Error parsing steps: {str(e)}"
    
    elif isinstance(text_content, str):
        logger.debug(f"✅ Direct string response: {text_content[:100]}...")
        return text_content
    
    elif isinstance(text_content, dict):
        return str(text_content)
    
    else:
        logger.error(f"❌ Unknown format: {type(text_content)}")
        return f"Error: Unknown format"

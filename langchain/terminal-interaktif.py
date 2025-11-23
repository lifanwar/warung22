import asyncio
import json
from perplexity_async import Client
from config.cookies.perplexity_cookies import perplexity_cookies

def extract_answer_from_response(resp):
    """
    Ekstrak jawaban dari response Perplexity API dengan menangani multiple format.
    Support untuk: step-by-step (Claude/GPT), plain text (Grok), dan error fallback.
    """
    # Error handling jika response kosong atau None
    if not resp:
        return "Error: No response from API"
    
    # Cek apakah 'text' ada di response
    if 'text' not in resp:
        return f"Error: Missing 'text' field in response. Keys: {list(resp.keys())}"
    
    text_content = resp['text']
    
    # Format 1: List of steps (Claude, GPT, dll)
    if isinstance(text_content, list):
        try:
            # Cari step dengan step_type == 'FINAL'
            final_step = next((step for step in text_content if isinstance(step, dict) and step.get('step_type') == 'FINAL'), None)
            
            if final_step and 'content' in final_step:
                content = final_step['content']
                
                # Cek apakah content adalah dict dengan 'answer' field
                if isinstance(content, dict) and 'answer' in content:
                    # Jika answer adalah JSON string, parse dulu
                    if isinstance(content['answer'], str):
                        try:
                            answer_json = json.loads(content['answer'])
                            return answer_json.get('answer', str(answer_json))
                        except json.JSONDecodeError:
                            return content['answer']
                    # Jika answer sudah dict atau string biasa
                    elif isinstance(content['answer'], dict):
                        return content['answer'].get('answer', str(content['answer']))
                    else:
                        return str(content['answer'])
                
                # Fallback: return content langsung
                return str(content)
            
            # Jika tidak ada FINAL step, coba last step
            elif text_content:
                last_step = text_content[-1]
                if isinstance(last_step, dict) and 'content' in last_step:
                    return str(last_step['content'])
                return str(last_step)
            
            return "Error: Empty steps list"
        
        except Exception as e:
            return f"Error parsing steps: {str(e)}"
    
    # Format 2: Plain text/string (Grok, plain response)
    elif isinstance(text_content, str):
        return text_content
    
    # Format 3: Dict langsung (jika Perplexity ubah format)
    elif isinstance(text_content, dict):
        return str(text_content)
    
    # Format tidak dikenali
    else:
        return f"Error: Unknown text format: {type(text_content)} - {str(text_content)[:100]}"

async def ask_question(perplexity_cli):
    while True:
        question = input("Masukkan pertanyaan (atau ketik 'exit' untuk keluar): ")
        
        if question.lower() == 'exit':
            print("Terima kasih! Program selesai.")
            break
        
        try:
            resp = await perplexity_cli.search(
                question, 
                mode="pro",           
                model='claude-4.5-sonnet',        
                sources=['web'], 
                stream=False, 
                follow_up=None, 
                incognito=True
            )
            
            # Gunakan handler universal
            answer = extract_answer_from_response(resp)
            
            print(f"Jawaban: {answer}\n")
            
        except Exception as e:
            print(f"Error saat memproses pertanyaan: {str(e)}\n")
            # Print debug info jika error
            if 'resp' in locals():
                print(f"Debug - Response keys: {list(resp.keys())}")
                if 'text' in resp:
                    print(f"Debug - Text type: {type(resp['text'])}")

async def main():
    perplexity_cli = await Client(perplexity_cookies)
    await ask_question(perplexity_cli)

asyncio.run(main())


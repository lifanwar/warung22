import asyncio
import json
import inspect
import sys
from typing import Dict, Any, Union, AsyncGenerator

try:
    from perplexity_async import Client
    from config.cookies.perplexity_cookies import perplexity_cookies
except ImportError as e:
    print(f"Error importing: {e}")
    sys.exit(1)


def extract_answer_from_response(resp: Dict[str, Any]) -> str:
    """Ekstrak jawaban dari response Perplexity API"""
    if not resp:
        return "Error: No response from API"
    
    if 'text' not in resp:
        return f"Error: Missing 'text' field. Keys: {list(resp.keys())}"
    
    text_content = resp['text']
    
    if isinstance(text_content, list):
        try:
            final_step = next((step for step in text_content 
                             if isinstance(step, dict) and step.get('step_type') == 'FINAL'), None)
            
            if final_step and 'content' in final_step:
                content = final_step['content']
                
                if isinstance(content, dict) and 'answer' in content:
                    if isinstance(content['answer'], str):
                        try:
                            answer_json = json.loads(content['answer'])
                            return answer_json.get('answer', str(answer_json))
                        except json.JSONDecodeError:
                            return content['answer']
                    elif isinstance(content['answer'], dict):
                        return content['answer'].get('answer', str(content['answer']))
                    else:
                        return str(content['answer'])
                
                return str(content)
            
            elif text_content:
                last_step = text_content[-1]
                if isinstance(last_step, dict) and 'content' in last_step:
                    return str(last_step['content'])
                return str(last_step)
            
            return "Error: Empty steps list"
        
        except Exception as e:
            return f"Error parsing steps: {str(e)}"
    
    elif isinstance(text_content, str):
        return text_content
    
    elif isinstance(text_content, dict):
        return str(text_content)
    
    else:
        return f"Error: Unknown text format: {type(text_content)}"


async def process_response(resp: Union[Dict, AsyncGenerator, None]) -> Dict[str, Any]:
    """Universal response processor"""
    
    # Case 0: None response (API failed)
    if resp is None:
        raise ValueError("API returned None - possible authentication or connection issue")
    
    # Case 1: Async generator
    if inspect.isasyncgen(resp):
        print("[DEBUG] Processing async generator...")
        full_response = {}
        chunk_count = 0
        
        try:
            async for chunk in resp:
                chunk_count += 1
                print(f"[DEBUG] Chunk {chunk_count}: {type(chunk)}")
                
                if isinstance(chunk, dict):
                    for key, value in chunk.items():
                        if key == 'text':
                            if key in full_response:
                                if isinstance(full_response[key], list) and isinstance(value, list):
                                    full_response[key].extend(value)
                                else:
                                    full_response[key] = value
                            else:
                                full_response[key] = value
                        else:
                            full_response[key] = value
        except Exception as e:
            print(f"[ERROR] Failed processing generator: {e}")
            raise
        
        print(f"[DEBUG] Processed {chunk_count} chunks")
        return full_response if full_response else None
    
    # Case 2: Async iterable
    elif hasattr(resp, '__aiter__'):
        print("[DEBUG] Processing async iterable...")
        full_response = {}
        
        async for chunk in resp:
            if isinstance(chunk, dict):
                full_response.update(chunk)
        
        return full_response if full_response else None
    
    # Case 3: Already dict
    elif isinstance(resp, dict):
        print("[DEBUG] Response is dict")
        return resp
    
    # Case 4: Unknown
    else:
        raise TypeError(f"Unknown response type: {type(resp)}")


async def test_connection(perplexity_cli):
    """Test koneksi ke Perplexity API"""
    print("=== Testing Connection ===")
    
    try:
        # Test dengan query sederhana
        print("Sending test query...")
        resp = await perplexity_cli.search(
            "test", 
            mode="pro",           
            model='claude-4.5-sonnet',        
            sources=['web'], 
            stream=False, 
            follow_up=None, 
            incognito=True
        )
        
        print(f"Response type: {type(resp)}")
        print(f"Response is None: {resp is None}")
        
        if resp is None:
            print("\n❌ API returned None!")
            print("Possible causes:")
            print("1. Invalid/expired cookies")
            print("2. Network/firewall blocking")
            print("3. Rate limiting")
            print("4. Server IP blocked by Perplexity")
            return False
        
        print("✓ Connection successful")
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def ask_question(perplexity_cli):
    while True:
        question = input("\nMasukkan pertanyaan (atau ketik 'exit' untuk keluar): ")
        
        if question.lower() == 'exit':
            print("Terima kasih! Program selesai.")
            break
        
        try:
            print(f"[DEBUG] Sending query: {question}")
            
            # Check if client is valid
            if perplexity_cli is None:
                print("Error: Client not initialized")
                continue
            
            resp = await perplexity_cli.search(
                question, 
                mode="pro",           
                model='claude-4.5-sonnet',        
                sources=['web'], 
                stream=False, 
                follow_up=None, 
                incognito=True
            )
            
            print(f"[DEBUG] Raw response type: {type(resp)}")
            print(f"[DEBUG] Response is None: {resp is None}")
            
            if resp is None:
                print("\n❌ API returned None")
                print("Kemungkinan penyebab:")
                print("- Cookies tidak valid atau expired")
                print("- IP server diblok oleh Perplexity")
                print("- Rate limit tercapai")
                print("- Network/firewall issue")
                print("\nCoba:")
                print("1. Update cookies dari browser")
                print("2. Test dari local dulu")
                print("3. Cek network access dari server")
                continue
            
            # Process response
            final_response = await process_response(resp)
            
            if not final_response:
                print("Error: Empty response after processing")
                continue
            
            print(f"[DEBUG] Final response keys: {list(final_response.keys())}")
            
            # Extract answer
            answer = extract_answer_from_response(final_response)
            print(f"\nJawaban: {answer}\n")
            
        except ValueError as ve:
            print(f"\n❌ ValueError: {ve}")
            print("API call failed - check authentication\n")
            
        except TypeError as te:
            print(f"\n❌ TypeError: {te}")
            import traceback
            traceback.print_exc()
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()


async def main():
    try:
        print("=== Perplexity Terminal Client ===\n")
        
        # Validate cookies
        print("Validating cookies...")
        if not perplexity_cookies:
            print("❌ No cookies found!")
            print("Please add cookies to config/cookies/perplexity_cookies.py")
            return
        
        print(f"✓ Cookies loaded ({len(perplexity_cookies)} entries)")
        
        # Initialize client
        print("\nInitializing client...")
        perplexity_cli = await Client(perplexity_cookies)
        
        if perplexity_cli is None:
            print("❌ Failed to initialize client")
            return
        
        print("✓ Client initialized")
        
        # Test connection
        connection_ok = await test_connection(perplexity_cli)
        
        if not connection_ok:
            print("\n❌ Connection test failed")
            print("Cannot proceed without valid connection")
            return
        
        print("\n" + "="*40)
        
        # Start Q&A loop
        await ask_question(perplexity_cli)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
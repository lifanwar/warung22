import asyncio
import json
import os
from perplexity_async import Client
from config.cookies.perplexity_cookies import perplexity_cookies


def extract_answer_from_response(resp):
    """
    Ekstrak jawaban dari response Perplexity API dengan menangani multiple format.
    Support untuk: step-by-step (Claude/GPT), plain text (Grok), dan error fallback.
    """

    print("\n[LOG] Masuk extract_answer_from_response")
    print("[LOG] Tipe resp:", type(resp))
    print("[LOG] Keys resp:", list(resp.keys()) if isinstance(resp, dict) else None)

    # Error handling jika response kosong atau None
    if not resp:
        print("[LOG] RESP kosong / None")
        return "Error: No response from API"
    
    # Cek apakah 'text' ada di response
    if 'text' not in resp:
        print("[LOG] Field 'text' tidak ada di resp")
        return f"Error: Missing 'text' field in response. Keys: {list(resp.keys())}"
    
    text_content = resp['text']
    print("[LOG] Tipe text_content:", type(text_content))

    # Format 1: List of steps (Claude, GPT, dll)
    if isinstance(text_content, list):
        print("[LOG] text_content adalah list dengan panjang:", len(text_content))
        try:
            # Cari step dengan step_type == 'FINAL'
            final_step = next(
                (step for step in text_content 
                 if isinstance(step, dict) and step.get('step_type') == 'FINAL'),
                None
            )
            print("[LOG] FINAL step ditemukan:", bool(final_step))

            if final_step and 'content' in final_step:
                content = final_step['content']
                print("[LOG] Tipe content di FINAL step:", type(content))
                
                # Cek apakah content adalah dict dengan 'answer' field
                if isinstance(content, dict) and 'answer' in content:
                    print("[LOG] content punya field 'answer', tipe:", type(content['answer']))

                    # Jika answer adalah JSON string, parse dulu
                    if isinstance(content['answer'], str):
                        try:
                            answer_json = json.loads(content['answer'])
                            print("[LOG] answer berhasil di-parse ke JSON, keys:", list(answer_json.keys()))
                            return answer_json.get('answer', str(answer_json))
                        except json.JSONDecodeError:
                            print("[LOG] answer bukan JSON, pakai string mentah")
                            return content['answer']
                    # Jika answer sudah dict atau string biasa
                    elif isinstance(content['answer'], dict):
                        print("[LOG] answer sudah dict, keys:", list(content['answer'].keys()))
                        return content['answer'].get('answer', str(content['answer']))
                    else:
                        print("[LOG] answer tipe lain:", type(content['answer']))
                        return str(content['answer'])
                
                # Fallback: return content langsung
                print("[LOG] FINAL step tanpa field 'answer', fallback return content langsung")
                return str(content)
            
            # Jika tidak ada FINAL step, coba last step
            elif text_content:
                print("[LOG] Tidak ada FINAL step, pakai last step")
                last_step = text_content[-1]
                if isinstance(last_step, dict) and 'content' in last_step:
                    return str(last_step['content'])
                return str(last_step)
            
            print("[LOG] List steps kosong")
            return "Error: Empty steps list"
        
        except Exception as e:
            print("[LOG] Exception di extract_answer_from_response:", repr(e))
            return f"Error parsing steps: {str(e)}"
    
    # Format 2: Plain text/string (Grok, plain response)
    elif isinstance(text_content, str):
        print("[LOG] text_content adalah string plain, panjang:", len(text_content))
        return text_content
    
    # Format 3: Dict langsung (jika Perplexity ubah format)
    elif isinstance(text_content, dict):
        print("[LOG] text_content adalah dict, keys:", list(text_content.keys()))
        return str(text_content)
    
    # Format tidak dikenali
    else:
        print("[LOG] text_content format tidak dikenali:", type(text_content))
        return f"Error: Unknown text format: {type(text_content)} - {str(text_content)[:100]}"


async def ask_question(perplexity_cli):
    print("[LOG] Masuk ask_question(), siap menerima input user")
    print("[LOG] ENV DEBUG, beberapa var terkait PERPLEX / COOKIE:")
    env_keys = [k for k in os.environ.keys() if "PERPLEX" in k.upper() or "COOKIE" in k.upper()]
    print("       ENV KEYS:", env_keys)
    print("[LOG] Tipe perplexity_cookies:", type(perplexity_cookies), "truthy:", bool(perplexity_cookies))

    while True:
        question = input("Masukkan pertanyaan (atau ketik 'exit' untuk keluar): ")
        print(f"[LOG] User question: {question!r}")
        
        if question.lower() == 'exit':
            print("Terima kasih! Program selesai.")
            print("[LOG] User memilih exit, break loop")
            break
        
        try:
            print("[LOG] Memanggil perplexity_cli.search() ...")
            resp = await perplexity_cli.search(
                question, 
                mode="pro",           
                model='claude-4.5-sonnet',        
                sources=['web'], 
                stream=False, 
                follow_up=None, 
                incognito=True
            )
            print("[LOG] Selesai await search()")
            print("[LOG] Tipe resp dari search():", type(resp))

            # RAW RESP (dipotong agar tidak kebanyakan)
            try:
                preview = repr(resp)
            except Exception as e:
                preview = f"<error saat repr(resp): {e}>"
            print("[LOG] RAW RESP PREVIEW (max 800 chars):")
            print(preview[:800])
            
            # KUNCI: Deteksi apakah resp adalah async generator atau dict
            final_response = None
            
            # Cek apakah async generator
            if hasattr(resp, '__aiter__'):
                print("[LOG] resp punya __aiter__, perlakukan sebagai async generator")
                # Ini async generator, collect semua chunks
                full_response = {}
                async for chunk in resp:
                    print("[LOG] Chunk diterima, tipe:", type(chunk))
                    print("[LOG] Chunk preview:", repr(chunk)[:400])
                    if isinstance(chunk, dict):
                        # Merge chunks
                        for key, value in chunk.items():
                            if key == 'text' and key in full_response:
                                # Append text jika sudah ada
                                if isinstance(full_response[key], list):
                                    if isinstance(value, list):
                                        full_response[key].extend(value)
                                    else:
                                        full_response[key].append(value)
                                else:
                                    full_response[key] = value
                            else:
                                full_response[key] = value
                final_response = full_response
                print("[LOG] final_response dari async generator, keys:", list(final_response.keys()))
            
            elif isinstance(resp, dict):
                # Sudah dict langsung (behavior di local)
                print("[LOG] resp adalah dict langsung, keys:", list(resp.keys()))
                final_response = resp
            
            else:
                print(f"[LOG] Error: Unknown response type: {type(resp)}")
                continue
            
            # Extract answer
            answer = extract_answer_from_response(final_response)
            print("[LOG] Hasil extract_answer_from_response, type:", type(answer))
            print(f"Jawaban: {answer}\n")
            
        except Exception as e:
            print(f"Error saat memproses pertanyaan: {str(e)}\n")
            print("[LOG] Exception detail di ask_question:")
            import traceback
            traceback.print_exc()



async def main():
    print("[LOG] Start main()")
    print("[LOG] Python version:", os.sys.version)
    print("[LOG] Current working dir:", os.getcwd())

    print("[LOG] Inisialisasi Client ...")
    perplexity_cli = await Client(perplexity_cookies)
    print("[LOG] Client siap, masuk ask_question()")
    await ask_question(perplexity_cli)
    print("[LOG] Selesai main()")



if __name__ == "__main__":
    print("[LOG] __main__ dieksekusi, menjalankan asyncio.run(main())")
    asyncio.run(main())
    print("[LOG] asyncio.run(main()) selesai")
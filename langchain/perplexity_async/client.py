import re
import sys
import json
import random
import asyncio
import mimetypes
from uuid import uuid4
from curl_cffi import requests, CurlMime

from .emailnator import Emailnator


class AsyncMixin:
    def __init__(self, *args, **kwargs):
        self.__storedargs = args, kwargs
        self.async_initialized = False

    async def __ainit__(self, *args, **kwargs):
        pass

    async def __initobj(self):
        assert not self.async_initialized
        self.async_initialized = True

        # pass the parameters to __ainit__ that passed to __init__
        await self.__ainit__(*self.__storedargs[0], **self.__storedargs[1])
        return self

    def __await__(self):
        return self.__initobj().__await__()


class Client(AsyncMixin):
    '''
    A client for interacting with the Perplexity AI API.
    '''
    async def __ainit__(self, cookies={}):
        print("[CLI-LOG] __ainit__ Client, tipe cookies:", type(cookies), "truthy:", bool(cookies))
        self.session = requests.AsyncSession(
            headers={
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-language': 'en-US,en;q=0.9',
                'cache-control': 'max-age=0',
                'dnt': '1',
                'priority': 'u=0, i',
                'sec-ch-ua': '"Not;A=Brand";v="24", "Chromium";v="128"',
                'sec-ch-ua-arch': '"x86"',
                'sec-ch-ua-bitness': '"64"',
                'sec-ch-ua-full-version': '"128.0.6613.120"',
                'sec-ch-ua-full-version-list': '"Not;A=Brand";v="24.0.0.0", "Chromium";v="128.0.6613.120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-model': '""',
                'sec-ch-ua-platform': '"Windows"',
                'sec-ch-ua-platform-version': '"19.0.0"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'sec-fetch-user': '?1',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            },
            cookies=cookies,
            impersonate='chrome'
        )
        self.own = bool(cookies)
        self.copilot = 0 if not cookies else float('inf')
        self.file_upload = 0 if not cookies else float('inf')
        self.signin_regex = re.compile(r'"(https://www\.perplexity\.ai/api/auth/callback/email\?callbackUrl=.*?)"')
        self.timestamp = format(random.getrandbits(32), '08x')

        print("[CLI-LOG] GET /api/auth/session ...")
        try:
            resp = await self.session.get('https://www.perplexity.ai/api/auth/session')
            print("[CLI-LOG] /api/auth/session status:", getattr(resp, "status_code", None))
        except Exception as e:
            print("[CLI-LOG] EXCEPTION /api/auth/session:", repr(e))
            import traceback; traceback.print_exc()

    async def create_account(self, cookies):
        '''
        Function to create a new account
        '''
        while True:
            try:
                emailnator_cli = await Emailnator(cookies)

                resp = await self.session.post(
                    'https://www.perplexity.ai/api/auth/signin/email',
                    data={
                        'email': emailnator_cli.email,
                        'csrfToken': self.session.cookies.get_dict()['next-auth.csrf-token'].split('%')[0],
                        'callbackUrl': 'https://www.perplexity.ai/',
                        'json': 'true'
                    }
                )

                if resp.ok:
                    new_msgs = await emailnator_cli.reload(
                        wait_for=lambda x: x['subject'] == 'Sign in to Perplexity',
                        timeout=20
                    )

                    if new_msgs:
                        break
                else:
                    print('Perplexity account creating error:', resp)

            except Exception as e:
                print("[CLI-LOG] EXCEPTION create_account loop:", repr(e))
                pass

        msg = emailnator_cli.get(func=lambda x: x['subject'] == 'Sign in to Perplexity')
        new_account_link = self.signin_regex.search(
            await emailnator_cli.open(msg['messageID'])
        ).group(1)

        await self.session.get(new_account_link)

        self.copilot = 5
        self.file_upload = 10

        return True

    async def search(
        self,
        query,
        mode='auto',
        model=None,
        sources=['web'],
        files={},
        stream=False,
        language='en-US',
        follow_up=None,
        incognito=False
    ):
        '''
        Query function
        '''
        print("\n[CLI-LOG] === search() DIPANGGIL ===")
        print("[CLI-LOG] query:", repr(query))
        print("[CLI-LOG] mode:", mode, "model:", model, "sources:", sources, "stream:", stream)

        assert mode in ['auto', 'pro', 'reasoning', 'deep research'], 'Search modes -> ["auto", "pro", "reasoning", "deep research"]'
        assert model in {
            'auto': [None],
            'pro': [None, 'sonar', 'gpt-5.1', 'claude-4.5-sonnet', 'gemini-2.5-pro', 'grok-4'],
            'reasoning': [None, 'gpt-5.1-thingking', 'claude-4.5-sonnet-thinking', 'gemini-3.0-pro', 'kimi-k2-thinking'],
            'deep research': [None],
            'copilot': [None, 'gemini-3.0-pro' ,'kimi-k2-thinking']
        }[mode] if self.own else True, '''Models for modes -> {
        'auto': [None],
        'pro': [None, 'sonar','gpt-5.1', 'claude-4.5-sonnet', 'gemini-2.5-pro', 'grok-4'],
        'reasoning': [None, 'gpt-5.1-thingking', 'claude-4.5-sonnet-thinking', 'gemini-3.0-pro', 'kimi-k2-thinking'],
        'deep research': [None],
}'''
        assert all([source in ('web', 'scholar', 'social') for source in sources]), 'Sources -> ["web", "scholar", "social"]'
        assert self.copilot > 0 if mode in ['pro', 'reasoning', 'deep research'] else True, 'You have used all of your enhanced (pro) queries'
        assert self.file_upload - len(files) >= 0 if files else True, f'You have tried to upload {len(files)} files but you have {self.file_upload} file upload(s) remaining.'

        print("[CLI-LOG] copilot before:", self.copilot, "file_upload before:", self.file_upload)
        self.copilot = self.copilot - 1 if mode in ['pro', 'reasoning', 'deep research'] else self.copilot
        self.file_upload = self.file_upload - len(files) if files else self.file_upload
        print("[CLI-LOG] copilot after:", self.copilot, "file_upload after:", self.file_upload)

        uploaded_files = []

        # FILE UPLOAD
        for filename, file in files.items():
            print("[CLI-LOG] Upload file:", filename)
            file_type = mimetypes.guess_type(filename)[0]
            print("[CLI-LOG] Detected file_type:", file_type)

            try:
                file_upload_info = (await self.session.post(
                    'https://www.perplexity.ai/rest/uploads/create_upload_url?version=2.18&source=default',
                    json={
                        'content_type': file_type,
                        'file_size': sys.getsizeof(file),
                        'filename': filename,
                        'force_image': False,
                        'source': 'default',
                    }
                )).json()
                print("[CLI-LOG] file_upload_info keys:", list(file_upload_info.keys()))
            except Exception as e:
                print("[CLI-LOG] EXCEPTION create_upload_url:", repr(e))
                import traceback; traceback.print_exc()
                raise

            mp = CurlMime()
            for key, value in file_upload_info['fields'].items():
                mp.addpart(name=key, data=value)
            mp.addpart(name='file', content_type=file_type, filename=filename, data=file)

            upload_resp = await self.session.post(file_upload_info['s3_bucket_url'], multipart=mp)
            print("[CLI-LOG] upload_resp status:", upload_resp.status_code)

            if not upload_resp.ok:
                print("[CLI-LOG] File upload error:", upload_resp)
                raise Exception('File upload error', upload_resp)

            if 'image/upload' in file_upload_info['s3_object_url']:
                uploaded_url = re.sub(
                    r'/private/s--.*?--/v\d+/user_uploads/',
                    '/private/user_uploads/',
                    upload_resp.json()['secure_url']
                )
            else:
                uploaded_url = file_upload_info['s3_object_url']

            print("[CLI-LOG] Uploaded file URL:", uploaded_url)
            uploaded_files.append(uploaded_url)

        # JSON DATA
        json_data = {
            'query_str': query,
            'params': {
                'attachments': uploaded_files + (follow_up['attachments'] if follow_up else []),
                'frontend_context_uuid': str(uuid4()),
                'frontend_uuid': str(uuid4()),
                'is_incognito': incognito,
                'language': language,
                'last_backend_uuid': follow_up['backend_uuid'] if follow_up else None,
                'mode': 'concise' if mode == 'auto' else 'copilot',
                'model_preference': {
                    'auto': {
                        None: 'turbo'
                    },
                    'pro': {
                        None: 'pplx_pro',
                        'sonar': 'experimental',
                        'gpt-5.1': 'gpt51',
                        'claude-4.5-sonnet': 'claude45sonnet',
                        'gemini-2.5-pro': 'gemini25pro',
                        'grok-4': 'grok4'
                    },
                    'reasoning': {
                        None: 'pplx_reasoning',
                        'gpt-5.1-thingking': 'gpt51_thinking',
                        'claude-4.5-sonnet-thinking': 'claude45sonnetthinking',
                        'gemini-3.0-pro': 'gemini30pro',
                        'kimi-k2-thinking': 'kimik2thinking'
                    },
                    'deep research': {
                        None: 'pplx_alpha'
                    }
                }[mode][model],
                'source': 'default',
                'sources': sources,
                'version': '2.18'
            }
        }

        print("[CLI-LOG] JSON data siap, model_preference:", json_data['params']['model_preference'])

        # SSE REQUEST
        print("[CLI-LOG] POST /rest/sse/perplexity_ask ...")
        try:
            resp = await self.session.post(
                'https://www.perplexity.ai/rest/sse/perplexity_ask',
                json=json_data,
                stream=True
            )
        except Exception as e:
            print("[CLI-LOG] EXCEPTION POST perplexity_ask:", repr(e))
            import traceback; traceback.print_exc()
            return {}

        print("[CLI-LOG] POST selesai, status:", getattr(resp, "status_code", None))
        if getattr(resp, "status_code", None) != 200:
            text_preview = ""
            try:
                text_preview = (await resp.aread()).decode("utf-8")[:300]
            except Exception:
                pass
            print("[CLI-LOG] ERROR HTTP:", resp.status_code, "preview:", repr(text_preview))
            return {}

        chunks = []

        async def stream_response(resp):
            print("[CLI-LOG] stream_response() dimulai")
            try:
                async for chunk in resp.aiter_lines(delimiter=b'\r\n\r\n'):
                    print("[CLI-LOG] stream_response: chunk bytes len:", len(chunk))
                    try:
                        content = chunk.decode('utf-8')
                    except Exception as e:
                        print("[CLI-LOG] stream_response: decode error:", repr(e))
                        continue

                    print("[CLI-LOG] stream_response: content preview:", repr(content[:200]))

                    if content.startswith('event: message\r\n'):
                        content_json = json.loads(content[len('event: message\r\ndata: '):])
                        try:
                            if content_json.get('text'):
                                content_json['text'] = json.loads(content_json['text'])
                        except (json.JSONDecodeError, TypeError):
                            pass

                        chunks.append(content_json)
                        print("[CLI-LOG] stream_response: message appended, total chunks:", len(chunks))
                        yield chunks[-1]

                    elif content.startswith('event: end_of_stream\r\n'):
                        print("[CLI-LOG] stream_response: end_of_stream diterima, return")
                        return

            except Exception as e:
                print("[CLI-LOG] EXCEPTION di stream_response:", repr(e))
                import traceback; traceback.print_exc()
                return

        if stream:
            print("[CLI-LOG] stream=True, return async generator")
            return stream_response(resp)

        print("[CLI-LOG] Non-stream mode, mulai baca SSE lines")
        try:
            async for chunk in resp.aiter_lines(delimiter=b'\r\n\r\n'):
                print("[CLI-LOG] Chunk bytes len:", len(chunk))
                try:
                    content = chunk.decode('utf-8')
                except Exception as e:
                    print("[CLI-LOG] Decode error:", repr(e))
                    continue

                print("[CLI-LOG] Content preview:", repr(content[:200]))

                if content.startswith('event: message\r\n'):
                    content_json = json.loads(content[len('event: message\r\ndata: '):])

                    try:
                        if content_json.get('text'):
                            content_json['text'] = json.loads(content_json['text'])
                    except (json.JSONDecodeError, TypeError):
                        pass

                    chunks.append(content_json)
                    print("[CLI-LOG] message event, total chunks:", len(chunks))

                elif content.startswith('event: end_of_stream\r\n'):
                    print("[CLI-LOG] Dapat end_of_stream, return hasil terakhir / {}")
                    return chunks[-1] if chunks else {}
        except Exception as e:
            print("[CLI-LOG] EXCEPTION di loop SSE:", repr(e))
            import traceback; traceback.print_exc()
            print("[CLI-LOG] Fallback return {} karena exception")
            return {}

        print("[CLI-LOG] LOOP SSE SELESAI TANPA end_of_stream, fallback return {}")
        return chunks[-1] if chunks else {}

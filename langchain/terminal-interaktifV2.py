import asyncio
import json
from perplexity_async import Client
from config.cookies.perplexity_cookies import perplexity_cookies
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich.rule import Rule
from rich.align import Align
from datetime import datetime

console = Console()

def extract_answer_from_response(resp):
    """
    Ekstrak jawaban dari response Perplexity API dengan menangani multiple format.
    Support:
      - step-by-step (Claude/GPT) => cari step_type='FINAL'
      - plain text (Grok)
      - Fallback error
    """
    if not resp or 'text' not in resp:
        return "Error: No response from API"

    text_content = resp['text']
    if isinstance(text_content, list):
        try:
            final_step = next((step for step in text_content if isinstance(step, dict) and step.get('step_type') == 'FINAL'), None)
            if final_step and 'content' in final_step:
                content = final_step['content']
                # jawab kl 'answer' ada
                if isinstance(content, dict) and 'answer' in content:
                    answer_content = content['answer']
                    # kadang ini double string json
                    if isinstance(answer_content, str):
                        try:
                            answer_json = json.loads(answer_content)
                            # Claude, Grok format: {"answer": "...", "web_results": [...]}
                            return answer_json.get('answer', str(answer_json))
                        except Exception:
                            return answer_content
                    elif isinstance(answer_content, dict):
                        return answer_content.get('answer', str(answer_content))
                    else:
                        return str(answer_content)
                # fallback ke content string
                return str(content)
            # fallback step terakhir
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
    return f"Error: Unknown text format: {type(text_content)} - {str(text_content)[:100]}"

def show_search_queries(steps):
    """
    Cari step_type==SEARCH_WEB dan tampilkan queries.
    """
    for step in steps:
        if step.get('step_type') == 'SEARCH_WEB':
            queries = []
            if 'content' in step and 'queries' in step['content']:
                queries = step['content']['queries']
            elif 'content' in step and 'queries' not in step['content'] and 'goal_id' in step['content']:  # support variasi lain
                queries = step['content'].get('queries', [])
            if queries:
                console.print("\n[bold cyan]Web Search Queries Used:[/bold cyan]")
                for i, q in enumerate(queries, 1):
                    console.print(f"- [{q.get('engine', '-')}] {q.get('query', '')}")

def show_search_results(steps):
    """
    Cari step_type==SEARCH_RESULTS dan tampilkan web_results (judul, url, snippet)
    """
    for step in steps:
        if step.get('step_type') == 'SEARCH_RESULTS':
            web_results = []
            # Versi dict bisa berbeda, akomodasi dua kemungkinan kunci
            if 'content' in step and 'web_results' in step['content']:
                web_results = step['content']['web_results']
            elif 'web_results_content' in step and 'web_results' in step['web_results_content']:
                web_results = step['web_results_content']['web_results']
            if web_results:
                console.print("\n[bold magenta]Top Web Results:[/bold magenta]")
                for i, r in enumerate(web_results[:6], 1):
                    name = r.get('name', '-')
                    url = r.get('url', '-')
                    snippet = r.get('snippet', '-')
                    console.print(Panel(f"[bold]{i}. {name}[/bold]\n[yellow]{snippet}[/yellow]\n[blue underline]{url}[/blue underline]",
                                        border_style="dim", padding=(0,1)))

def print_header():
    title = Text("🤖 Perplexity AI Terminal", style="bold cyan")
    subtitle = Text("Web Search & AI Answer (Claude CLI style)", style="dim")
    header_panel = Panel(Align.center(Text.assemble(title, "\n", subtitle)),
                         border_style="bright_blue", padding=(1, 2))
    console.print(header_panel)
    console.print(Rule(style="dim"))

def print_footer():
    timestamp = Text(f"Session ended at {datetime.now().strftime('%H:%M:%S')}", style="dim")
    footer_panel = Panel(Align.center(timestamp), border_style="dim", padding=(0, 1))
    console.print(footer_panel)

async def ask_question(perplexity_cli, use_streaming=False):
    print_header()
    while True:
        prompt_text = Text.assemble(
            ("\n┌─", "bright_black"),
            (" Query ", "bold green"),
            ("────────────────────────────────────────────┐\n", "bright_black"),
            ("│ ", "bright_black"),
            ("Enter your question ", "dim"),
            ("(or 'exit' to quit)", "dim italic"),
            ("\n└─> ", "bright_black")
        )
        console.print(prompt_text, end="")
        question = console.input("[bold green]> [/bold green]").strip()
        if question.lower() == 'exit':
            console.print("\n[bold yellow]👋 Thank you! Goodbye![/bold yellow]\n")
            print_footer()
            break
        if not question:
            console.print("[bold red]⚠️  Question cannot be empty![/bold red]")
            continue
        try:
            # non-streaming untuk kejelasan step dan raw
            resp = await perplexity_cli.search(
                question,
                mode="pro",
                model='claude-4.5-sonnet',
                sources=['web'],
                stream=False,
                follow_up=None,
                incognito=True
            )
            all_steps = []
            if hasattr(resp, '__aiter__'):
                full_response = {}
                async for chunk in resp:
                    if isinstance(chunk, dict):
                        if 'text' in chunk and isinstance(chunk['text'], list):
                            all_steps.extend(chunk['text'])
                        for key, value in chunk.items():
                            if key == 'text' and key in full_response:
                                if isinstance(full_response[key], list):
                                    if isinstance(value, list):
                                        full_response[key].extend(value)
                                    else:
                                        full_response[key].append(value)
                                else:
                                    full_response[key] = value
                            else:
                                full_response[key] = value
            elif isinstance(resp, dict):
                if 'text' in resp and isinstance(resp['text'], list):
                    all_steps.extend(resp['text'])
            else:
                console.print(f"[bold red]❌ Error: Unknown response type: {type(resp)}[/bold red]")
                continue

            # tampilkan step search queries dan web result
            show_search_queries(all_steps)
            show_search_results(all_steps)

            # tampilkan jawaban akhir (final answer)
            answer = extract_answer_from_response({'text': all_steps})
            console.print(Rule(title="Final Answer", style="bright_green"))
            # auto tampilkan markdown jika ada code block/nl
            if isinstance(answer, str) and ('```'):
                console.print(Markdown(answer))
            else:
                answer_panel = Panel(answer, border_style="bright_blue", padding=(1,2), title="Answer", title_align="left")
                console.print(answer_panel)
            console.print(Rule(style="bright_green"))
        except Exception as e:
            error_panel = Panel(f"❌ Error processing question: {str(e)}", border_style="red", style="bold red", title="Error")
            console.print(error_panel)
            import traceback
            traceback.print_exc()

async def main():
    console.print("\n[dim]Initializing Perplexity AI Client...[/dim]")
    try:
        perplexity_cli = await Client(perplexity_cookies)
        console.print("[bold green]✓[/bold green] [dim]Client ready![/dim]\n")
        await ask_question(perplexity_cli, use_streaming=False)
    except Exception as e:
        error_panel = Panel(f"Failed to initialize client: {str(e)}", border_style="red", style="bold red", title="Initialization Error")
        console.print(error_panel)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]👋 Program terminated. Goodbye![/bold yellow]\n")
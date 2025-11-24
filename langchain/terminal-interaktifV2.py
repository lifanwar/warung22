import asyncio
import json
import time
from perplexity_async import Client
from config.cookies.perplexity_cookies import perplexity_cookies
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich.rule import Rule
from rich.align import Align
from rich.live import Live
from rich import box
from datetime import datetime

console = Console()

def extract_answer_from_response(resp):
    if not resp or 'text' not in resp:
        return "Error: No response from API"
    text_content = resp['text']
    if isinstance(text_content, list):
        try:
            final_step = next((step for step in text_content if isinstance(step, dict) and step.get('step_type') == 'FINAL'), None)
            if final_step and 'content' in final_step:
                content = final_step['content']
                if isinstance(content, dict) and 'answer' in content:
                    answer_content = content['answer']
                    if isinstance(answer_content, str):
                        try:
                            answer_json = json.loads(answer_content)
                            return answer_json.get('answer', str(answer_json))
                        except Exception:
                            return answer_content
                    elif isinstance(answer_content, dict):
                        return answer_content.get('answer', str(answer_content))
                    else:
                        return str(answer_content)
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
    return f"Error: Unknown text format: {type(text_content)} - {str(text_content)[:100]}"

def show_search_queries(steps):
    for step in steps:
        if step.get('step_type') == 'SEARCH_WEB':
            queries = []
            if 'content' in step and 'queries' in step['content']:
                queries = step['content']['queries']
            elif 'content' in step and 'queries' not in step['content'] and 'goal_id' in step['content']:
                queries = step['content'].get('queries', [])
            if queries:
                console.print("\n[bold cyan]Web Search Queries Used:[/bold cyan]")
                for i, q in enumerate(queries, 1):
                    console.print(f"- [{q.get('engine', '-')}] {q.get('query', '')}")

def show_search_preview_and_wait(steps):
    """
    Tampilkan satu panel preview search web result saat loading.
    """
    for step in steps:
        if step.get('step_type') == 'SEARCH_RESULTS':
            web_results = []
            if 'content' in step and 'web_results' in step['content']:
                web_results = step['content']['web_results']
            if web_results:
                r = web_results[0]
                name = r.get('name', '-')
                url = r.get('url', '-')
                snippet = r.get('snippet', '-')
                console.print(Panel(f"[bold yellow]1. {name}[/bold yellow]\n[yellow]{snippet}[/yellow]\n[blue underline]{url}[/blue underline]",
                                    border_style="bright_magenta", padding=(0,1)))
            break

def show_search_results_simple(steps):
    """
    Tampilkan semua web result sebagai list sederhana saja (tidak pakai panel/box).
    """
    for step in steps:
        if step.get('step_type') == 'SEARCH_RESULTS':
            web_results = []
            if 'content' in step and 'web_results' in step['content']:
                web_results = step['content']['web_results']
            if web_results:
                console.print("\n[bold magenta]Web Sources Used:[/bold magenta]")
                for i, r in enumerate(web_results, 1):
                    name = r.get('name', '-')
                    url = r.get('url', '-')
                    domain = url.split('//')[-1].split('/')[0]
                    # Title cyan, domain kuning, index bold
                    console.print(f"[bold cyan]{i}.[/bold cyan] [white]{name}[/white] [dim]-[/dim] [yellow]{domain}[/yellow]")
            break

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

async def ask_question(perplexity_cli):
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
            # TAHAP 1: Spinner + search preview box  
            with Progress(
                SpinnerColumn("dots"),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Loading initial search web...", total=None)
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
                    async for chunk in resp:
                        if isinstance(chunk, dict):
                            if 'text' in chunk and isinstance(chunk['text'], list):
                                all_steps.extend(chunk['text'])
                elif isinstance(resp, dict):
                    if 'text' in resp and isinstance(resp['text'], list):
                        all_steps.extend(resp['text'])
                else:
                    console.print(f"[bold red]❌ Error: Unknown response type: {type(resp)}[/bold red]")
                    continue
                progress.update(task, description="[magenta]Showing preview result...")
                show_search_preview_and_wait(all_steps)
                time.sleep(1.5)  # biar preview box bisa terbaca, lalu diganti next stage

            # TAHAP 2: Loading final answer + simple web list
            with Progress(
                SpinnerColumn("dots"),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Generating final answer...", total=None)
                time.sleep(0.5)
                show_search_results_simple(all_steps)
                progress.remove_task(task)

            # FINAL ANSWER
            answer = extract_answer_from_response({'text': all_steps})
            console.print(Rule(title="Final Answer", style="bright_green"))
            if isinstance(answer, str) and ('```'):
                console.print(Markdown(answer))
            else:
                console.print(Panel(answer, border_style="bright_blue", padding=(1,2), title="Answer", title_align="left"))
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
        await ask_question(perplexity_cli)
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

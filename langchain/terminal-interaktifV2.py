import asyncio
import json
from perplexity_async import Client
from config.cookies.perplexity_cookies import perplexity_cookies
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.rule import Rule
from rich.live import Live
from rich.align import Align
from datetime import datetime


console = Console()


def extract_answer_from_response(resp):
    """
    Ekstrak jawaban dari response Perplexity API dengan menangani multiple format.
    Support untuk: step-by-step (Claude/GPT), plain text (Grok), dan error fallback.
    """
    if not resp:
        return Text("Error: No response from API", style="bold red")
    
    if 'text' not in resp:
        return Text(f"Error: Missing 'text' field in response. Keys: {list(resp.keys())}", style="bold red")
    
    text_content = resp['text']
    
    if isinstance(text_content, list):
        try:
            final_step = next((step for step in text_content if isinstance(step, dict) and step.get('step_type') == 'FINAL'), None)
            
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
            
            return Text("Error: Empty steps list", style="bold red")
        
        except Exception as e:
            return Text(f"Error parsing steps: {str(e)}", style="bold red")
    
    elif isinstance(text_content, str):
        return text_content
    
    elif isinstance(text_content, dict):
        return str(text_content)
    
    else:
        return Text(f"Error: Unknown text format: {type(text_content)}", style="bold red")


def print_header():
    """Tampilkan header yang menarik"""
    title = Text("🤖 Perplexity AI Terminal", style="bold cyan")
    subtitle = Text("Interactive Research Assistant", style="dim")
    
    header_panel = Panel(
        Align.center(Text.assemble(title, "\n", subtitle)),
        border_style="bright_blue",
        padding=(1, 2)
    )
    
    console.print(header_panel)
    console.print(Rule(style="dim"))


def print_footer():
    """Tampilkan footer"""
    timestamp = Text(f"Session ended at {datetime.now().strftime('%H:%M:%S')}", style="dim")
    footer_panel = Panel(
        Align.center(timestamp),
        border_style="dim",
        padding=(0, 1)
    )
    console.print(footer_panel)


async def ask_question(perplexity_cli, use_streaming=False):
    """Terminal interaktif untuk bertanya ke Perplexity AI"""
    print_header()
    
    while True:
        # Tampilkan prompt interaktif
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
            if use_streaming:
                await handle_streaming_response(perplexity_cli, question)
            else:
                await handle_non_streaming_response(perplexity_cli, question)
            
        except KeyboardInterrupt:
            console.print("\n\n[bold yellow]⏹️  Process cancelled by user.[/bold yellow]")
            continue
            
        except Exception as e:
            error_panel = Panel(
                f"❌ Error processing question: {str(e)}",
                border_style="red",
                style="bold red",
                title="Error"
            )
            console.print(error_panel)
            console.print_exception()


async def handle_streaming_response(perplexity_cli, question):
    """Handle streaming response dengan tampilan real-time yang menarik"""
    # Tampilkan query dalam panel
    query_panel = Panel(
        f"[bold green]Query:[/bold green] {question}",
        border_style="green",
        padding=(1, 2)
    )
    console.print(query_panel)
    
    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        task = progress.add_task("[cyan]Initializing search...", total=None)
        
        resp = await perplexity_cli.search(
            question,
            mode="pro",
            model='claude-4.5-sonnet',
            sources=['web'],
            stream=True,
            follow_up=None,
            incognito=True
        )
        
        step_count = 0
        
        # Container untuk live update
        status_text = Text("")
        
        with Live(status_text, console=console, refresh_per_second=10) as live:
            async for chunk in resp:
                if not isinstance(chunk, dict):
                    continue
                
                step_type = chunk.get('step_type', '')
                step_count += 1
                
                if step_type == 'INITIAL_QUERY':
                    query = chunk.get('content', {}).get('query', '')
                    status_text = Text(f"📝 Processing: '{query}'", style="yellow")
                    progress.update(task, description="[yellow]Analyzing query...")
                    
                elif step_type == 'SEARCH_WEB':
                    status_text = Text("🔍 Searching the web...", style="blue")
                    progress.update(task, description="[blue]Searching web sources...")
                    
                elif step_type == 'SEARCH_RESULTS':
                    results = chunk.get('content', {}).get('web_results', [])
                    status_text = Text(f"📚 Found {len(results)} sources", style="magenta")
                    progress.update(task, description=f"[magenta]Processing {len(results)} results...")
                    
                elif step_type == 'FINAL':
                    status_text = Text("✨ Generating final answer...", style="green")
                    progress.update(task, description="[green]Generating answer...")
                    
                    # Tunggu sebentar agar user bisa lihat status terakhir
                    await asyncio.sleep(0.5)
                    
                else:
                    status_text = Text(f"⚙️ Step {step_count}: {step_type}", style="dim")
        
        # Tampilkan hasil akhir
        console.print("\n")
        console.print(Rule(title="Final Answer", style="bright_green"))
        
        answer = extract_answer_from_response({'text': [chunk]})
        
        # Cek apakah answer mengandung kode
        if isinstance(answer, str) and ('```'):
            # Tampilkan sebagai markdown
            console.print(Markdown(answer))
        else:
            # Tampilkan sebagai text biasa
            answer_panel = Panel(
                answer,
                border_style="bright_blue",
                padding=(1, 2),
                title="Answer",
                title_align="left"
            )
            console.print(answer_panel)
        
        console.print(Rule(style="bright_green"))
        
        # Tampilkan ringkasan
        summary = Text.assemble(
            ("✅ Search completed in ", "dim"),
            (f"{step_count} steps", "bold"),
            (".\n", "dim")
        )
        console.print(summary)


async def handle_non_streaming_response(perplexity_cli, question):
    """Handle non-streaming response dengan tampilan menarik"""
    # Tampilkan query
    query_panel = Panel(
        f"[bold green]Query:[/bold green] {question}",
        border_style="green",
        padding=(1, 2)
    )
    console.print(query_panel)
    
    with Progress(
        SpinnerColumn("dots"),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        task = progress.add_task("[cyan]Processing request...", total=None)
        
        resp = await perplexity_cli.search(
            question,
            mode="pro",
            model='claude-4.5-sonnet',
            sources=['web'],
            stream=False,
            follow_up=None,
            incognito=True
        )
        
        progress.update(task, description="[green]Collecting response...")
        
        final_response = None
        
        if hasattr(resp, '__aiter__'):
            full_response = {}
            async for chunk in resp:
                if isinstance(chunk, dict):
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
            final_response = full_response
        
        elif isinstance(resp, dict):
            final_response = resp
        
        else:
            console.print(f"[bold red]❌ Error: Unknown response type: {type(resp)}[/bold red]")
            return
        
        progress.update(task, description="[green]Rendering answer...")
    
    # Tampilkan hasil
    console.print("\n")
    console.print(Rule(title="Result", style="bright_green"))
    
    answer = extract_answer_from_response(final_response)
    
    if isinstance(answer, Text):
        console.print(Panel(answer, border_style="red"))
    elif isinstance(answer, str):
        if '```' in answer or '    ' in answer:
            console.print(Markdown(answer))
        else:
            answer_panel = Panel(
                answer,
                border_style="bright_blue",
                padding=(1, 2),
                title="Answer",
                title_align="left"
            )
            console.print(answer_panel)
    
    console.print(Rule(style="bright_green"))


async def main():
    """Fungsi utama untuk menjalankan terminal interaktif"""
    console.print("\n[dim]Initializing Perplexity AI Client...[/dim]")
    
    try:
        perplexity_cli = await Client(perplexity_cookies)
        console.print("[bold green]✓[/bold green] [dim]Client ready![/dim]\n")
        
        # Ganti use_streaming=True/False untuk mengubah mode
        await ask_question(perplexity_cli, use_streaming=True)
        
    except Exception as e:
        error_panel = Panel(
            f"Failed to initialize client: {str(e)}",
            border_style="red",
            style="bold red",
            title="Initialization Error"
        )
        console.print(error_panel)
        console.print_exception()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]👋 Program terminated. Goodbye![/bold yellow]\n")
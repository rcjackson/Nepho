#!/usr/bin/env python3
"""
Multi-Model Chatbot CLI
Supports GPT API and Ollama local models with parallel execution.
"""

import asyncio
import click
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich import print as rprint

from chatbot import ParallelChatbot
from config import config
from datastream import DatastreamParseError
from dq_pipeline import DataQualityPipeline, DQReport

console = Console()

@click.group()
def cli():
    """Multi-Model Chatbot - Compare responses from GPT and Ollama models."""
    pass

@cli.command()
@click.option('--prompt', '-p', required=True, help='The prompt/question to ask')
@click.option('--images', '-i', multiple=True, help='Path(s) to image files')
@click.option('--models', '-m', multiple=True, help='Specific models to use (default: all available)')
@click.option('--parallel/--sequential', default=True, help='Run models in parallel or sequentially')
@click.option('--output', '-o', help='Save responses to JSON file')
def chat(prompt: str, images: List[str], models: List[str], parallel: bool, output: Optional[str]):
    """Chat with multiple models and compare responses."""
    asyncio.run(_chat_command(prompt, images, models, parallel, output))

def _build_default_chatbot(models: List[str]) -> Tuple[ParallelChatbot, List[str]]:
    """Build a ParallelChatbot with the requested or default models.

    If no models are specified, adds the default GPT model (when an API key is
    available) and the default Ollama model. Otherwise adds each ``type:name``
    spec (defaulting to ollama when no type prefix is given).

    Returns the chatbot along with the list of model keys it was populated with.
    These keys (the bare model names, without any ``type:`` prefix) are what the
    chatbot stores internally, so callers must use them — not the raw specs —
    when asking the chatbot to run a specific subset of models.
    """
    chatbot = ParallelChatbot()
    model_keys: List[str] = []

    # Add default models if none specified
    if not models:
        # Try to add GPT model
        if config.OPENAI_API_KEY:
            try:
                chatbot.add_model("gpt", config.DEFAULT_GPT_MODEL)
                model_keys.append(config.DEFAULT_GPT_MODEL)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not add GPT model: {e}[/yellow]")

        # Try to add Ollama model
        try:
            chatbot.add_model("ollama", config.DEFAULT_OLLAMA_MODEL)
            model_keys.append(config.DEFAULT_OLLAMA_MODEL)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not add Ollama model: {e}[/yellow]")
    else:
        # Add specified models
        for model_spec in models:
            if ':' in model_spec:
                model_type, model_name = model_spec.split(':', 1)
                chatbot.add_model(model_type, model_name)
            else:
                # Default to ollama if no type specified
                model_type, model_name = "ollama", model_spec
                chatbot.add_model(model_type, model_name)
            model_keys.append(model_name)

    return chatbot, model_keys

async def _chat_command(prompt: str, images: List[str], models: List[str], parallel: bool, output: Optional[str]):
    """Internal chat command implementation."""
    chatbot, model_keys = _build_default_chatbot(models)

    if not chatbot.list_models():
        console.print("[red]Error: No models available![/red]")
        console.print("Make sure you have:")
        console.print("1. Set OPENAI_API_KEY environment variable for GPT models")
        console.print("2. Ollama running with available models")
        return
    
    # Display setup
    console.print(Panel(f"[bold blue]Multi-Model Chatbot[/bold blue]\n"
                       f"Prompt: {prompt}\n"
                       f"Models: {', '.join(chatbot.list_models())}\n"
                       f"Images: {len(images) if images else 'None'}\n"
                       f"Mode: {'Parallel' if parallel else 'Sequential'}"))
    
    # Validate images
    if images:
        valid_images = []
        for img_path in images:
            if Path(img_path).exists():
                valid_images.append(img_path)
            else:
                console.print(f"[yellow]Warning: Image not found: {img_path}[/yellow]")
        images = valid_images
    
    # Run the chat
    try:
        if parallel:
            responses = await chatbot.chat_parallel(prompt, images if images else None, model_keys if models else None)
        else:
            responses = await chatbot.chat_sequential(prompt, images if images else None, model_keys if models else None)
        
        # Display results
        _display_responses(responses)
        
        # Save to file if requested
        if output:
            comparison_data = chatbot.compare_responses()
            with open(output, 'w') as f:
                json.dump(comparison_data, f, indent=2, default=str)
            console.print(f"[green]Responses saved to {output}[/green]")
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

def _display_responses(responses):
    """Display the responses in a formatted table."""
    if not responses:
        console.print("[red]No responses received[/red]")
        return
    
    # Create response table
    table = Table(title="Model Responses Comparison")
    table.add_column("Model", style="cyan", no_wrap=True)
    table.add_column("Response Time", style="green", justify="right")
    table.add_column("Status", style="yellow")
    table.add_column("Response", style="white")
    
    for response in responses:
        status = "✅ Success" if response.error is None else f"❌ {response.error}"
        response_time = f"{response.response_time:.2f}s"
        response_text = response.response[:100] + "..." if len(response.response) > 100 else response.response
        
        table.add_row(
            response.model_name,
            response_time,
            status,
            response_text
        )
    
    console.print(table)
    
    # Display full responses
    console.print("\n[bold]Full Responses:[/bold]")
    for response in responses:
        if response.error is None:
            console.print(Panel(
                response.response,
                title=f"[bold]{response.model_name}[/bold] ({response.response_time:.2f}s)",
                border_style="blue"
            ))
        else:
            console.print(Panel(
                f"Error: {response.error}",
                title=f"[bold red]{response.model_name}[/bold red]",
                border_style="red"
            ))

@cli.command()
def list_models():
    """List available models in Ollama."""
    asyncio.run(_list_models_command())

async def _list_models_command():
    """Internal list models command."""
    try:
        from models.ollama_model import OllamaModel
        ollama = OllamaModel()
        models = await ollama.list_available_models()
        
        if models:
            console.print("[bold green]Available Ollama Models:[/bold green]")
            for model in models:
                console.print(f"  • {model}")
        else:
            console.print("[yellow]No Ollama models found or Ollama is not running[/yellow]")
            console.print("Make sure Ollama is installed and running: https://ollama.ai/")
    
    except Exception as e:
        console.print(f"[red]Error listing models: {e}[/red]")

@cli.command()
@click.argument('model_name')
def pull_model(model_name: str):
    """Pull a model from Ollama."""
    asyncio.run(_pull_model_command(model_name))

async def _pull_model_command(model_name: str):
    """Internal pull model command."""
    try:
        from models.ollama_model import OllamaModel
        ollama = OllamaModel(model_name)
        
        console.print(f"[yellow]Pulling model: {model_name}[/yellow]")
        success = await ollama.pull_model()
        
        if success:
            console.print(f"[green]Successfully pulled model: {model_name}[/green]")
        else:
            console.print(f"[red]Failed to pull model: {model_name}[/red]")
    
    except Exception as e:
        console.print(f"[red]Error pulling model: {e}[/red]")

@cli.command()
@click.argument('datastream')
@click.option('--start', '-s', required=True, help='Start date YYYY-MM-DD (inclusive)')
@click.option('--end', '-e', help='End date YYYY-MM-DD (inclusive; default: same as start)')
@click.option('--models', '-m', multiple=True, help='Specific models to use (default: all available)')
@click.option('--output', '-o', help='Save the DQ report to a JSON file')
@click.option('--max-images', type=int, default=None,
              help='Max quicklook images per day (default: config value)')
@click.option('--cache/--no-cache', default=False,
              help='Cache downloaded quicklook images per day for reuse on later runs')
@click.option('--cache-dir', default=None,
              help='Custom picture cache directory (implies --cache)')
@click.option('--refresh-cache', is_flag=True, default=False,
              help='Re-download images even when a cached copy exists')
def dq(datastream: str, start: str, end: Optional[str], models: List[str],
       output: Optional[str], max_images: Optional[int], cache: bool,
       cache_dir: Optional[str], refresh_cache: bool):
    """Assess data quality of a datastream's quicklook images via LLM(s)."""
    asyncio.run(_dq_command(datastream, start, end, models, output, max_images,
                            cache, cache_dir, refresh_cache))

async def _dq_command(datastream: str, start: str, end: Optional[str], models: List[str],
                      output: Optional[str], max_images: Optional[int],
                      cache: bool = False, cache_dir: Optional[str] = None,
                      refresh_cache: bool = False):
    """Internal data quality command implementation."""
    # Parse and validate the date window.
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date() if end else start_date
    except ValueError:
        console.print("[red]Error: dates must be in YYYY-MM-DD format[/red]")
        return

    if end_date < start_date:
        console.print("[red]Error: --end must not be before --start[/red]")
        return

    chatbot, model_keys = _build_default_chatbot(models)
    if not chatbot.list_models():
        console.print("[red]Error: No models available![/red]")
        console.print("Make sure you have:")
        console.print("1. Set OPENAI_API_KEY environment variable for GPT models")
        console.print("2. Ollama running with available models")
        return

    # Resolve the effective cache directory: an explicit --cache-dir implies
    # caching; otherwise --cache enables it at the configured default location.
    effective_cache_dir = cache_dir or (config.DQ_CACHE_DIR if cache else None)

    # Build the pipeline (this parses the datastream name).
    try:
        pipeline = DataQualityPipeline(
            chatbot, datastream, model_keys if models else None,
            max_images=max_images, cache_dir=effective_cache_dir,
            refresh_cache=refresh_cache,
        )
    except DatastreamParseError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    if effective_cache_dir:
        cache_line = f"\nCache: {effective_cache_dir}" + (
            " (refreshing)" if refresh_cache else "")
    else:
        cache_line = ""

    console.print(Panel(f"[bold blue]Nepho Data Quality Check[/bold blue]\n"
                        f"Datastream: {datastream}\n"
                        f"Window: {start_date} to {end_date}\n"
                        f"Models: {', '.join(chatbot.list_models())}"
                        f"{cache_line}"))

    try:
        report = await pipeline.run(start_date, end_date)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    _display_dq_report(report)

    if output:
        with open(output, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        console.print(f"[green]DQ report saved to {output}[/green]")

_SEVERITY_STYLES = {
    "Good": "green",
    "Indeterminate": "yellow",
    "Bad": "red",
}

def _display_dq_report(report: DQReport):
    """Display the DQ report as per-day tables mirroring chat output."""
    if not report.days:
        console.print("[yellow]No days processed[/yellow]")
        return

    for day_result in report.days:
        if day_result.skipped:
            style = "red" if day_result.fetch_error else "dim"
            console.print(f"[{style}]{day_result.day}: {day_result.note}[/{style}]")
            continue

        cached_label = " (cached)" if day_result.from_cache else ""
        table = Table(title=f"Data Quality - {day_result.day} "
                            f"({day_result.image_count} image(s)){cached_label}")
        table.add_column("Model", style="cyan", no_wrap=True)
        table.add_column("Issues?", justify="center")
        table.add_column("Severity")
        table.add_column("Time", style="green", justify="right")
        table.add_column("Summary", style="white")

        for verdict in day_result.verdicts:
            if verdict.error is not None:
                table.add_row(
                    verdict.model_name,
                    "[red]error[/red]",
                    "-",
                    f"{verdict.response_time:.2f}s",
                    f"[red]{verdict.error}[/red]",
                )
                continue

            if verdict.issues_found is True:
                issues = "[red]yes[/red]"
            elif verdict.issues_found is False:
                issues = "[green]no[/green]"
            else:
                issues = "[yellow]?[/yellow]"

            severity = verdict.severity or "-"
            style = _SEVERITY_STYLES.get(verdict.severity, "white")
            severity_text = f"[{style}]{severity}[/{style}]"

            summary = verdict.summary or ""
            if len(summary) > 200:
                summary = summary[:200] + "..."

            table.add_row(
                verdict.model_name,
                issues,
                severity_text,
                f"{verdict.response_time:.2f}s",
                summary,
            )

        console.print(table)

        # Show the detailed issue lists below the table.
        for verdict in day_result.verdicts:
            if verdict.error is None and verdict.issues:
                bullets = "\n".join(f"• {issue}" for issue in verdict.issues)
                console.print(Panel(
                    bullets,
                    title=f"[bold]{verdict.model_name}[/bold] - issues ({day_result.day})",
                    border_style="yellow",
                ))

if __name__ == '__main__':
    cli()

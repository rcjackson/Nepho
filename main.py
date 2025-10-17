#!/usr/bin/env python3
"""
Multi-Model Chatbot CLI
Supports GPT API and Ollama local models with parallel execution.
"""

import asyncio
import click
import json
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich import print as rprint

from chatbot import ParallelChatbot
from config import config

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

async def _chat_command(prompt: str, images: List[str], models: List[str], parallel: bool, output: Optional[str]):
    """Internal chat command implementation."""
    chatbot = ParallelChatbot()
    
    # Add default models if none specified
    if not models:
        # Try to add GPT model
        if config.OPENAI_API_KEY:
            try:
                chatbot.add_model("gpt", config.DEFAULT_GPT_MODEL)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not add GPT model: {e}[/yellow]")
        
        # Try to add Ollama model
        try:
            chatbot.add_model("ollama", config.DEFAULT_OLLAMA_MODEL)
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
                chatbot.add_model("ollama", model_spec)
    
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
            responses = await chatbot.chat_parallel(prompt, images if images else None, models if models else None)
        else:
            responses = await chatbot.chat_sequential(prompt, images if images else None, models if models else None)
        
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

if __name__ == '__main__':
    cli()

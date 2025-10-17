#!/usr/bin/env python3
"""
Setup script for the Multi-Model Chatbot
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.8+."""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✓ Python version: {sys.version.split()[0]}")
    return True

def install_requirements():
    """Install required packages."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install requirements: {e}")
        return False

def check_environment():
    """Check environment variables."""
    print("\nChecking environment variables...")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        print("✓ OPENAI_API_KEY is set")
    else:
        print("⚠ OPENAI_API_KEY is not set (required for GPT models)")
        print("  Set it with: export OPENAI_API_KEY='your_key_here'")
    
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    print(f"✓ OLLAMA_BASE_URL: {ollama_url}")

def check_ollama():
    """Check if Ollama is available."""
    try:
        import requests
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        if response.status_code == 200:
            print("✓ Ollama is running")
            return True
        else:
            print("⚠ Ollama is not responding properly")
            return False
    except Exception as e:
        print(f"⚠ Ollama check failed: {e}")
        print("  Make sure Ollama is installed and running: https://ollama.ai/")
        return False

def create_env_example():
    """Create .env.example file."""
    env_example = """# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434

# Default models to use
DEFAULT_GPT_MODEL=gpt-4-vision-preview
DEFAULT_OLLAMA_MODEL=llava

# Image processing settings
MAX_IMAGE_SIZE_MB=10
SUPPORTED_IMAGE_FORMATS=jpg,jpeg,png,gif,bmp,webp

# Parallel processing settings
MAX_CONCURRENT_MODELS=3
REQUEST_TIMEOUT=60
"""
    
    with open(".env.example", "w") as f:
        f.write(env_example)
    print("✓ Created .env.example file")

def main():
    """Main setup function."""
    print("🚀 Setting up Multi-Model Chatbot...")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install requirements
    if not install_requirements():
        return False
    
    # Create .env.example
    create_env_example()
    
    # Check environment
    check_environment()
    
    # Check Ollama
    check_ollama()
    
    print("\n" + "=" * 50)
    print("✅ Setup completed!")
    print("\nNext steps:")
    print("1. Set your OPENAI_API_KEY environment variable")
    print("2. Start Ollama: ollama serve")
    print("3. Pull some models: ollama pull llava")
    print("4. Test the chatbot: python main.py chat --prompt 'Hello world'")
    print("\nFor more information, see README.md")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

# Multi-Model Chatbot

A powerful chatbot that supports both GPT (via OpenAI API) and local models (via Ollama) with parallel execution for response comparison.

## Features

- 🤖 **Multi-Model Support**: GPT API and Ollama local models
- 🖼️ **Image Processing**: Analyze images with vision-capable models
- ⚡ **Parallel Execution**: Run multiple models simultaneously for comparison
- 📊 **Response Comparison**: Compare responses side-by-side with timing metrics
- 🎯 **Flexible Configuration**: Easy setup with environment variables
- 💻 **CLI Interface**: User-friendly command-line interface
- 🔧 **Extensible**: Easy to add new model types

## Installation

### Prerequisites

1. **Python 3.8+**
2. **OpenAI API Key** (for GPT models)
3. **Ollama** (for local models) - [Install Ollama](https://ollama.ai/)

### Setup

1. Clone or download this repository:
```bash
git clone <repository-url>
cd chatbot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# Create .env file (optional, you can also set environment variables directly)
export OPENAI_API_KEY="your_openai_api_key_here"
export OLLAMA_BASE_URL="http://localhost:11434"  # Default Ollama URL
```

4. Install and start Ollama (if using local models):
```bash
# Install Ollama from https://ollama.ai/
ollama serve
```

5. Pull some Ollama models:
```bash
# Vision-capable model
ollama pull llava

# Text-only model
ollama pull llama2

# Or use the built-in command
python main.py pull-model llava
```

## Usage

### Command Line Interface

#### Basic Chat
```bash
# Chat with all available models
python main.py chat --prompt "Explain quantum computing"

# Chat with specific models
python main.py chat --prompt "What is AI?" --models gpt:gpt-4-vision-preview ollama:llava

# Chat with images
python main.py chat --prompt "What's in this image?" --images photo1.jpg photo2.png

# Run models sequentially instead of parallel
python main.py chat --prompt "Hello world" --sequential

# Save responses to file
python main.py chat --prompt "Explain machine learning" --output responses.json
```

#### Model Management
```bash
# List available Ollama models
python main.py list-models

# Pull a new model
python main.py pull-model llama2
```

### Python API

```python
import asyncio
from chatbot import ParallelChatbot

async def main():
    # Create chatbot
    chatbot = ParallelChatbot()
    
    # Add models
    chatbot.add_model("gpt", "gpt-4-vision-preview")
    chatbot.add_model("ollama", "llava")
    
    # Chat with parallel execution
    responses = await chatbot.chat_parallel(
        prompt="What is machine learning?",
        images=["image.jpg"]  # Optional
    )
    
    # Process responses
    for response in responses:
        print(f"{response.model_name}: {response.response}")
        print(f"Response time: {response.response_time:.2f}s")

# Run the example
asyncio.run(main())
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for GPT models | Required |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `DEFAULT_GPT_MODEL` | Default GPT model | `gpt-4-vision-preview` |
| `DEFAULT_OLLAMA_MODEL` | Default Ollama model | `llava` |
| `MAX_CONCURRENT_MODELS` | Max parallel models | `3` |
| `REQUEST_TIMEOUT` | Request timeout (seconds) | `60` |
| `MAX_IMAGE_SIZE_MB` | Max image size | `10` |

### Supported Image Formats

- JPEG/JPG
- PNG
- GIF
- BMP
- WebP

### Vision-Capable Models

**GPT Models:**
- `gpt-4-vision-preview`
- `gpt-4o` (when available)

**Ollama Models:**
- `llava`
- `bakllava`
- `moondream`
- `minicpm-v`
- `llava-llama2`
- `llava-llama3`

## Examples

### Text Analysis
```bash
python main.py chat --prompt "Compare Python and JavaScript programming languages"
```

### Image Analysis
```bash
python main.py chat --prompt "Describe this image in detail" --images photo.jpg
```

### Model Comparison
```bash
python main.py chat --prompt "Write a short story about a robot" --models ollama:llava ollama:llama2
```

### Save Results
```bash
python main.py chat --prompt "Explain blockchain technology" --output blockchain_analysis.json
```

## Response Format

The chatbot returns structured responses with:

```json
{
  "total_models": 2,
  "successful_responses": 2,
  "failed_responses": 0,
  "average_response_time": 3.45,
  "fastest_model": "gpt-4-vision-preview",
  "responses": {
    "gpt-4-vision-preview": {
      "response": "GPT response text...",
      "response_time": 2.1,
      "error": null,
      "timestamp": "2024-01-01T12:00:00"
    },
    "llava": {
      "response": "Ollama response text...",
      "response_time": 4.8,
      "error": null,
      "timestamp": "2024-01-01T12:00:00"
    }
  }
}
```

## Troubleshooting

### Common Issues

1. **"No models available"**
   - Check if `OPENAI_API_KEY` is set
   - Ensure Ollama is running: `ollama serve`
   - Verify models are pulled: `ollama list`

2. **"Error calling Ollama API"**
   - Check if Ollama is running on the correct port
   - Verify the model exists: `python main.py list-models`
   - Try pulling the model: `python main.py pull-model model-name`

3. **"Invalid image"**
   - Check image file exists and is readable
   - Verify image format is supported
   - Ensure image size is under the limit (10MB default)

4. **Slow responses**
   - Reduce `MAX_CONCURRENT_MODELS` in config
   - Use smaller models for faster responses
   - Check your internet connection for API models

### Performance Tips

- Use parallel execution for better performance
- Limit concurrent models to avoid overwhelming your system
- Use appropriate model sizes for your hardware
- Cache responses for repeated queries

## Development

### Adding New Model Types

1. Create a new model class inheriting from `BaseModel`
2. Implement the `chat` method
3. Add the model type to the `ParallelChatbot.add_model` method
4. Update the CLI to support the new model type

### Running Tests

```bash
# Run the example
python example.py

# Test specific functionality
python -c "from chatbot import ParallelChatbot; print('Import successful')"
```

## License

This project is open source. Feel free to modify and distribute according to your needs.

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

---

**Happy Chatting! 🤖💬**

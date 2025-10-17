#!/usr/bin/env python3
"""
Example usage of the Multi-Model Chatbot
"""

import asyncio
from chatbot import ParallelChatbot

async def main():
    """Example usage of the chatbot."""
    # Create chatbot instance
    chatbot = ParallelChatbot()
    
    # Add models
    print("Adding models...")
    
    # Add GPT model (requires OPENAI_API_KEY environment variable)
    try:
        chatbot.add_model("gpt", "gpt-4-vision-preview")
        print("✓ Added GPT model")
    except Exception as e:
        print(f"✗ Failed to add GPT model: {e}")
    
    # Add Ollama models
    try:
        chatbot.add_model("ollama", "llava")
        print("✓ Added Ollama LLaVA model")
    except Exception as e:
        print(f"✗ Failed to add Ollama LLaVA model: {e}")
    
    try:
        chatbot.add_model("ollama", "llama2")
        print("✓ Added Ollama Llama2 model")
    except Exception as e:
        print(f"✗ Failed to add Ollama Llama2 model: {e}")
    
    # List available models
    print(f"\nAvailable models: {chatbot.list_models()}")
    
    if not chatbot.list_models():
        print("No models available. Please check your configuration.")
        return
    
    # Example 1: Text-only prompt
    print("\n" + "="*50)
    print("Example 1: Text-only prompt")
    print("="*50)
    
    prompt = "Explain the concept of machine learning in simple terms."
    responses = await chatbot.chat_parallel(prompt)
    
    print(f"\nPrompt: {prompt}")
    print(f"Models used: {[r.model_name for r in responses]}")
    
    for response in responses:
        print(f"\n--- {response.model_name} ({response.response_time:.2f}s) ---")
        if response.error:
            print(f"Error: {response.error}")
        else:
            print(response.response[:200] + "..." if len(response.response) > 200 else response.response)
    
    # Example 2: Image analysis (if images are available)
    print("\n" + "="*50)
    print("Example 2: Image analysis")
    print("="*50)
    
    # You can add your own image path here
    image_path = "example_image.jpg"  # Replace with actual image path
    
    import os
    if os.path.exists(image_path):
        prompt = "What do you see in this image? Describe it in detail."
        responses = await chatbot.chat_parallel(prompt, [image_path])
        
        print(f"\nPrompt: {prompt}")
        print(f"Image: {image_path}")
        
        for response in responses:
            print(f"\n--- {response.model_name} ({response.response_time:.2f}s) ---")
            if response.error:
                print(f"Error: {response.error}")
            else:
                print(response.response[:300] + "..." if len(response.response) > 300 else response.response)
    else:
        print(f"Image {image_path} not found. Skipping image analysis example.")
    
    # Example 3: Compare responses
    print("\n" + "="*50)
    print("Example 3: Response comparison")
    print("="*50)
    
    comparison = chatbot.compare_responses()
    print(f"Total models: {comparison['total_models']}")
    print(f"Successful responses: {comparison['successful_responses']}")
    print(f"Failed responses: {comparison['failed_responses']}")
    print(f"Average response time: {comparison['average_response_time']:.2f}s")
    print(f"Fastest model: {comparison['fastest_model']}")

if __name__ == "__main__":
    asyncio.run(main())

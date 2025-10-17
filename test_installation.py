#!/usr/bin/env python3
"""
Quick test to verify the chatbot installation works
"""

def test_imports():
    """Test that all modules can be imported."""
    try:
        from config import config
        print("✓ Config module imported successfully")
        
        from models.base_model import BaseModel
        print("✓ Base model imported successfully")
        
        from models.gpt_model import GPTModel
        print("✓ GPT model imported successfully")
        
        from models.ollama_model import OllamaModel
        print("✓ Ollama model imported successfully")
        
        from chatbot import ParallelChatbot
        print("✓ Parallel chatbot imported successfully")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_config():
    """Test configuration loading."""
    try:
        from config import config
        print(f"✓ Config loaded - Ollama URL: {config.OLLAMA_BASE_URL}")
        print(f"✓ Default GPT model: {config.DEFAULT_GPT_MODEL}")
        print(f"✓ Default Ollama model: {config.DEFAULT_OLLAMA_MODEL}")
        return True
    except Exception as e:
        print(f"✗ Config error: {e}")
        return False

def test_chatbot_creation():
    """Test chatbot instance creation."""
    try:
        from chatbot import ParallelChatbot
        chatbot = ParallelChatbot()
        print("✓ Chatbot instance created successfully")
        print(f"✓ Available models: {chatbot.list_models()}")
        return True
    except Exception as e:
        print(f"✗ Chatbot creation error: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Multi-Model Chatbot Installation")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("Config Test", test_config),
        ("Chatbot Creation Test", test_chatbot_creation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Installation is working correctly.")
        print("\nYou can now:")
        print("1. Set your OPENAI_API_KEY environment variable")
        print("2. Start Ollama: ollama serve")
        print("3. Test with: python main.py chat --prompt 'Hello world'")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False
    
    return True

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)

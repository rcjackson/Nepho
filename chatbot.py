import asyncio
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import time

from models import BaseModel, GPTModel, OllamaModel
from config import config

@dataclass
class ChatResponse:
    """Response from a model with metadata."""
    model_name: str
    response: str
    response_time: float
    timestamp: datetime
    error: Optional[str] = None

class ParallelChatbot:
    """Chatbot that can run multiple models in parallel for comparison."""
    
    def __init__(self):
        self.models: Dict[str, BaseModel] = {}
        self.responses: List[ChatResponse] = []
    
    def add_model(self, model_type: str, model_name: str, **kwargs) -> None:
        """Add a model to the chatbot."""
        try:
            if model_type.lower() == "gpt":
                model = GPTModel(model_name, **kwargs)
            elif model_type.lower() == "ollama":
                model = OllamaModel(model_name, **kwargs)
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
            
            self.models[model_name] = model
            print(f"Added {model_type} model: {model_name}")
            
        except Exception as e:
            print(f"Failed to add {model_type} model {model_name}: {e}")
    
    def remove_model(self, model_name: str) -> None:
        """Remove a model from the chatbot."""
        if model_name in self.models:
            del self.models[model_name]
            print(f"Removed model: {model_name}")
        else:
            print(f"Model {model_name} not found")
    
    def list_models(self) -> List[str]:
        """List all available models."""
        return list(self.models.keys())
    
    async def chat_single(self, model_name: str, prompt: str, images: Optional[List[str]] = None) -> ChatResponse:
        """Chat with a single model."""
        if model_name not in self.models:
            return ChatResponse(
                model_name=model_name,
                response="",
                response_time=0.0,
                timestamp=datetime.now(),
                error=f"Model {model_name} not found"
            )
        
        model = self.models[model_name]
        start_time = time.time()
        
        try:
            response_text = await model.chat(prompt, images)
            response_time = time.time() - start_time
            
            return ChatResponse(
                model_name=model_name,
                response=response_text,
                response_time=response_time,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return ChatResponse(
                model_name=model_name,
                response="",
                response_time=response_time,
                timestamp=datetime.now(),
                error=str(e)
            )
    
    async def chat_parallel(self, prompt: str, images: Optional[List[str]] = None, 
                          model_names: Optional[List[str]] = None) -> List[ChatResponse]:
        """Chat with multiple models in parallel."""
        if not self.models:
            return [ChatResponse(
                model_name="none",
                response="",
                response_time=0.0,
                timestamp=datetime.now(),
                error="No models available"
            )]
        
        # Filter models if specific ones are requested
        if model_names:
            available_models = [name for name in model_names if name in self.models.keys()]
        else:
            available_models = list(self.models.keys())
        
        if not available_models:
            return [ChatResponse(
                model_name="none",
                response="",
                response_time=0.0,
                timestamp=datetime.now(),
                error="No available models match the request"
            )]
        
        # Limit concurrent models to avoid overwhelming the system
        max_concurrent = min(len(available_models), config.MAX_CONCURRENT_MODELS)
        
        print(f"Running {len(available_models)} models in parallel (max {max_concurrent} concurrent)...")
        
        # Create tasks for parallel execution
        tasks = []
        for model_name in available_models:
            task = asyncio.create_task(self.chat_single(model_name, prompt, images))
            tasks.append(task)
        
        # Execute tasks with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_chat(model_name: str, prompt: str, images: Optional[List[str]]):
            async with semaphore:
                return await self.chat_single(model_name, prompt, images)
        
        limited_tasks = []
        for model_name in available_models:
            task = asyncio.create_task(limited_chat(model_name, prompt, images))
            limited_tasks.append(task)
        
        # Wait for all tasks to complete
        responses = await asyncio.gather(*limited_tasks, return_exceptions=True)
        
        # Filter out exceptions and convert to ChatResponse objects
        valid_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                valid_responses.append(ChatResponse(
                    model_name=available_models[i],
                    response="",
                    response_time=0.0,
                    timestamp=datetime.now(),
                    error=str(response)
                ))
            else:
                valid_responses.append(response)
        
        self.responses = valid_responses
        return valid_responses
    
    async def chat_sequential(self, prompt: str, images: Optional[List[str]] = None,
                            model_names: Optional[List[str]] = None) -> List[ChatResponse]:
        """Chat with multiple models sequentially."""
        if not self.models:
            return [ChatResponse(
                model_name="none",
                response="",
                response_time=0.0,
                timestamp=datetime.now(),
                error="No models available"
            )]
        
        # Filter models if specific ones are requested
        if model_names:
            available_models = [name for name in model_names if name in self.models]
        else:
            available_models = list(self.models.keys())
        print(model_names, available_models)
        if not available_models:
            return [ChatResponse(
                model_name="none",
                response="",
                response_time=0.0,
                timestamp=datetime.now(),
                error="No available models match the request"
            )]
        
        print(f"Running {len(available_models)} models sequentially...")
        
        responses = []
        for model_name in available_models:
            response = await self.chat_single(model_name, prompt, images)
            responses.append(response)
        
        self.responses = responses
        return responses
    
    def get_last_responses(self) -> List[ChatResponse]:
        """Get the last set of responses."""
        return self.responses
    
    def compare_responses(self) -> Dict[str, any]:
        """Compare the last set of responses."""
        if not self.responses:
            return {"error": "No responses to compare"}
        
        # Basic comparison metrics
        comparison = {
            "total_models": len(self.responses),
            "successful_responses": len([r for r in self.responses if r.error is None]),
            "failed_responses": len([r for r in self.responses if r.error is not None]),
            "average_response_time": sum(r.response_time for r in self.responses if r.error is None) / 
                                   max(1, len([r for r in self.responses if r.error is None])),
            "fastest_model": min(self.responses, key=lambda r: r.response_time).model_name if self.responses else None,
            "responses": {}
        }
        
        for response in self.responses:
            comparison["responses"][response.model_name] = {
                "response": response.response,
                "response_time": response.response_time,
                "error": response.error,
                "timestamp": response.timestamp.isoformat()
            }
        
        return comparison

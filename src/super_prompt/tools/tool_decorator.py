"""
Decorator-based tool registration system.
"""
from typing import Dict, List, Callable, Any

# Global registries
TOOL_REGISTRY: Dict[str, Callable] = {}
TOOL_SCHEMAS: List[Dict[str, Any]] = []
TOOL_COMPLEXITY: Dict[str, str] = {}

def tool(
    description: str,
    parameters: Dict[str, Any],
    required: List[str],
    complexity: str = "simple"
):
    """
    A decorator to register a function as a tool for the AI agent.

    Args:
        description: A clear description of what the tool does.
        parameters: A dictionary defining the tool's parameters, following the OpenAI schema.
        required: A list of required parameter names.
        complexity: "simple" or "complex", to determine which AI model to use.
    """
    def decorator(func: Callable):
        name = func.__name__
        
        # Register the function, its complexity, and its schema
        TOOL_REGISTRY[name] = func
        TOOL_COMPLEXITY[name] = complexity
        TOOL_SCHEMAS.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required
                }
            }
        })
        
        # Return the original function without modification
        return func
    return decorator

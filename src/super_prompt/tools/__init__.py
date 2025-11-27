"""
Tool Aggregator for the Modern AI Agent.

This module imports all tool functions from the segmented files and provides a
function to get a dictionary of ready-to-use tools with their dependencies (like code_agent)
already bound.
"""
import functools
import inspect
from pathlib import Path
from typing import Dict, Callable, Any

from ..code_agent import CodeAgent

# Import all tool functions from the segmented files.
# The act of importing executes the @tool decorators, populating the global registries.
from .file_system import *
from .code_editing import *
from .shell import *
from .code_analysis import *
from .cognitive import *  # Meta-ferramentas cognitivas (complex)

# Import the global registries from the decorator module
from .tool_decorator import TOOL_REGISTRY, TOOL_SCHEMAS, TOOL_COMPLEXITY

def get_all_tools(code_agent: CodeAgent, workspace: Path) -> Dict[str, Callable[..., Any]]:
    """
    Initializes and returns a dictionary of all registered tools.

    This function binds the necessary context (code_agent, workspace) to each
    tool function that requires it. It intelligently checks which parameters
    each function accepts before binding.

    Args:
        code_agent: An instance of the CodeAgent for file manipulation.
        workspace: The Path object representing the agent's workspace.

    Returns:
        A dictionary mapping tool names to their callable functions.
    """
    
    # Create a new dictionary to hold the bound tools
    bound_tools: Dict[str, Callable[..., Any]] = {}

    for name, func in TOOL_REGISTRY.items():
        # Get the function signature to see which parameters it accepts
        sig = inspect.signature(func)
        params = sig.parameters
        
        # Build kwargs based on what the function actually accepts
        kwargs = {}
        if 'code_agent' in params:
            kwargs['code_agent'] = code_agent
        if 'workspace' in params:
            kwargs['workspace'] = workspace
        
        # Create a partial function with only the parameters the function accepts
        if kwargs:
            bound_tools[name] = functools.partial(func, **kwargs)
        else:
            # If the function doesn't need any of our context, use it as-is
            bound_tools[name] = func
        
    return bound_tools

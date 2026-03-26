'''
Utility functions for discovering and managing AI utility functions
'''

import os
import importlib
import inspect
from pathlib import Path


def discover_utility_functions():
    """
    Discover all available utility functions in the ai_utils directory.
    
    Returns:
        list: List of tuples (function_path, display_name) for use in model choices
    """
    utility_functions = []
    ai_utils_dir = Path(__file__).parent
    
    # Iterate through all Python files in ai_utils directory
    for file_path in ai_utils_dir.glob('*.py'):
        # Skip __init__.py and utils.py itself
        if file_path.name in ['__init__.py', 'utils.py']:
            continue
        
        module_name = file_path.stem
        try:
            # Import the module
            module = importlib.import_module(f'promapp.ai_utils.{module_name}')
            
            # Find all callable functions in the module
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                # Skip private functions
                if name.startswith('_'):
                    continue
                
                # Build the full import path
                function_path = f'promapp.ai_utils.{module_name}.{name}'
                
                # Create a display name from the function name
                display_name = f'{module_name}.{name}'
                
                # Get docstring first line if available
                if obj.__doc__:
                    first_line = obj.__doc__.strip().split('\n')[0]
                    display_name = f'{display_name} - {first_line}'
                
                utility_functions.append((function_path, display_name))
        
        except Exception:
            # Skip modules that can't be imported
            continue
    
    return sorted(utility_functions, key=lambda x: x[0])


def get_utility_function_choices():
    """
    Get choices for the utility_function_path field.
    
    Returns:
        list: List of tuples (value, label) for Django field choices
    """
    return discover_utility_functions()

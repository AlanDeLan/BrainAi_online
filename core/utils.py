"""
Utility functions for Local Brain.
Common functions used across the project.
"""
import os
import sys


def resource_path(relative_path: str) -> str:
    """
    Get correct path to resources for PyInstaller.
    
    Args:
        relative_path: Relative path to resource
        
    Returns:
        Absolute path to resource
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates temporary folder in _MEIPASS
        base_path = sys._MEIPASS
    else:
        # Normal mode - use current directory
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_base_directory() -> str:
    """
    Get base directory (next to exe or project root) with PyInstaller support.
    
    Returns:
        Base directory path
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller: search next to exe file
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))
    else:
        return os.getcwd()


def get_base_dir() -> str:
    """
    Alias for get_base_directory() for backward compatibility.
    
    Returns:
        Base directory path
    """
    return get_base_directory()





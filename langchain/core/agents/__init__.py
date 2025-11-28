# core/agents/__init__.py
"""
AI Agents for Warung22
"""

from core.agents.menu_agent import MenuAgent, create_menu_agent
from core.agents.crud_agent import CRUDAgent, create_crud_agent

__all__ = [
    'MenuAgent',
    'create_menu_agent',
    'CRUDAgent',
    'create_crud_agent',
]

"""
Core package initialization.
Exports bot instance, event setup, and shutdown handler.
"""

from core.bot_instance import bot, get_bot
from core.events import setup_events
from core.shutdown_handler import setup_shutdown_handlers, ShutdownHandler

__all__ = [
    'bot',
    'get_bot',
    'setup_events',
    'setup_shutdown_handlers',
    'ShutdownHandler',
]
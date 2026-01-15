"""
Permission checking utilities for Discord commands.
Provides common permission validation patterns.
"""
import discord
from typing import Optional, Tuple

from config.constants import MSG_SERVER_ONLY, MSG_ADMIN_ONLY


def check_admin_permission(interaction: discord.Interaction) -> Tuple[bool, Optional[str]]:
    """
    Check if user has admin permissions in the guild.
    
    Args:
        interaction: Discord interaction object
        
    Returns:
        Tuple of (has_permission, error_message)
        error_message is None if user has permission
    """
    # Check if in a guild (not DM)
    if not interaction.guild:
        return False, MSG_SERVER_ONLY
    
    # Check if user exists (should always be true, but safety check)
    if not interaction.user:
        return False, MSG_ADMIN_ONLY
    
    # Check admin permissions
    if not interaction.user.guild_permissions.administrator:
        return False, MSG_ADMIN_ONLY
    
    return True, None


def is_guild_admin(interaction: discord.Interaction) -> bool:
    """
    Check if the user has admin permissions (simple boolean version).
    
    Args:
        interaction: Discord interaction object
        
    Returns:
        True if user has admin permissions
    """
    has_permission, _ = check_admin_permission(interaction)
    return has_permission


def require_guild_context(interaction: discord.Interaction) -> Tuple[bool, Optional[str]]:
    """
    Check if interaction is in a guild context (not a DM).
    
    Args:
        interaction: Discord interaction object
        
    Returns:
        Tuple of (is_in_guild, error_message)
        error_message is None if in guild
    """
    if not interaction.guild:
        return False, MSG_SERVER_ONLY
    
    return True, None

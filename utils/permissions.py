"""
Permission checking utilities for Discord commands.
Provides common permission validation patterns with bot-specific roles.
"""
import discord
from typing import Optional, Tuple
import logging
import os

from config.constants import MSG_SERVER_ONLY, MSG_ADMIN_ONLY

logger = logging.getLogger(__name__)

# Bot owner IDs (from environment variable)
BOT_OWNER_IDS_STR = os.getenv('BOT_OWNER_IDS', '')
BOT_OWNER_IDS = [int(id.strip()) for id in BOT_OWNER_IDS_STR.split(',') if id.strip().isdigit()]

# Bot admin role name (configurable per guild via settings, this is the default)
DEFAULT_BOT_ADMIN_ROLE_NAME = os.getenv('BOT_ADMIN_ROLE_NAME', 'Bot Admin')


def is_bot_owner(user_id: int) -> bool:
    """
    Check if user is a bot owner.

    Args:
        user_id: Discord user ID

    Returns:
        True if user is a bot owner
    """
    return user_id in BOT_OWNER_IDS


def has_bot_admin_role(interaction: discord.Interaction) -> bool:
    """
    Check if user has the bot-specific admin role.

    Checks for custom role name set in guild settings, or falls back to default.

    Args:
        interaction: Discord interaction object

    Returns:
        True if user has bot admin role
    """
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return False

    # Import here to avoid circular dependency
    from utils.settings_manager import get_guild_setting

    # Get custom admin role name for this guild, or use default
    admin_role_name = get_guild_setting(
        interaction.guild.id,
        'bot_admin_role_name',
        DEFAULT_BOT_ADMIN_ROLE_NAME
    )

    # Check if user has the bot admin role
    return any(role.name == admin_role_name for role in interaction.user.roles)


def check_admin_permission(
    interaction: discord.Interaction,
    require_owner: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Enhanced permission check with bot-specific roles.

    Permission hierarchy:
    1. Bot owners (highest)
    2. Bot admin role (medium)
    3. Discord administrator permission (lowest admin tier)

    Args:
        interaction: Discord interaction object
        require_owner: If True, only bot owners can proceed

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

    user_id = interaction.user.id

    # Bot owners always have access
    if is_bot_owner(user_id):
        logger.info(f"Bot owner {user_id} accessed admin command in guild {interaction.guild.id}")
        return True, None

    # If owner-only, reject non-owners
    if require_owner:
        logger.warning(
            f"User {user_id} ({interaction.user.name}) attempted owner-only command "
            f"in guild {interaction.guild.id}"
        )
        return False, "❌ This command is only available to bot owners."

    # Check bot-specific admin role first
    if has_bot_admin_role(interaction):
        logger.info(
            f"User {user_id} ({interaction.user.name}) with bot admin role "
            f"accessed command in guild {interaction.guild.id}"
        )
        return True, None

    # Fall back to Discord administrator permission
    if interaction.user.guild_permissions.administrator:
        logger.info(
            f"User {user_id} ({interaction.user.name}) with Discord admin "
            f"accessed command in guild {interaction.guild.id}"
        )
        return True, None

    # User has no admin permissions
    logger.warning(
        f"User {user_id} ({interaction.user.name}) denied access to admin command "
        f"in guild {interaction.guild.id}"
    )
    return False, MSG_ADMIN_ONLY


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

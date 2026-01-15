"""
Channel management commands.
Handles /add_channel, /remove_channel and /list_channel commands for per-guild channel monitoring.
"""
import discord
from discord import app_commands
import logging

from utils.settings_manager import (
    add_monitored_channel,
    remove_monitored_channel,
    get_monitored_channels,
    is_channel_monitored
)
from utils.permissions import check_admin_permission, require_guild_context

logger = logging.getLogger(__name__)


def setup_channel_commands(tree: app_commands.CommandTree):
    """
    Register channel management commands with the bot's command tree.
    
    Args:
        tree: Discord command tree to register commands with
    """
    
    @tree.command(name='add_channel', description='Add current channel to monitored channels (Admin only)')
    async def add_channel(interaction: discord.Interaction):
        """Add the current channel to the list of monitored channels."""
        # Check if in guild
        is_in_guild, error_msg = require_guild_context(interaction)
        if not is_in_guild:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return
        
        # Check admin permission
        has_permission, error_msg = check_admin_permission(interaction)
        if not has_permission:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return
        
        guild_id = interaction.guild.id
        channel_id = interaction.channel_id
        channel_name = interaction.channel.name
        
        # Add channel
        was_added = add_monitored_channel(guild_id, channel_id)
        
        if was_added:
            await interaction.response.send_message(
                f"✅ Added #{channel_name} to monitored channels. The bot will now respond to messages here.",
                ephemeral=True
            )
            logger.info(
                f"Channel added to monitoring | guild={guild_id} ({interaction.guild.name}) | "
                f"channel={channel_id} (#{channel_name}) | user={interaction.user.name}"
            )
        else:
            await interaction.response.send_message(
                f"ℹ️ #{channel_name} is already being monitored.",
                ephemeral=True
            )
            logger.info(
                f"Channel already monitored | guild={guild_id} ({interaction.guild.name}) | "
                f"channel={channel_id} (#{channel_name}) | user={interaction.user.name}"
            )
    
    @tree.command(name='remove_channel', description='Remove current channel from monitored channels (Admin only)')
    async def remove_channel(interaction: discord.Interaction):
        """Remove the current channel from the list of monitored channels."""
        # Check if in guild
        is_in_guild, error_msg = require_guild_context(interaction)
        if not is_in_guild:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return
        
        # Check admin permission
        has_permission, error_msg = check_admin_permission(interaction)
        if not has_permission:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return
        
        guild_id = interaction.guild.id
        channel_id = interaction.channel_id
        channel_name = interaction.channel.name
        
        # Remove channel
        was_removed = remove_monitored_channel(guild_id, channel_id)
        
        if was_removed:
            await interaction.response.send_message(
                f"✅ Removed #{channel_name} from monitored channels. The bot will no longer respond to messages here.",
                ephemeral=True
            )
            logger.info(
                f"Channel removed from monitoring | guild={guild_id} ({interaction.guild.name}) | "
                f"channel={channel_id} (#{channel_name}) | user={interaction.user.name}"
            )
        else:
            await interaction.response.send_message(
                f"ℹ️ #{channel_name} is not currently being monitored.",
                ephemeral=True
            )
            logger.info(
                f"Channel not in monitored list | guild={guild_id} ({interaction.guild.name}) | "
                f"channel={channel_id} (#{channel_name}) | user={interaction.user.name}"
            )
    
    @tree.command(name='list_channels', description='List all monitored channels in this server (Admin only)')
    async def list_channels(interaction: discord.Interaction):
        """List all monitored channels for this guild."""
        # Check if in guild
        is_in_guild, error_msg = require_guild_context(interaction)
        if not is_in_guild:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return
        
        # Check admin permission
        has_permission, error_msg = check_admin_permission(interaction)
        if not has_permission:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return
        
        guild_id = interaction.guild.id
        monitored = get_monitored_channels(guild_id)
        
        if not monitored:
            await interaction.response.send_message(
                "ℹ️ No channels are currently being monitored in this server.\n"
                "Use `/add_channel` to add the current channel to the monitored list.",
                ephemeral=True
            )
            logger.info(f"Monitored channels listed | guild={guild_id} ({interaction.guild.name}) | count=0")
            return
        
        # Build list of channel mentions
        channel_mentions = []
        for ch_id in sorted(monitored):
            channel = interaction.guild.get_channel(ch_id)
            if channel:
                channel_mentions.append(f"• <#{ch_id}> (#{channel.name})")
            else:
                # Channel might have been deleted
                channel_mentions.append(f"• <#{ch_id}> (deleted or inaccessible)")
        
        channels_text = "\n".join(channel_mentions)
        
        await interaction.response.send_message(
            f"📋 **Monitored Channels ({len(monitored)}):**\n\n{channels_text}",
            ephemeral=True
        )
        logger.info(
            f"Monitored channels listed | guild={guild_id} ({interaction.guild.name}) | "
            f"count={len(monitored)} | user={interaction.user.name}"
        )
"""
Configuration command.
Handles /config command for server settings using interactive modals.
"""
import discord
from discord import app_commands
from typing import Optional, Tuple, Dict, List
import logging
import re
from datetime import datetime, timedelta

from utils.settings_manager import (
    get_guild_setting,
    set_guild_setting,
    delete_guild_setting,
    get_guild_temperature,
    get_guild_max_tokens,
    is_search_enabled,
    )
from utils.stats_manager import get_conversation_history, clear_conversation_history
from utils.permissions import check_admin_permission, require_guild_context
from config.settings import ENABLE_COMFYUI
from config.constants import MAX_PROMPT_CHANGES_PER_HOUR

logger = logging.getLogger(__name__)

# Suspicious patterns that could indicate prompt injection
PROMPT_INJECTION_PATTERNS = [
    r'ignore\s+(previous|all|prior)\s+instructions',
    r'disregard\s+(previous|all|prior)',
    r'forget\s+(everything|all|previous)',
    r'new\s+instructions',
    r'system\s+override',
    r'admin\s+mode',
    r'developer\s+mode',
    r'jailbreak',
    r'\\n\\n---\\n\\n',  # Common delimiter in injection attempts
    r'<\s*system\s*>',  # XML-style system tags
    r'SYSTEM:',  # System prompt markers
    r'you\s+are\s+now',  # Role redefinition attempts
]

# Track prompt changes per guild for rate limiting
prompt_change_timestamps: Dict[int, List[datetime]] = {}


def validate_system_prompt(prompt: str, guild_id: int) -> Tuple[bool, str]:
    """
    Validate system prompt for injection attempts and rate limiting.

    Args:
        prompt: The system prompt to validate
        guild_id: Guild ID for rate limiting

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check for injection patterns
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            logger.warning(
                f"Potential prompt injection detected in guild {guild_id}: "
                f"matched pattern '{pattern}'"
            )
            return False, "System prompt contains suspicious patterns. Please rephrase."

    # Rate limiting
    current_time = datetime.now()
    if guild_id not in prompt_change_timestamps:
        prompt_change_timestamps[guild_id] = []

    # Clean up old timestamps (older than 1 hour)
    prompt_change_timestamps[guild_id] = [
        ts for ts in prompt_change_timestamps[guild_id]
        if current_time - ts < timedelta(hours=1)
    ]

    # Check rate limit
    if len(prompt_change_timestamps[guild_id]) >= MAX_PROMPT_CHANGES_PER_HOUR:
        return False, f"Too many prompt changes ({MAX_PROMPT_CHANGES_PER_HOUR}/hour limit). Please wait before modifying again."

    # Record this change
    prompt_change_timestamps[guild_id].append(current_time)

    return True, ""


class SystemPromptModal(discord.ui.Modal, title="System Prompt Configuration"):
    """Modal for configuring the system prompt."""
    
    system_prompt = discord.ui.TextInput(
        label="System Prompt",
        style=discord.TextStyle.paragraph,
        placeholder="Enter custom system prompt (leave blank to use default)",
        required=False,
        max_length=2000
    )
    
    def __init__(self, guild_id: int, current_prompt: Optional[str] = None):
        super().__init__()
        self.guild_id = guild_id
        if current_prompt:
            self.system_prompt.default = current_prompt
    
    async def on_submit(self, interaction: discord.Interaction):
        prompt_value = self.system_prompt.value.strip()

        # Validate length
        if len(prompt_value) > 10000:
            await interaction.response.send_message(
                "❌ System prompt too long (max 10,000 characters).",
                ephemeral=True
            )
            return

        # Validate for injection patterns and rate limits
        if prompt_value:
            is_valid, error_msg = validate_system_prompt(prompt_value, self.guild_id)
            if not is_valid:
                await interaction.response.send_message(
                    f"❌ {error_msg}",
                    ephemeral=True
                )
                return

        if prompt_value:
            set_guild_setting(self.guild_id, "system_prompt", prompt_value)
            # Log who made the change for audit trail
            logger.info(
                f"System prompt updated for guild {self.guild_id} "
                f"by user {interaction.user.id} ({interaction.user.name})"
            )
            await interaction.response.send_message(
                f"✅ System prompt updated ({len(prompt_value)} characters).",
                ephemeral=True
            )
        else:
            delete_guild_setting(self.guild_id, "system_prompt")
            logger.info(
                f"System prompt cleared for guild {self.guild_id} "
                f"by user {interaction.user.id} ({interaction.user.name})"
            )
            await interaction.response.send_message(
                "✅ System prompt cleared (using default).",
                ephemeral=True
            )


class TemperatureModal(discord.ui.Modal, title="Temperature Configuration"):
    """Modal for configuring temperature."""
    
    temperature = discord.ui.TextInput(
        label="Temperature (0.0 - 2.0)",
        style=discord.TextStyle.short,
        placeholder="0.7",
        required=True,
        max_length=4
    )
    
    def __init__(self, guild_id: int, current_temp: float = 0.7):
        super().__init__()
        self.guild_id = guild_id
        self.temperature.default = str(current_temp)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            temp = float(self.temperature.value)
            if not 0.0 <= temp <= 2.0:
                await interaction.response.send_message(
                    "❌ Temperature must be between 0.0 and 2.0.",
                    ephemeral=True
                )
                return
            
            set_guild_setting(self.guild_id, "temperature", temp)
            await interaction.response.send_message(
                f"✅ Temperature set to **{temp}**.",
                ephemeral=True
            )
            logger.info(f"Temperature set to {temp} for guild {self.guild_id}")
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid number between 0.0 and 2.0.",
                ephemeral=True
            )


class MaxTokensModal(discord.ui.Modal, title="Max Tokens Configuration"):
    """Modal for configuring max tokens."""
    
    max_tokens = discord.ui.TextInput(
        label="Max Tokens (-1 for unlimited)",
        style=discord.TextStyle.short,
        placeholder="-1",
        required=True,
        max_length=6
    )
    
    def __init__(self, guild_id: int, current_max: int = -1):
        super().__init__()
        self.guild_id = guild_id
        self.max_tokens.default = str(current_max)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            tokens = int(self.max_tokens.value)
            if tokens <= 0 and tokens != -1:
                await interaction.response.send_message(
                    "❌ Max tokens must be a positive integer or -1 (unlimited).",
                    ephemeral=True
                )
                return
            
            set_guild_setting(self.guild_id, "max_tokens", tokens)
            display = "unlimited" if tokens == -1 else str(tokens)
            await interaction.response.send_message(
                f"✅ Max tokens set to **{display}**.",
                ephemeral=True
            )
            logger.info(f"Max tokens set to {tokens} for guild {self.guild_id}")
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid integer or -1 for unlimited.",
                ephemeral=True
            )


class ConfigView(discord.ui.View):
    """Interactive view for bot configuration."""
    
    def __init__(self, guild_id: int):
        super().__init__(timeout=300)  # 5 minute timeout
        self.guild_id = guild_id
        self.update_toggle_buttons()
    
    def update_toggle_buttons(self):
        """Update button states based on current settings."""
        # Update search button
        search_enabled = is_search_enabled(self.guild_id)
        self.toggle_search.label = f"Web Search: {'ON' if search_enabled else 'OFF'}"
        self.toggle_search.style = discord.ButtonStyle.success if search_enabled else discord.ButtonStyle.secondary

        # Update TTS button
        tts_enabled = get_guild_setting(self.guild_id, "tts_enabled", True)
        self.toggle_tts.label = f"TTS: {'ON' if tts_enabled else 'OFF'}"
        self.toggle_tts.style = discord.ButtonStyle.success if tts_enabled else discord.ButtonStyle.secondary

        # Update ComfyUI button (only if globally enabled)
        if ENABLE_COMFYUI:
            comfyui_enabled = get_guild_setting(self.guild_id, "comfyui_enabled", True)
            self.toggle_comfyui.label = f"Image Gen: {'ON' if comfyui_enabled else 'OFF'}"
            self.toggle_comfyui.style = discord.ButtonStyle.success if comfyui_enabled else discord.ButtonStyle.secondary
            self.toggle_comfyui.disabled = False
        else:
            # Hide button if ComfyUI is globally disabled
            if hasattr(self, 'toggle_comfyui'):
                self.toggle_comfyui.disabled = True
                self.toggle_comfyui.style = discord.ButtonStyle.secondary
    
    def create_embed(self) -> discord.Embed:
        """Create embed showing current configuration."""
        system_prompt = get_guild_setting(self.guild_id, "system_prompt")
        temperature = get_guild_temperature(self.guild_id)
        max_tokens = get_guild_max_tokens(self.guild_id)
        search_enabled = is_search_enabled(self.guild_id)

        prompt_display = (
            "Default"
            if not system_prompt
            else f"Custom ({len(system_prompt)} chars)"
        )
        max_tokens_display = "unlimited" if max_tokens == -1 else str(max_tokens)

        embed = discord.Embed(
            title="⚙️ Bot Configuration",
            description="Click the buttons below to configure settings",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="🧠 System Prompt",
            value=prompt_display,
            inline=True
        )
        embed.add_field(
            name="🌡️ Temperature",
            value=str(temperature),
            inline=True
        )
        embed.add_field(
            name="📊 Max Tokens",
            value=max_tokens_display,
            inline=True
        )
        embed.add_field(
            name="🔍 Web Search",
            value="Enabled" if search_enabled else "Disabled",
            inline=True
        )
        embed.add_field(
            name="🔊 Text-to-Speech",
            value="Enabled" if get_guild_setting(self.guild_id, "tts_enabled", True) else "Disabled",
            inline=True
        )

        # Only show ComfyUI if globally enabled
        if ENABLE_COMFYUI:
            comfyui_enabled = get_guild_setting(self.guild_id, "comfyui_enabled", True)
            embed.add_field(
                name="🎨 Image Generation",
                value="Enabled" if comfyui_enabled else "Disabled",
                inline=True
            )

        embed.set_footer(text="⚠️ Admin permissions required to make changes")
        
        return embed
    
    @discord.ui.button(label="System Prompt", style=discord.ButtonStyle.primary, emoji="🧠", row=0)
    async def edit_prompt(self, interaction: discord.Interaction, button: discord.ui.Button):
        has_permission, error_msg = check_admin_permission(interaction)
        if not has_permission:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        current = get_guild_setting(self.guild_id, "system_prompt")
        modal = SystemPromptModal(self.guild_id, current)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Temperature", style=discord.ButtonStyle.primary, emoji="🌡️", row=0)
    async def adjust_temp(self, interaction: discord.Interaction, button: discord.ui.Button):
        has_permission, error_msg = check_admin_permission(interaction)
        if not has_permission:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        current = get_guild_temperature(self.guild_id)
        modal = TemperatureModal(self.guild_id, current)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Max Tokens", style=discord.ButtonStyle.primary, emoji="📊", row=0)
    async def set_tokens(self, interaction: discord.Interaction, button: discord.ui.Button):
        has_permission, error_msg = check_admin_permission(interaction)
        if not has_permission:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        current = get_guild_max_tokens(self.guild_id)
        modal = MaxTokensModal(self.guild_id, current)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Web Search: ON", style=discord.ButtonStyle.success, emoji="🔍", row=1)
    async def toggle_search(self, interaction: discord.Interaction, button: discord.ui.Button):
        has_permission, error_msg = check_admin_permission(interaction)
        if not has_permission:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return
        
        current = is_search_enabled(self.guild_id)
        new_state = not current
        
        set_guild_setting(self.guild_id, "search_enabled", new_state)
        self.update_toggle_buttons()
        
        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)
        
        logger.info(f"Web search {'enabled' if new_state else 'disabled'} for guild {self.guild_id}")
    
    @discord.ui.button(label="TTS: ON", style=discord.ButtonStyle.success, emoji="🔊", row=1)
    async def toggle_tts(self, interaction: discord.Interaction, button: discord.ui.Button):
        has_permission, error_msg = check_admin_permission(interaction)
        if not has_permission:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        current = get_guild_setting(self.guild_id, "tts_enabled", True)
        new_state = not current

        set_guild_setting(self.guild_id, "tts_enabled", new_state)
        self.update_toggle_buttons()

        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

        logger.info(f"TTS {'enabled' if new_state else 'disabled'} for guild {self.guild_id}")

    @discord.ui.button(label="Image Gen: ON", style=discord.ButtonStyle.success, emoji="🎨", row=1)
    async def toggle_comfyui(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if ComfyUI is globally enabled
        if not ENABLE_COMFYUI:
            await interaction.response.send_message(
                "❌ Image generation is globally disabled. Enable it in the .env configuration.",
                ephemeral=True
            )
            return

        has_permission, error_msg = check_admin_permission(interaction)
        if not has_permission:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        current = get_guild_setting(self.guild_id, "comfyui_enabled", True)
        new_state = not current

        set_guild_setting(self.guild_id, "comfyui_enabled", new_state)
        self.update_toggle_buttons()

        embed = self.create_embed()
        await interaction.response.edit_message(embed=embed, view=self)

        logger.info(f"ComfyUI image generation {'enabled' if new_state else 'disabled'} for guild {self.guild_id}")

    @discord.ui.button(label="Clear Last Message", style=discord.ButtonStyle.danger, emoji="🧹", row=2)
    async def clear_last(self, interaction: discord.Interaction, button: discord.ui.Button):
        has_permission, error_msg = check_admin_permission(interaction)
        if not has_permission:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        conversation_id = interaction.channel_id
        history = get_conversation_history(conversation_id)

        if not history:
            await interaction.response.send_message(
                "ℹ️ No conversation history to clear.",
                ephemeral=True
            )
            return

        # Remove last assistant + user messages
        removed = 0
        while history and removed < 2:
            if history[-1]["role"] in {"assistant", "user"}:
                history.pop()
                removed += 1
            else:
                break

        await interaction.response.send_message(
            "🧹 Last interaction removed from conversation history.",
            ephemeral=True
        )
        logger.info(f"Cleared last interaction in channel {interaction.channel_id}")

    @discord.ui.button(label="Clear All History", style=discord.ButtonStyle.danger, emoji="🗑️", row=2)
    async def clear_all_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        has_permission, error_msg = check_admin_permission(interaction)
        if not has_permission:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        conversation_id = interaction.channel_id
        history = get_conversation_history(conversation_id)

        if not history:
            await interaction.response.send_message(
                "ℹ️ No conversation history to clear.",
                ephemeral=True
            )
            return

        clear_conversation_history(conversation_id)
        await interaction.response.send_message(
            f"🗑️ Cleared entire conversation history ({len(history)} messages).",
            ephemeral=True
        )
        logger.info(f"Cleared all conversation history in channel {interaction.channel_id}")

    @discord.ui.button(label="Reset to Defaults", style=discord.ButtonStyle.danger, emoji="🔄", row=3)
    async def reset_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        has_permission, error_msg = check_admin_permission(interaction)
        if not has_permission:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        # Clear all custom settings
        settings_to_clear = [
            "system_prompt",
            "temperature",
            "max_tokens",
            "search_enabled",
            "tts_enabled",
            "selected_voice",
            "comfyui_enabled"
        ]

        for setting in settings_to_clear:
            delete_guild_setting(self.guild_id, setting)

        self.update_toggle_buttons()
        embed = self.create_embed()

        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(
            "✅ All settings reset to defaults.",
            ephemeral=True
        )
        logger.info(f"All settings reset to defaults for guild {self.guild_id}")

    @discord.ui.button(label="Clear All Stats", style=discord.ButtonStyle.danger, emoji="📊", row=3)
    async def clear_all_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        has_permission, error_msg = check_admin_permission(interaction)
        if not has_permission:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        # Get all channel IDs in this guild
        guild = interaction.guild
        channel_ids = [channel.id for channel in guild.channels]

        # Reset statistics for all channels in this guild
        reset_count = 0
        from utils.stats_manager import reset_stats
        from utils.database import get_database

        db = get_database()
        for channel_id in channel_ids:
            # Check if conversation exists for this channel
            if db.get_conversation(channel_id):
                reset_stats(channel_id)
                reset_count += 1

        await interaction.response.send_message(
            f"📊 Reset statistics for {reset_count} channel(s) in this server. All stats are now back to zero.",
            ephemeral=True
        )
        logger.info(f"All statistics reset for guild {self.guild_id} ({reset_count} channels)")


def setup_config_command(tree: app_commands.CommandTree):
    """
    Register config command with the bot's command tree.
    
    Args:
        tree: Discord command tree to register commands with
    """
    
    @tree.command(name="config", description="Configure bot settings for this server")
    async def config(interaction: discord.Interaction):
        """Open the configuration panel."""
        is_in_guild, error_msg = require_guild_context(interaction)
        if not is_in_guild:
            await interaction.response.send_message(error_msg, ephemeral=True)
            return
        
        view = ConfigView(interaction.guild.id)
        embed = view.create_embed()
        
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )
        logger.info(f"Config panel opened by {interaction.user} in guild {interaction.guild.id}")
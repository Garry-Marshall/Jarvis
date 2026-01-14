"""
Voice and TTS commands.
Handles /join, /leave, and /voice commands.
"""
import discord
from discord import app_commands
from typing import Dict, Optional
import logging

from config.settings import ENABLE_TTS, ALLTALK_VOICE
from config.constants import AVAILABLE_VOICES, VOICE_DESCRIPTIONS
from utils.guild_settings import is_tts_enabled_for_guild, get_guild_voice, set_guild_setting


logger = logging.getLogger(__name__)

# Store voice channel connections per guild (Still in-memory as these are active sessions)
voice_clients: Dict[int, discord.VoiceClient] = {}


class VoiceSelectView(discord.ui.View):
    """View with dropdown for voice selection."""
    def __init__(self, current_voice: str):
        super().__init__(timeout=60)
        self.add_item(VoiceSelectDropdown(current_voice))


class VoiceSelectDropdown(discord.ui.Select):
    """Dropdown menu for selecting TTS voice."""
    def __init__(self, current_voice: str):
        options = [
            discord.SelectOption(
                label=voice.capitalize(),
                value=voice,
                description=VOICE_DESCRIPTIONS.get(voice, f"Voice: {voice}"),
                default=(voice == current_voice)
            )
            for voice in AVAILABLE_VOICES
        ]
        
        super().__init__(
            placeholder="Select a voice...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        selected_voice = self.values[0]
        guild_id = interaction.guild.id
        
        # Save to persistent guild settings
        set_guild_setting(guild_id, "selected_voice", selected_voice)
        
        await interaction.response.send_message(
            f"✅ Voice changed to: **{selected_voice}**",
            ephemeral=True
        )
        logger.info(f"Voice changed to '{selected_voice}' in {interaction.guild.name}")


def setup_voice_commands(tree: app_commands.CommandTree):
    """Register voice commands with the bot's command tree."""
    
    @tree.command(name='join', description='Join your voice channel')
    async def join_voice(interaction: discord.Interaction):
        guild_id = interaction.guild.id
        
        if not is_tts_enabled_for_guild(guild_id):
            if not ENABLE_TTS:
                await interaction.response.send_message("❌ TTS is globally disabled.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ TTS is disabled for this server.", ephemeral=True)
            return
        
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You need to be in a voice channel!", ephemeral=True)
            return
        
        voice_channel = interaction.user.voice.channel
        
        if guild_id in voice_clients and voice_clients[guild_id].is_connected():
            if voice_clients[guild_id].channel.id == voice_channel.id:
                await interaction.response.send_message("✅ Already in your channel!", ephemeral=True)
                return
            await voice_clients[guild_id].move_to(voice_channel)
            await interaction.response.send_message(f"✅ Moved to {voice_channel.name}!", ephemeral=True)
            return
        
        try:
            voice_client = await voice_channel.connect()
            voice_clients[guild_id] = voice_client
            await interaction.response.send_message(f"✅ Joined {voice_channel.name}!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error joining: {e}")
            await interaction.response.send_message(f"❌ Failed to join: {str(e)}", ephemeral=True)
    
    @tree.command(name='leave', description='Leave the voice channel')
    async def leave_voice(interaction: discord.Interaction):
        guild_id = interaction.guild.id
        if guild_id not in voice_clients or not voice_clients[guild_id].is_connected():
            await interaction.response.send_message("❌ I'm not in a voice channel!", ephemeral=True)
            return
        
        await voice_clients[guild_id].disconnect()
        del voice_clients[guild_id]
        await interaction.response.send_message("✅ Left the voice channel.", ephemeral=True)
    
    @tree.command(name='voice', description='Select TTS voice')
    async def select_voice(interaction: discord.Interaction):
        guild_id = interaction.guild.id
        
        if not is_tts_enabled_for_guild(guild_id):
            await interaction.response.send_message("❌ TTS is disabled.", ephemeral=True)
            return
        
        # Pull from persistent settings
        current_voice = get_guild_voice(guild_id)
        
        voice_list = "\n".join([
            f"• **{voice}** - {VOICE_DESCRIPTIONS.get(voice, 'Unknown')}"
            for voice in AVAILABLE_VOICES
        ])
        
        view = VoiceSelectView(current_voice)
        await interaction.response.send_message(
            f"**Current voice:** {current_voice}\n\n**Available voices:**\n{voice_list}\n\nSelect a new voice:",
            view=view,
            ephemeral=True
        )


def get_voice_client(guild_id: int) -> Optional[discord.VoiceClient]:
    """Get the voice client for a guild."""
    return voice_clients.get(guild_id)


def get_selected_voice(guild_id: int) -> str:
    """Get the selected voice for a guild from persistent settings."""
    return get_guild_voice(guild_id)
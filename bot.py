import discord
from discord.ext import commands
import aiohttp
import json
import os
from typing import Optional, List, Dict
from dotenv import load_dotenv
from collections import defaultdict
from datetime import datetime
import time
import base64
import io
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables from .env file
load_dotenv()

# Check if .env file exists, if not create one with defaults
env_file_path = ".env"
if not os.path.exists(env_file_path):
    default_env_content = """# Discord Bot Configuration
# Fill in your bot token and channel IDs below

# REQUIRED: Your Discord bot token from https://discord.com/developers/applications
DISCORD_BOT_TOKEN=your-discord-bot-token-here

# REQUIRED: Comma-separated list of channel IDs where the bot should listen
# Enable Developer Mode in Discord, right-click channels, and select "Copy ID"
DISCORD_CHANNEL_IDS=

# LMStudio API Configuration
LMSTUDIO_URL=http://localhost:1234/v1/chat/completions

# Conversation Settings
MAX_HISTORY_MESSAGES=10
CONTEXT_MESSAGES=5

# Bot Behavior
IGNORE_BOTS=true
ALLOW_DMS=true

# Image Support
ALLOW_IMAGES=true
MAX_IMAGE_SIZE=5

# Text File Support
ALLOW_TEXT_FILES=true
MAX_TEXT_FILE_SIZE=2

# Reasoning Model Settings
HIDE_THINKING=true
"""
    with open(env_file_path, 'w', encoding='utf-8') as f:
        f.write(default_env_content)
    print(f"Created default .env file at {env_file_path}")
    print("Please edit the .env file and add your DISCORD_BOT_TOKEN and DISCORD_CHANNEL_IDS")
    print("")
    # Reload after creating the file
    load_dotenv()

# Setup logging
log_dir = "Logs"
os.makedirs(log_dir, exist_ok=True)

# Create log filename with date stamp
log_filename = os.path.join(log_dir, f"bot_{datetime.now().strftime('%Y-%m-%d')}.log")

# Configure logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        # File handler with rotation (max 10MB per file, keep 5 backup files)
        RotatingFileHandler(log_filename, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'),
        # Console handler
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Configuration
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN', 'your-discord-bot-token-here')
LMSTUDIO_URL = os.getenv('LMSTUDIO_URL', 'http://localhost:1234/v1/chat/completions')
MAX_HISTORY = int(os.getenv('MAX_HISTORY_MESSAGES', '10'))
CONTEXT_MESSAGES = int(os.getenv('CONTEXT_MESSAGES', '5'))
IGNORE_BOTS = os.getenv('IGNORE_BOTS', 'true').lower() == 'true'
ALLOW_DMS = os.getenv('ALLOW_DMS', 'true').lower() == 'true'
ALLOW_IMAGES = os.getenv('ALLOW_IMAGES', 'true').lower() == 'true'
MAX_IMAGE_SIZE = int(os.getenv('MAX_IMAGE_SIZE', '5'))
ALLOW_TEXT_FILES = os.getenv('ALLOW_TEXT_FILES', 'true').lower() == 'true'
MAX_TEXT_FILE_SIZE = int(os.getenv('MAX_TEXT_FILE_SIZE', '2'))
HIDE_THINKING = os.getenv('HIDE_THINKING', 'true').lower() == 'true'

# Parse channel IDs from environment variable (comma-separated)
CHANNEL_IDS_STR = os.getenv('DISCORD_CHANNEL_IDS', '0')
CHANNEL_IDS = set()
if CHANNEL_IDS_STR and CHANNEL_IDS_STR != '0':
    try:
        CHANNEL_IDS = set(int(cid.strip()) for cid in CHANNEL_IDS_STR.split(',') if cid.strip())
    except ValueError:
        logger.error("DISCORD_CHANNEL_IDS must be comma-separated numbers")
        CHANNEL_IDS = set()

# Store conversation history per channel/DM
conversation_histories: Dict[int, List[Dict[str, str]]] = defaultdict(list)

# Track whether context has been loaded for each conversation
context_loaded: Dict[int, bool] = defaultdict(bool)

# Store statistics per channel/DM
channel_stats: Dict[int, Dict] = defaultdict(lambda: {
    'total_messages': 0,
    'total_tokens_estimate': 0,
    'start_time': datetime.now(),
    'last_message_time': None,
    'response_times': []
})

# Bot setup with message content intent
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

async def get_recent_context(channel, limit: int = CONTEXT_MESSAGES) -> List[Dict[str, str]]:
    """Fetch recent messages from the Discord channel to provide context."""
    context = []
    try:
        async for msg in channel.history(limit=limit * 3):
            if IGNORE_BOTS and msg.author.bot:
                continue
            if msg.author == bot.user:
                continue
            
            if isinstance(channel, discord.DMChannel):
                context.append({"role": "user", "content": msg.content})
            else:
                context.append({"role": "user", "content": f"{msg.author.display_name}: {msg.content}"})
            
            if len(context) >= limit:
                break
        
        context.reverse()
        return context
    except Exception as e:
        logger.error(f"Error fetching message history: {e}")
        return []

def estimate_tokens(text: str) -> int:
    """Rough estimation of tokens (approximately 4 characters per token)."""
    return len(text) // 4

def remove_thinking_tags(text: str) -> str:
    """Remove thinking tags and box markers from reasoning model outputs."""
    import re
    
    if not HIDE_THINKING:
        return text
    
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'\[THINK\].*?\[/THINK\]', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<think\s*/>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\[THINK\s*/\]', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<\|begin_of_box\|>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<\|end_of_box\|>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
    cleaned = cleaned.strip()
    
    return cleaned

def is_inside_thinking_tags(text: str) -> bool:
    """Check if we're currently inside an unclosed thinking tag."""
    import re
    
    if not HIDE_THINKING:
        return False
    
    open_tags = len(re.findall(r'<think>', text, flags=re.IGNORECASE))
    close_tags = len(re.findall(r'</think>', text, flags=re.IGNORECASE))
    open_brackets = len(re.findall(r'\[THINK\]', text, flags=re.IGNORECASE))
    close_brackets = len(re.findall(r'\[/THINK\]', text, flags=re.IGNORECASE))
    
    return (open_tags > close_tags) or (open_brackets > close_brackets)

async def process_image_attachment(attachment) -> Optional[Dict]:
    """Download and convert an image attachment to base64 for the vision model."""
    if not attachment.content_type or not attachment.content_type.startswith('image/'):
        return None
    
    if attachment.size > MAX_IMAGE_SIZE * 1024 * 1024:
        logger.warning(f"Image too large: {attachment.size / (1024*1024):.2f}MB (max: {MAX_IMAGE_SIZE}MB)")
        return None
    
    try:
        image_data = await attachment.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        media_type = attachment.content_type.lower().strip()
        
        if 'png' in media_type or attachment.filename.lower().endswith('.png'):
            media_type = 'image/png'
        elif 'jpeg' in media_type or 'jpg' in media_type or attachment.filename.lower().endswith(('.jpg', '.jpeg')):
            media_type = 'image/jpeg'
        elif 'gif' in media_type or attachment.filename.lower().endswith('.gif'):
            media_type = 'image/gif'
        elif 'webp' in media_type or attachment.filename.lower().endswith('.webp'):
            media_type = 'image/webp'
        else:
            logger.warning(f"Unknown image type '{attachment.content_type}', defaulting to image/jpeg")
            media_type = 'image/jpeg'
        
        logger.info(f"Processing image: {attachment.filename} ({attachment.size / 1024:.2f}KB, {media_type})")
        
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{media_type};base64,{base64_image}"
            }
        }
    except Exception as e:
        logger.error(f"Error processing image {attachment.filename}: {e}")
        logger.debug(f"  Content type was: {attachment.content_type}")
        logger.debug(f"  Filename was: {attachment.filename}")
        return None

async def process_text_attachment(attachment) -> Optional[str]:
    """Download and read a text file attachment."""
    text_extensions = ['.txt', '.md', '.py', '.js', '.java', '.c', '.cpp', '.h', '.html', 
                      '.css', '.json', '.xml', '.yaml', '.yml', '.csv', '.log', '.sh', 
                      '.bat', '.ps1', '.sql', '.r', '.php', '.go', '.rs', '.swift', '.kt']
    
    filename_lower = attachment.filename.lower()
    
    is_text = any(filename_lower.endswith(ext) for ext in text_extensions)
    if attachment.content_type:
        is_text = is_text or 'text/' in attachment.content_type or 'application/json' in attachment.content_type
    
    if not is_text:
        return None
    
    if attachment.size > MAX_TEXT_FILE_SIZE * 1024 * 1024:
        logger.warning(f"Text file too large: {attachment.size / (1024*1024):.2f}MB (max: {MAX_TEXT_FILE_SIZE}MB)")
        return None
    
    try:
        file_data = await attachment.read()
        
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                text_content = file_data.decode(encoding)
                logger.info(f"Processing text file: {attachment.filename} ({attachment.size / 1024:.2f}KB)")
                return f"\n\n--- Content of {attachment.filename} ---\n{text_content}\n--- End of {attachment.filename} ---\n"
            except UnicodeDecodeError:
                continue
        
        logger.error(f"Could not decode text file {attachment.filename}")
        return None
        
    except Exception as e:
        logger.error(f"Error processing text file {attachment.filename}: {e}")
        return None

async def query_lmstudio(conversation_id: int, message_text: str, channel, username: str, images: List[Dict] = None) -> Optional[str]:
    """Send a message to LMStudio API with conversation history and return the response."""
    start_time = time.time()
    
    if len(conversation_histories[conversation_id]) == 0 and not context_loaded[conversation_id] and CONTEXT_MESSAGES > 0:
        recent_context = await get_recent_context(channel, CONTEXT_MESSAGES)
        conversation_histories[conversation_id].extend(recent_context)
        context_loaded[conversation_id] = True
        logger.info(f"Loaded {len(recent_context)} context messages")
    
    if images and len(images) > 0:
        message_content = []
        
        if message_text.strip():
            message_content.append({"type": "text", "text": message_text})
        else:
            message_content.append({"type": "text", "text": "What's in this image?"})
        
        message_content.extend(images)
        
        conversation_histories[conversation_id].append({
            "role": "user",
            "content": message_content
        })
    else:
        conversation_histories[conversation_id].append({
            "role": "user",
            "content": message_text
        })
    
    is_dm = isinstance(channel, discord.DMChannel)
    if is_dm:
        context_type = f"DM from {username} (ID: {conversation_id})"
    else:
        channel_name = getattr(channel, 'name', 'Unknown')
        guild_name = getattr(channel.guild, 'name', 'Unknown') if hasattr(channel, 'guild') else 'Unknown'
        context_type = f"#{channel_name} in {guild_name} - User: {username}"
    
    image_info = f" [with {len(images)} image(s)]" if images and len(images) > 0 else ""
    logger.info(f"[{context_type}]{image_info}")
    logger.info(f"Message: {message_text}")
    
    if len(conversation_histories[conversation_id]) > MAX_HISTORY * 2:
        conversation_histories[conversation_id] = conversation_histories[conversation_id][-(MAX_HISTORY * 2):]
    
    api_messages = []
    
    for msg in conversation_histories[conversation_id]:
        current_role = msg["role"]
        
        if api_messages:
            last_role = api_messages[-1]["role"]
            
            if current_role == last_role:
                if current_role == "user":
                    api_messages.append({"role": "assistant", "content": "Understood."})
                else:
                    continue
        
        api_messages.append(msg)
    
    if api_messages and api_messages[-1]["role"] == "assistant":
        api_messages.pop()
    
    logger.debug(f"Sending {len(api_messages)} messages to API:")
    for i, msg in enumerate(api_messages):
        content_preview = str(msg["content"])[:100] if isinstance(msg["content"], str) else f"[complex content with {len(msg['content'])} parts]"
        logger.debug(f"  {i+1}. {msg['role']}: {content_preview}")
    
    payload = {
        #"model": "local-model",
        "model": "zai-org/glm-4.6v-flash",
        "messages": api_messages,
        "temperature": 0.7,
        "max_tokens": -1,
        "stream": True
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(LMSTUDIO_URL, json=payload) as response:
                if response.status == 200:
                    assistant_message = ""
                    
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data_str = line[6:]
                            if data_str == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                if 'choices' in data and len(data['choices']) > 0:
                                    delta = data['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        assistant_message += content
                                        yield content
                            except json.JSONDecodeError:
                                continue
                    
                    response_time = time.time() - start_time
                    
                    logger.info(f"Full Response (with thinking): {assistant_message}")
                    
                    assistant_message_filtered = remove_thinking_tags(assistant_message)
                    
                    logger.info(f"Filtered Response (shown to user): {assistant_message_filtered}")
                    logger.info(f"Response time: {response_time:.2f}s")
                    
                    if HIDE_THINKING and assistant_message != assistant_message_filtered:
                        logger.info(f"Thinking tags removed. Original length: {len(assistant_message)}, Filtered length: {len(assistant_message_filtered)}")
                    
                    conversation_histories[conversation_id].append({
                        "role": "assistant",
                        "content": assistant_message
                    })
                    
                    stats = channel_stats[conversation_id]
                    stats['total_messages'] += 2
                    stats['total_tokens_estimate'] += estimate_tokens(message_text) + estimate_tokens(assistant_message)
                    stats['last_message_time'] = datetime.now()
                    stats['response_times'].append(response_time)
                else:
                    error_text = await response.text()
                    logger.error(f"LMStudio API error: {response.status} - {error_text}")
                    conversation_histories[conversation_id].pop()
                    yield f"Error: LMStudio API returned status {response.status}"
    except aiohttp.ClientError as e:
        logger.error(f"Connection error to LMStudio: {e}")
        conversation_histories[conversation_id].pop()
        yield "Error: Could not connect to LMStudio. Is it running?"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        conversation_histories[conversation_id].pop()
        yield f"Error: {str(e)}"

@bot.tree.command(name='reset', description='Reset the conversation history for this channel or DM')
async def reset_conversation(interaction: discord.Interaction):
    """Slash command to reset the conversation history for the current channel or DM."""
    conversation_id = interaction.channel_id if interaction.guild else interaction.user.id
    
    if interaction.guild and interaction.channel_id not in CHANNEL_IDS:
        await interaction.response.send_message("❌ This command only works in monitored channels.", ephemeral=True)
        return
    
    if not interaction.guild and not ALLOW_DMS:
        await interaction.response.send_message("❌ DM conversations are not enabled.", ephemeral=True)
        return
    
    conversation_histories[conversation_id].clear()
    context_loaded[conversation_id] = False
    channel_stats[conversation_id] = {
        'total_messages': 0,
        'total_tokens_estimate': 0,
        'start_time': datetime.now(),
        'last_message_time': None,
        'response_times': []
    }
    await interaction.response.send_message("✅ Conversation history and statistics have been reset. Starting fresh!", ephemeral=True)

@bot.tree.command(name='history', description='Show the conversation history length')
async def show_history(interaction: discord.Interaction):
    """Slash command to show how many messages are in the current channel's or DM's history."""
    conversation_id = interaction.channel_id if interaction.guild else interaction.user.id
    
    if interaction.guild and interaction.channel_id not in CHANNEL_IDS:
        await interaction.response.send_message("❌ This command only works in monitored channels.", ephemeral=True)
        return
    
    if not interaction.guild and not ALLOW_DMS:
        await interaction.response.send_message("❌ DM conversations are not enabled.", ephemeral=True)
        return
    
    msg_count = len(conversation_histories[conversation_id])
    await interaction.response.send_message(
        f"📊 This conversation has {msg_count} messages in its history (max: {MAX_HISTORY * 2}).",
        ephemeral=True
    )

@bot.tree.command(name='stats', description='Show conversation statistics')
async def show_stats(interaction: discord.Interaction):
    """Slash command to show conversation statistics."""
    conversation_id = interaction.channel_id if interaction.guild else interaction.user.id
    
    if interaction.guild and interaction.channel_id not in CHANNEL_IDS:
        await interaction.response.send_message("❌ This command only works in monitored channels.", ephemeral=True)
        return
    
    if not interaction.guild and not ALLOW_DMS:
        await interaction.response.send_message("❌ DM conversations are not enabled.", ephemeral=True)
        return
    
    stats = channel_stats[conversation_id]
    
    avg_response_time = 0
    if stats['response_times']:
        avg_response_time = sum(stats['response_times']) / len(stats['response_times'])
    
    duration = datetime.now() - stats['start_time']
    hours, remainder = divmod(int(duration.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    
    last_msg = "Never"
    if stats['last_message_time']:
        last_msg = stats['last_message_time'].strftime("%Y-%m-%d %H:%M:%S")
    
    stats_message = f"""📈 **Conversation Statistics**
    
**Total Messages:** {stats['total_messages']}
**Estimated Tokens:** {stats['total_tokens_estimate']:,}
**Session Duration:** {hours}h {minutes}m {seconds}s
**Average Response Time:** {avg_response_time:.2f}s
**Last Message:** {last_msg}
**Messages in History:** {len(conversation_histories[conversation_id])}
    """
    
    await interaction.response.send_message(stats_message, ephemeral=True)

@bot.event
async def on_ready():
    """Called when the bot successfully connects to Discord."""
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} server(s)')
    logger.info(f'Listening in {len(CHANNEL_IDS)} channel(s): {CHANNEL_IDS}')
    logger.info(f'LMStudio URL: {LMSTUDIO_URL}')
    
    for channel_id in CHANNEL_IDS:
        channel = bot.get_channel(channel_id)
        if channel:
            logger.info(f'  - #{channel.name} in {channel.guild.name}')
        else:
            logger.warning(f'  - Channel ID {channel_id} not found (bot may not have access)')
    
    try:
        synced = await bot.tree.sync()
        logger.info(f'Synced {len(synced)} slash command(s)')
    except Exception as e:
        logger.error(f'Failed to sync slash commands: {e}')
    
    logger.info(f'IGNORE_BOTS setting: {IGNORE_BOTS}')
    logger.info(f'CONTEXT_MESSAGES setting: {CONTEXT_MESSAGES}')
    logger.info(f'ALLOW_DMS setting: {ALLOW_DMS}')
    logger.info(f'ALLOW_IMAGES setting: {ALLOW_IMAGES}')
    logger.info(f'MAX_IMAGE_SIZE setting: {MAX_IMAGE_SIZE}MB')
    logger.info(f'ALLOW_TEXT_FILES setting: {ALLOW_TEXT_FILES}')
    logger.info(f'MAX_TEXT_FILE_SIZE setting: {MAX_TEXT_FILE_SIZE}MB')
    logger.info(f'HIDE_THINKING setting: {HIDE_THINKING}')
    logger.info(f'Logging to: {log_filename}')

@bot.event
async def on_message(message):
    """Called when any message is sent in a channel the bot can see."""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Ignore messages from other bots if enabled
    if IGNORE_BOTS and message.author.bot:
        return
    
    # Check if it's a DM
    is_dm = isinstance(message.channel, discord.DMChannel)
    
    # For DMs, check if they're allowed
    if is_dm:
        if not ALLOW_DMS:
            return
        conversation_id = message.author.id
    else:
        # For guild channels, check if it's a monitored channel
        if message.channel.id not in CHANNEL_IDS:
            return
        conversation_id = message.channel.id
    
    # Ignore messages starting with * (user wants to exclude from bot)
    if message.content.startswith('*'):
        logger.info(f"Ignoring message starting with asterisk from {message.author.display_name}")
        return
    
    # Ignore empty messages
    if not message.content.strip():
        return
    
    # Process any attachments if enabled
    images = []
    text_files_content = ""
    
    if message.attachments:
        for attachment in message.attachments:
            if ALLOW_IMAGES:
                image_data = await process_image_attachment(attachment)
                if image_data:
                    images.append(image_data)
                    continue
            
            if ALLOW_TEXT_FILES:
                text_content = await process_text_attachment(attachment)
                if text_content:
                    text_files_content += text_content
    
    if not message.content.strip() and not images and not text_files_content:
        return
    
    combined_message = message.content
    if text_files_content:
        combined_message = f"{message.content}\n{text_files_content}" if message.content.strip() else text_files_content
    
    status_msg = await message.channel.send("🤔 Thinking...")
    
    try:
        response_text = ""
        last_update = time.time()
        update_interval = 1.0
        
        username = message.author.display_name
        
        async for chunk in query_lmstudio(conversation_id, combined_message, message.channel, username, images):
            response_text += chunk
            
            current_time = time.time()
            if current_time - last_update >= update_interval:
                display_text = remove_thinking_tags(response_text)
                
                if not is_inside_thinking_tags(response_text):
                    display_text = display_text[:1900] + "..." if len(display_text) > 1900 else display_text
                    
                    if display_text.strip():
                        try:
                            await status_msg.edit(content=display_text if display_text else "🤔 Thinking...")
                            last_update = current_time
                        except discord.errors.HTTPException:
                            pass
                else:
                    try:
                        await status_msg.edit(content="🤔 Thinking...")
                        last_update = current_time
                    except discord.errors.HTTPException:
                        pass
        
        if response_text:
            final_response = remove_thinking_tags(response_text)
            
            if final_response.strip():
                if len(final_response) > 2000:
                    await status_msg.delete()
                    chunks = [final_response[i:i+2000] for i in range(0, len(final_response), 2000)]
                    for chunk in chunks:
                        await message.channel.send(chunk)
                else:
                    await status_msg.edit(content=final_response)
            else:
                await status_msg.edit(content="_[Response contained only thinking process]_")
        else:
            await status_msg.edit(content="Sorry, I couldn't generate a response.")
            
    except Exception as e:
        logger.error(f"Error in on_message: {e}", exc_info=True)
        try:
            await status_msg.edit(content="An error occurred while processing your message.")
        except:
            pass

# Run the bot
if __name__ == "__main__":
    if DISCORD_TOKEN == 'your-discord-bot-token-here':
        logger.error("Please set your DISCORD_BOT_TOKEN environment variable")
        logger.info("You can create a bot at: https://discord.com/developers/applications")
    elif not CHANNEL_IDS or CHANNEL_IDS == {0}:
        logger.error("Please set your DISCORD_CHANNEL_IDS environment variable")
        logger.info("Right-click channels in Discord (with Developer Mode on) and click 'Copy ID'")
        logger.info("Format: DISCORD_CHANNEL_IDS=123456789,987654321,111222333")
    else:
        logger.info("Starting bot...")
        bot.run(DISCORD_TOKEN)
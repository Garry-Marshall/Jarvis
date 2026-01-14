"""
Main bot entry point.
Initializes and runs the Discord bot with graceful shutdown support.
"""
import logging
import sys

from config.settings import DISCORD_TOKEN
from utils.logging_config import setup_logging
from core.bot_instance import get_bot
from core.events import setup_events
from core.shutdown_handler import setup_shutdown_handlers

# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the bot."""
    # Validate token
    if not DISCORD_TOKEN or DISCORD_TOKEN == 'your-discord-bot-token-here':
        logger.error("❌ DISCORD_BOT_TOKEN not set in .env file!")
        logger.error("Please edit the .env file and add your bot token.")
        sys.exit(1)
    
    # Get bot instance
    bot = get_bot()
    
    # Setup event handlers
    setup_events(bot)
    
    # Setup graceful shutdown handlers
    setup_shutdown_handlers(bot)
    
    # Run the bot
    try:
        logger.info("🚀 Starting bot...")
        bot.run(DISCORD_TOKEN, log_handler=None)  # We handle logging ourselves
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
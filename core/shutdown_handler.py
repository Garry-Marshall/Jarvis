"""
Graceful shutdown handler.
Ensures stats and settings are saved before bot exits.
"""
import signal
import sys
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)


class ShutdownHandler:
    """
    Handles graceful shutdown of the bot.
    
    Saves all data and cleans up resources before exit.
    """
    
    def __init__(self, bot):
        """
        Initialize shutdown handler.
        
        Args:
            bot: Discord bot instance
        """
        self.bot = bot
        self.shutdown_initiated = False
        
    async def cleanup(self):
        """Perform cleanup operations before shutdown."""
        if self.shutdown_initiated:
            return
        
        self.shutdown_initiated = True
        logger.info("🛑 Initiating graceful shutdown...")
        
        try:
            # Save statistics
            logger.info("💾 Saving statistics...")
            from utils.stats_manager import save_stats
            save_stats()
            logger.info("✅ Statistics saved")
            
        except Exception as e:
            logger.error(f"❌ Error saving statistics: {e}", exc_info=True)
        
        try:
            # Save guild settings
            logger.info("💾 Saving guild settings...")
            from utils.settings_manager import save_guild_settings
            save_guild_settings()
            logger.info("✅ Guild settings saved")
            
        except Exception as e:
            logger.error(f"❌ Error saving guild settings: {e}", exc_info=True)
        
        try:
            # Disconnect from all voice channels
            logger.info("🔇 Disconnecting from voice channels...")
            from commands.voice import voice_clients
            
            disconnect_tasks = []
            for guild_id, voice_client in list(voice_clients.items()):
                if voice_client.is_connected():
                    disconnect_tasks.append(voice_client.disconnect())
            
            if disconnect_tasks:
                await asyncio.gather(*disconnect_tasks, return_exceptions=True)
                logger.info(f"✅ Disconnected from {len(disconnect_tasks)} voice channel(s)")
            
        except Exception as e:
            logger.error(f"❌ Error disconnecting from voice: {e}", exc_info=True)
        
        try:
            # Close the bot connection
            logger.info("🔌 Closing bot connection...")
            await self.bot.close()
            logger.info("✅ Bot connection closed")
            
        except Exception as e:
            logger.error(f"❌ Error closing bot connection: {e}", exc_info=True)
        
        logger.info("👋 Shutdown complete")
    
    def handle_signal(self, sig, frame):
        """
        Handle system signals (SIGINT, SIGTERM).
        
        Args:
            sig: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(sig).name
        logger.info(f"📡 Received signal: {signal_name}")
        
        # Create cleanup task
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Schedule cleanup
        if loop.is_running():
            asyncio.create_task(self.cleanup())
        else:
            loop.run_until_complete(self.cleanup())
            loop.close()
        
        sys.exit(0)


def setup_shutdown_handlers(bot):
    """
    Register signal handlers for graceful shutdown.
    
    Args:
        bot: Discord bot instance
    """
    handler = ShutdownHandler(bot)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, handler.handle_signal)   # Ctrl+C
    signal.signal(signal.SIGTERM, handler.handle_signal)  # Kill command
    
    # On Windows, also handle SIGBREAK (Ctrl+Break)
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, handler.handle_signal)
    
    logger.info("✅ Shutdown handlers registered (SIGINT, SIGTERM)")
    
    return handler
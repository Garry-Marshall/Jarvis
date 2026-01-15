"""
File utilities for size validation and formatting.
Provides common file handling patterns used across the application.
"""
import logging
from typing import Optional, Tuple
import discord

from config.constants import BYTES_PER_MB

logger = logging.getLogger(__name__)


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in bytes to human-readable format.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted size string (e.g., "2.45MB")
    """
    size_mb = size_bytes / BYTES_PER_MB
    return f"{size_mb:.2f}MB"


async def validate_file_size(
    attachment: discord.Attachment,
    max_size_mb: int,
    file_type: str,
    channel: discord.TextChannel
) -> Tuple[bool, Optional[str]]:
    """
    Validate file size against maximum and send error message if invalid.
    
    Args:
        attachment: Discord attachment to validate
        max_size_mb: Maximum allowed size in megabytes
        file_type: Type of file for error message (e.g., "Image", "PDF", "Text file")
        channel: Discord channel for sending error messages
        
    Returns:
        Tuple of (is_valid, error_message)
        error_message is None if valid
    """
    if attachment.size > max_size_mb * BYTES_PER_MB:
        size_str = format_file_size(attachment.size)
        error_msg = (
            f"⚠️ {file_type} **{attachment.filename}** is too large "
            f"({size_str}). Maximum size is {max_size_mb}MB."
        )
        
        logger.warning(
            f"{file_type} too large: {size_str} (max: {max_size_mb}MB) - {attachment.filename}"
        )
        
        # Send error message to channel
        await channel.send(error_msg)
        
        return False, error_msg
    
    return True, None


def log_file_processing(filename: str, size_bytes: int, file_type: str) -> None:
    """
    Log file processing information.
    
    Args:
        filename: Name of the file
        size_bytes: Size in bytes
        file_type: Type of file (for logging context)
    """
    size_kb = size_bytes / 1024
    logger.info(f"Processing {file_type}: {filename} ({size_kb:.2f}KB)")

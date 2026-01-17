"""
Web search service using DDGS (Dux Distributed Global Search).
Provides search functionality with cooldown management.
"""
import logging
import time
from utils.logging_config import guild_debug_log
from typing import Optional, Dict, List, Tuple
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from ddgs import DDGS

from config.constants import (
    SEARCH_TRIGGERS,
    NEGATIVE_SEARCH_TRIGGERS,
    MIN_MESSAGE_LENGTH_FOR_SEARCH,
    MAX_SEARCH_RESULTS,
    SEARCH_COOLDOWN_CLEANUP,
    SEARCH_RATE_LIMIT_USER_PER_MINUTE,
    SEARCH_RATE_LIMIT_USER_PER_HOUR,
    SEARCH_RATE_LIMIT_USER_COOLDOWN,
    SEARCH_RATE_LIMIT_GUILD_PER_MINUTE,
    SEARCH_RATE_LIMIT_GUILD_PER_HOUR,
    SEARCH_RATE_LIMIT_GUILD_COOLDOWN,
)
from config.settings import SEARCH_COOLDOWN


logger = logging.getLogger(__name__)

# Track search cooldowns per guild (legacy, kept for compatibility)
search_cooldowns: Dict[int, float] = {}


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    calls_per_minute: int
    calls_per_hour: int
    cooldown_seconds: int


# Different rate limits for different contexts (from constants.py)
RATE_LIMITS = {
    'per_user': RateLimitConfig(
        calls_per_minute=SEARCH_RATE_LIMIT_USER_PER_MINUTE,
        calls_per_hour=SEARCH_RATE_LIMIT_USER_PER_HOUR,
        cooldown_seconds=SEARCH_RATE_LIMIT_USER_COOLDOWN
    ),
    'per_guild': RateLimitConfig(
        calls_per_minute=SEARCH_RATE_LIMIT_GUILD_PER_MINUTE,
        calls_per_hour=SEARCH_RATE_LIMIT_GUILD_PER_HOUR,
        cooldown_seconds=SEARCH_RATE_LIMIT_GUILD_COOLDOWN
    ),
}

# Track user and guild rate limits separately
user_search_history: Dict[int, List[datetime]] = defaultdict(list)
guild_search_history: Dict[int, List[datetime]] = defaultdict(list)


def check_rate_limit(user_id: int, guild_id: int) -> Tuple[bool, str]:
    """
    Check if user/guild is within rate limits.

    Args:
        user_id: Discord user ID
        guild_id: Discord guild ID

    Returns:
        Tuple of (allowed, error_message)
    """
    current_time = datetime.now()

    # Check per-user limits
    user_history = user_search_history[user_id]
    # Clean old entries (older than 1 hour)
    user_history[:] = [ts for ts in user_history if current_time - ts < timedelta(hours=1)]

    # Check minute limit for user
    recent_user = [ts for ts in user_history if current_time - ts < timedelta(minutes=1)]
    if len(recent_user) >= RATE_LIMITS['per_user'].calls_per_minute:
        return False, f"⏱️ You're searching too frequently. Please wait {RATE_LIMITS['per_user'].cooldown_seconds} seconds."

    # Check hour limit for user
    if len(user_history) >= RATE_LIMITS['per_user'].calls_per_hour:
        return False, f"⏱️ You've reached your hourly search limit ({RATE_LIMITS['per_user'].calls_per_hour}). Please try again later."

    # Check per-guild limits
    guild_history = guild_search_history[guild_id]
    guild_history[:] = [ts for ts in guild_history if current_time - ts < timedelta(hours=1)]

    # Check minute limit for guild
    recent_guild = [ts for ts in guild_history if current_time - ts < timedelta(minutes=1)]
    if len(recent_guild) >= RATE_LIMITS['per_guild'].calls_per_minute:
        return False, f"⏱️ This server is searching too frequently. Please wait a moment."

    # Record this search
    user_history.append(current_time)
    guild_history.append(current_time)

    return True, ""


def cleanup_old_cooldowns() -> None:
    """Remove search cooldowns older than 1 hour to prevent memory leak."""
    current_time = time.time()
    old_guilds = [
        guild_id for guild_id, timestamp in search_cooldowns.items()
        if current_time - timestamp > SEARCH_COOLDOWN_CLEANUP  # 1 hour
    ]
    
    for guild_id in old_guilds:
        del search_cooldowns[guild_id]
    
    if old_guilds:
        logger.debug(f"Cleaned up {len(old_guilds)} old search cooldowns")


async def get_web_context(
    query: str,
    max_results: int = MAX_SEARCH_RESULTS,
    region: str = "wt-wt",  # Worldwide
    safesearch: str = "moderate",
    backend: str = "auto",  # Let DDGS choose best backend
    guild_id: Optional[int] = None,
    user_id: Optional[int] = None  # NEW: for rate limiting
) -> str:
    """
    Fetch search snippets from DDGS metasearch with rate limiting.

    Args:
        query: Search query
        max_results: Maximum number of results to fetch
        region: Search region (wt-wt for worldwide, us-en, etc.)
        safesearch: Safe search setting (on, moderate, off)
        backend: Search backend(s) to use (auto, duckduckgo, google, bing, etc.)
        guild_id: Guild ID for debug logging (optional)
        user_id: User ID for rate limiting (optional)

    Returns:
        Formatted search results string, or empty string if failed
    """
    # Check rate limits
    if user_id and guild_id:
        allowed, error_msg = check_rate_limit(user_id, guild_id)
        if not allowed:
            logger.info(f"Rate limit hit for user {user_id} in guild {guild_id}")
            guild_debug_log(guild_id, "info", f"Search rate limit: {error_msg}")
            return f"\n{error_msg}\n"

    guild_debug_log(guild_id, "info", f"Web search initiated: '{query[:50]}...'")
    guild_debug_log(guild_id, "debug", f"Search params: max_results={max_results}, region={region}, backend={backend}")
    
    try:
        # Initialize DDGS with timeout and optional proxy
        ddgs = DDGS(timeout=10)  # Increase timeout for reliability
        
        # Perform search with backend selection
        results = ddgs.text(
            query=query,
            region=region,
            safesearch=safesearch,
            max_results=max_results,
            backend=backend
        )
        
        if not results:
            logger.warning(f"No search results for: {query}")
            guild_debug_log(guild_id, "info", "Web search returned no results")
            return ""
        
        guild_debug_log(guild_id, "info", f"Web search found {len(results)} result(s)")
        
        # Format results with source attribution
        formatted_results = []
        for i, r in enumerate(results, 1):
            title = r.get('title', 'No title')
            href = r.get('href', 'No URL')
            body = r.get('body', 'No description')
            
            formatted_results.append(
                f"[{i}] {title}\n"
                f"URL: {href}\n"
                f"Summary: {body}\n"
            )
        
        context = "\n".join(formatted_results)
        return f"\n--- WEB SEARCH RESULTS ({len(results)} sources) ---\n{context}--------------------------\n"
            
    except Exception as e:
        logger.error(f"Search error for '{query}': {e}", exc_info=True)
        # Try fallback to DuckDuckGo only if auto fails
        if backend == "auto":
            try:
                guild_debug_log(guild_id, "info", "Retrying search with DuckDuckGo backend only...")
                ddgs = DDGS(timeout=10)
                results = ddgs.text(
                    query=query,
                    region=region,
                    safesearch=safesearch,
                    max_results=max_results,
                    backend="duckduckgo"
                )
                if results:
                    formatted_results = []
                    for i, r in enumerate(results, 1):
                        formatted_results.append(
                            f"[{i}] {r.get('title', 'No title')}\n"
                            f"URL: {r.get('href', 'No URL')}\n"
                            f"Summary: {r.get('body', 'No description')}\n"
                        )
                    context = "\n".join(formatted_results)
                    return f"\n--- WEB SEARCH RESULTS ({len(results)} sources) ---\n{context}--------------------------\n"
            except Exception as fallback_error:
                logger.error(f"Fallback search also failed: {fallback_error}")
        return ""


def should_trigger_search(message_text: str) -> bool:
    """
    Determine if a message should trigger a web search.
    
    Args:
        message_text: User's message text
        
    Returns:
        True if search should be triggered
    """
    # Check message length
    if len(message_text) < MIN_MESSAGE_LENGTH_FOR_SEARCH:
        return False
    
    message_lower = message_text.lower()
    
    # Check for search triggers
    has_search_trigger = any(trigger in message_lower for trigger in SEARCH_TRIGGERS)
    
    # Check if user is referencing a local file/document
    is_referencing_file = any(neg in message_lower for neg in NEGATIVE_SEARCH_TRIGGERS)
    
    # Only search if triggered AND NOT talking about an attachment
    return has_search_trigger and not is_referencing_file


def check_search_cooldown(guild_id: Optional[int]) -> Optional[int]:
    """
    Check if search is on cooldown for a guild.
    
    Args:
        guild_id: Guild ID to check (None for DMs)
        
    Returns:
        Remaining cooldown seconds, or None if not on cooldown
    """
    if not guild_id:
        return None  # No cooldown for DMs
    
    last_search = search_cooldowns.get(guild_id, 0)
    time_since_search = time.time() - last_search
    
    if time_since_search < SEARCH_COOLDOWN:
        remaining = int(SEARCH_COOLDOWN - time_since_search)
        return remaining
    
    return None


def update_search_cooldown(guild_id: Optional[int]) -> None:
    """
    Update the search cooldown timestamp for a guild.
    
    Args:
        guild_id: Guild ID (None for DMs)
    """
    if guild_id:
        search_cooldowns[guild_id] = time.time()
        guild_debug_log(guild_id, "info", f"Search cooldown updated for guild {guild_id}")
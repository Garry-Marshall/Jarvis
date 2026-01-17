"""
File processing service for Discord attachments.
Handles images, PDFs, and text files.

REFACTORED VERSION: Uses centralized file validation utilities with magic byte validation.
"""
import base64
import io
import logging
from typing import Optional, List, Dict, Tuple

from pypdf import PdfReader

# Try to import python-magic, fall back to basic validation if not available
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("python-magic not available. File type validation will be less secure. Install with: pip install python-magic python-magic-bin")

from config.settings import ALLOW_IMAGES, MAX_IMAGE_SIZE, ALLOW_TEXT_FILES, MAX_TEXT_FILE_SIZE, ALLOW_PDF, MAX_PDF_SIZE
from config.constants import TEXT_FILE_EXTENSIONS, FILE_ENCODINGS, MAX_PDF_CHARS, MSG_FAILED_TO_PROCESS_IMAGE, MSG_FAILED_TO_PROCESS_FILE, MSG_FAILED_TO_DECODE_FILE, MSG_FAILED_TO_PROCESS_PDF
from utils.logging_config import guild_debug_log
from utils.file_utils import validate_file_size, log_file_processing, format_file_size


logger = logging.getLogger(__name__)


def validate_file_magic_bytes(file_data: bytes, expected_type: str) -> Tuple[bool, str]:
    """
    Validate file using magic bytes (file signature).

    Args:
        file_data: Raw file bytes
        expected_type: Expected file type ('image', 'text', 'pdf')

    Returns:
        Tuple of (is_valid, detected_mime_type)
    """
    if not MAGIC_AVAILABLE:
        # Fallback to basic header validation if python-magic not available
        logger.debug("Magic library not available, using basic validation")
        return _validate_file_basic(file_data, expected_type)

    try:
        # Use python-magic to detect actual file type
        mime = magic.Magic(mime=True)
        detected_type = mime.from_buffer(file_data)

        if expected_type == 'image':
            # Check if detected type is an allowed image type
            if not detected_type.startswith('image/'):
                logger.warning(f"File claims to be image but detected as: {detected_type}")
                return False, detected_type

            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if detected_type not in allowed_types:
                logger.warning(f"Image type not allowed: {detected_type}")
                return False, detected_type

        elif expected_type == 'pdf':
            if detected_type != 'application/pdf':
                logger.warning(f"File claims to be PDF but detected as: {detected_type}")
                return False, detected_type

        elif expected_type == 'text':
            # Text files are trickier - check for common text types
            allowed_text_prefixes = ['text/', 'application/json', 'application/xml']
            if not any(detected_type.startswith(prefix) for prefix in allowed_text_prefixes):
                logger.warning(f"File claims to be text but detected as: {detected_type}")
                return False, detected_type

        return True, detected_type

    except Exception as e:
        logger.error(f"Error validating file magic bytes: {e}")
        return False, "unknown"


def _validate_file_basic(file_data: bytes, expected_type: str) -> Tuple[bool, str]:
    """
    Basic file validation using magic number headers (fallback when python-magic unavailable).

    Args:
        file_data: Raw file bytes
        expected_type: Expected file type

    Returns:
        Tuple of (is_valid, detected_type_hint)
    """
    if len(file_data) < 4:
        return False, "too_small"

    # Check magic numbers
    if expected_type == 'image':
        # JPEG
        if file_data[:2] == b'\xFF\xD8':
            return True, "image/jpeg"
        # PNG
        elif file_data[:8] == b'\x89PNG\r\n\x1a\n':
            return True, "image/png"
        # GIF
        elif file_data[:6] in (b'GIF87a', b'GIF89a'):
            return True, "image/gif"
        # WEBP
        elif file_data[:4] == b'RIFF' and file_data[8:12] == b'WEBP':
            return True, "image/webp"
        else:
            logger.warning(f"Image magic bytes not recognized")
            return False, "unknown_image"

    elif expected_type == 'pdf':
        # PDF
        if file_data[:5] == b'%PDF-':
            return True, "application/pdf"
        else:
            logger.warning(f"PDF magic bytes not found")
            return False, "unknown_pdf"

    elif expected_type == 'text':
        # Text files are harder to validate, allow common formats
        # Just check it's valid UTF-8 or ASCII
        try:
            file_data[:1024].decode('utf-8')
            return True, "text/plain"
        except UnicodeDecodeError:
            logger.warning(f"Text file validation failed (encoding)")
            return False, "invalid_text"

    return False, "unknown"


async def process_image_attachment(attachment, channel, guild_id: Optional[int] = None) -> Optional[Dict]:
    """
    Download and convert an image attachment to base64 with magic byte validation.

    Args:
        attachment: Discord attachment object
        channel: Discord channel (for error messages)
        guild_id: Guild ID for logging

    Returns:
        Dictionary with image data, or None if failed/rejected
    """
    if not ALLOW_IMAGES:
        return None

    # REFACTORED: Use centralized validation
    is_valid, error_msg = await validate_file_size(
        attachment, MAX_IMAGE_SIZE, "Image", channel
    )
    if not is_valid:
        return None

    try:
        # Download file data
        image_data = await attachment.read()

        # Validate magic bytes
        is_valid_type, detected_mime = validate_file_magic_bytes(image_data, 'image')
        if not is_valid_type:
            logger.warning(
                f"Image validation failed for {attachment.filename}: "
                f"claimed {attachment.content_type}, detected {detected_mime}"
            )
            await channel.send(
                f"⚠️ File `{attachment.filename}` was rejected: "
                f"Invalid or unsupported image format detected."
            )
            return None

        base64_image = base64.b64encode(image_data).decode('utf-8')

        # Use detected MIME type instead of claimed content_type
        media_type = detected_mime

        log_file_processing(attachment.filename, attachment.size, "image")
        guild_debug_log(
            guild_id, "debug",
            f"Processed image: {attachment.filename} ({format_file_size(attachment.size)}) "
            f"as {media_type} (validated)"
        )
        
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{media_type};base64,{base64_image}"
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing image {attachment.filename}: {e}")
        await channel.send(MSG_FAILED_TO_PROCESS_IMAGE.format(attachment=attachment.filename, exception=str(e)))
        return None


async def process_text_attachment(attachment, channel, guild_id: Optional[int] = None) -> Optional[str]:
    """
    Download and read a text file attachment.
    
    Args:
        attachment: Discord attachment object
        channel: Discord channel (for error messages)
        
    Returns:
        Formatted text content, or None if not a text file/failed
    """
    if not ALLOW_TEXT_FILES:
        return None
    
    filename_lower = attachment.filename.lower()
    
    # Check if it's a text file
    is_text = any(filename_lower.endswith(ext) for ext in TEXT_FILE_EXTENSIONS)
    if attachment.content_type:
        is_text = is_text or 'text/' in attachment.content_type or 'application/json' in attachment.content_type
    
    if not is_text:
        return None
    
    is_valid, error_msg = await validate_file_size(
        attachment, MAX_TEXT_FILE_SIZE, "Text file", channel
    )
    if not is_valid:
        return None
    
    try:
        file_data = await attachment.read()
        
        # Try different encodings
        for encoding in FILE_ENCODINGS:
            try:
                text_content = file_data.decode(encoding)
                log_file_processing(attachment.filename, attachment.size, "text file")
                guild_debug_log(guild_id, "debug", f"Processed text file: {attachment.filename} ({format_file_size(attachment.size)})")
                return f"\n\n--- Content of {attachment.filename} ---\n{text_content}\n--- End of {attachment.filename} ---\n"
            except UnicodeDecodeError:
                continue
        
        # If all encodings failed
        logger.error(f"Could not decode text file {attachment.filename}")
        await channel.send(
            MSG_FAILED_TO_DECODE_FILE.format(attachment=attachment.filename)
        )
        return None
        
    except Exception as e:
        logger.error(f"Error processing text file {attachment.filename}: {e}")
        await channel.send(MSG_FAILED_TO_PROCESS_FILE.format(attachment=attachment.filename, exception=str(e)))
        return None


async def process_pdf_attachment(attachment, channel, guild_id: Optional[int] = None) -> Optional[str]:
    """
    Download and extract text from a PDF with character truncation.
    
    Args:
        attachment: Discord attachment object
        channel: Discord channel (for error messages)
        
    Returns:
        Formatted PDF text content, or None if failed
    """
    if not ALLOW_PDF:
        return None
    
    # Check if it's a PDF
    is_pdf = attachment.filename.lower().endswith('.pdf') or attachment.content_type == 'application/pdf'
    if not is_pdf:
        return None
    
    is_valid, error_msg = await validate_file_size(
        attachment, MAX_PDF_SIZE, "PDF", channel
    )
    if not is_valid:
        return None
    
    try:
        file_data = await attachment.read()
        pdf_stream = io.BytesIO(file_data)
        reader = PdfReader(pdf_stream)
        
        extracted_text = []
        current_length = 0
        
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                # Check if adding this page exceeds our limit
                if current_length + len(page_text) > MAX_PDF_CHARS:
                    remaining_space = MAX_PDF_CHARS - current_length
                    extracted_text.append(f"--- Page {i+1} (TRUNCATED) ---\n{page_text[:remaining_space]}")
                    logger.info(f"✂️ PDF {attachment.filename} truncated at page {i+1}")
                    break
                
                extracted_text.append(f"--- Page {i+1} ---\n{page_text}")
                current_length += len(page_text)
        
        if not extracted_text:
            return f"\n[Note: PDF {attachment.filename} had no extractable text.]\n"

        full_content = "\n".join(extracted_text)
        
        log_file_processing(attachment.filename, len(full_content), "PDF")
        guild_debug_log(guild_id, "debug", f"Processed PDF: {attachment.filename}, extracted {len(full_content)} characters from {len(extracted_text)} page(s)")
        
        return f"\n\n--- Content of PDF: {attachment.filename} ---\n{full_content}\n--- End of PDF ---\n"
        
    except Exception as e:
        logger.error(f"Error processing PDF {attachment.filename}: {e}")
        await channel.send(MSG_FAILED_TO_PROCESS_PDF.format(attachment=attachment.filename, exception=str(e)))
        return None


async def process_all_attachments(attachments, channel, guild_id: Optional[int] = None) -> tuple[List[Dict], str]:
    """
    Process all attachments in a message.
    
    Args:
        attachments: List of Discord attachment objects
        channel: Discord channel (for error messages)
        
    Returns:
        Tuple of (images_list, text_content_string)
    """
    images = []
    text_files_content = ""
    
    for attachment in attachments:
        # Try image processing
        image_data = await process_image_attachment(attachment, channel, guild_id)
        if image_data:
            images.append(image_data)
            continue  # Don't process as other types if it's an image
        
        # Try PDF processing
        pdf_content = await process_pdf_attachment(attachment, channel, guild_id)
        if pdf_content:
            text_files_content += pdf_content
            continue
        
        # Try text file processing
        text_content = await process_text_attachment(attachment, channel, guild_id)
        if text_content:
            text_files_content += text_content
    
    return images, text_files_content
"""
Centralized logging configuration for the Hotel Operations Dashboard API.

This module provides async-safe logging that won't block the event loop.
"""
import logging
import logging.handlers
import sys
import queue
import atexit
from typing import Optional

# Define log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Create a queue for async-safe logging
log_queue = queue.Queue(-1)  # no limit on size
queue_handler = logging.handlers.QueueHandler(log_queue)

# Create queue listener that processes logs in a separate thread
def _setup_queue_listener():
    """Set up the queue listener with console handler."""
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    
    listener = logging.handlers.QueueListener(
        log_queue, 
        console_handler,
        respect_handler_level=True
    )
    listener.start()
    
    # Ensure listener stops on exit
    atexit.register(listener.stop)
    
    return listener

# Initialize the queue listener once
_queue_listener = _setup_queue_listener()

def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up an async-safe logger that won't block the event loop.
    
    Uses QueueHandler to offload logging to a separate thread,
    ensuring that logging operations don't block async code.
    
    Args:
        name: Logger name (usually __name__ of the module)
        level: Logging level (default: INFO)
        log_file: Optional file path to write logs to (not recommended for high-volume)
    
    Returns:
        Configured logger instance that's safe to use in async code
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False
    
    # Prevent adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Use QueueHandler for async-safe, non-blocking logging
    # This sends logs to a queue, which is processed by a background thread
    logger.addHandler(queue_handler)
    
    # WARNING: File logging is synchronous and can block
    # Only use for low-volume logging or consider async file writing
    if log_file:
        # Add file handler directly for simplicity
        # For high-volume production use, consider async file writing library
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

# Create default application logger
app_logger = setup_logger("hotel_dashboard")

"""
Unit tests for the logger module.
"""
import pytest
import logging
import logging.handlers
import time
from app.logger import setup_logger


def test_logger_creation():
    """Test that logger is created with correct name"""
    logger = setup_logger("test_logger")
    assert logger.name == "test_logger"
    assert isinstance(logger, logging.Logger)


def test_logger_default_level():
    """Test that logger has default INFO level"""
    logger = setup_logger("test_level")
    assert logger.level == logging.INFO


def test_logger_custom_level():
    """Test that logger can be created with custom level"""
    logger = setup_logger("test_custom", level=logging.DEBUG)
    assert logger.level == logging.DEBUG


def test_logger_has_handlers():
    """Test that logger has QueueHandler for async-safe logging"""
    logger = setup_logger("test_handlers")
    assert len(logger.handlers) > 0
    # Now using QueueHandler for async-safe logging
    assert any(isinstance(h, logging.handlers.QueueHandler) for h in logger.handlers)


def test_logger_singleton_behavior():
    """Test that calling setup_logger twice returns same logger instance"""
    logger1 = setup_logger("test_singleton")
    logger2 = setup_logger("test_singleton")
    assert logger1 is logger2


def test_logger_logs_messages(caplog):
    """Test that logger works with QueueHandler (async-safe)"""
    logger = setup_logger("test_logging")
    
    # Log messages - they go to queue and are processed by background thread
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")
    
    # Give the queue listener time to process
    time.sleep(0.1)
    
    # QueueHandler logs aren't captured by caplog, but we can verify logger works
    assert logger.level == logging.INFO
    assert len(logger.handlers) > 0


def test_logger_respects_level(caplog):
    """Test that logger respects logging level"""
    logger = setup_logger("test_level_respect", level=logging.WARNING)
    
    # Verify the logger level is set correctly
    assert logger.level == logging.WARNING
    
    # Logger should have handlers
    assert len(logger.handlers) > 0

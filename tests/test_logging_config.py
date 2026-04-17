"""Logging configuration tests."""

import logging
import tempfile
from pathlib import Path

import pytest

from repo_context.logging_config import (
    setup_logging,
    get_logger,
    LOGGING_INITIALIZED,
)
import repo_context.logging_config as logging_config


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_creates_logger(self) -> None:
        """Test get_logger creates a logger with correct name."""
        logger = get_logger("test_module")
        assert logger.name == "repo_context.test_module"

    def test_get_logger_returns_logging_logger(self) -> None:
        """Test get_logger returns a standard logging.Logger."""
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_with_nested_module(self) -> None:
        """Test get_logger handles nested module names."""
        logger = get_logger("storage.nodes")
        assert logger.name == "repo_context.storage.nodes"

    def test_get_logger_same_logger_for_same_name(self) -> None:
        """Test get_logger returns same logger for same name."""
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        assert logger1 is logger2


class TestSetupLogging:
    """Tests for setup_logging function."""

    def test_setup_logging_initializes_flag(self) -> None:
        """Test setup_logging sets LOGGING_INITIALIZED to True."""
        # Reset flag first
        logging_config.LOGGING_INITIALIZED = False
        
        setup_logging(level="INFO")
        assert logging_config.LOGGING_INITIALIZED is True

    def test_setup_logging_does_not_reinitialize(self, caplog) -> None:
        """Test setup_logging doesn't reinitialize if already set up."""
        logging_config.LOGGING_INITIALIZED = True
        
        with caplog.at_level(logging.WARNING):
            setup_logging(level="INFO")
        
        # Should warn about already initialized
        assert "already initialized" in caplog.text.lower()

    def test_setup_logging_console_handler(self) -> None:
        """Test setup_logging adds console handler."""
        logging_config.LOGGING_INITIALIZED = False
        
        # Clear any existing handlers
        root_logger = logging.getLogger("repo_context")
        root_logger.handlers.clear()
        
        setup_logging(level="INFO")
        
        # Should have at least one handler
        assert len(root_logger.handlers) > 0

    def test_setup_logging_respects_level(self) -> None:
        """Test setup_logging sets correct log level."""
        logging_config.LOGGING_INITIALIZED = False
        
        root_logger = logging.getLogger("repo_context")
        
        setup_logging(level="DEBUG")
        assert root_logger.level == logging.DEBUG
        
        # Reset for next test
        logging_config.LOGGING_INITIALIZED = False
        
        setup_logging(level="WARNING")
        assert root_logger.level == logging.WARNING

    def test_setup_logging_with_file_handler(self) -> None:
        """Test setup_logging creates file handler when log_file provided."""
        logging_config.LOGGING_INITIALIZED = False
        
        root_logger = logging.getLogger("repo_context")
        root_logger.handlers.clear()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            setup_logging(level="INFO", log_file=log_file)
            
            # Should have file handler
            has_file_handler = any(
                isinstance(h, logging.FileHandler)
                for h in root_logger.handlers
            )
            assert has_file_handler
            
            # Log file should exist
            assert log_file.exists()

    def test_setup_logging_default_level_is_info(self) -> None:
        """Test setup_logging default level is INFO."""
        logging_config.LOGGING_INITIALIZED = False
        
        root_logger = logging.getLogger("repo_context")
        
        setup_logging()
        assert root_logger.level == logging.INFO


class TestLoggingLevels:
    """Tests for logging level behavior."""

    def test_debug_messages_logged_at_debug_level(self, caplog) -> None:
        """Test debug messages are logged at DEBUG level."""
        logger = get_logger("test_levels")
        
        # Set logger level to DEBUG for this test
        original_level = logger.level
        logger.setLevel(logging.DEBUG)
        
        try:
            with caplog.at_level(logging.DEBUG, logger="repo_context"):
                logger.debug("Debug message")
            
            assert "Debug message" in caplog.text
        finally:
            logger.setLevel(original_level)

    def test_info_messages_logged_at_info_level(self, caplog) -> None:
        """Test info messages are logged at INFO level."""
        logger = get_logger("test_levels")
        
        with caplog.at_level(logging.INFO, logger="repo_context"):
            logger.info("Info message")
        
        assert "Info message" in caplog.text

    def test_warning_messages_logged_at_warning_level(self, caplog) -> None:
        """Test warning messages are logged at WARNING level."""
        logger = get_logger("test_levels")
        
        with caplog.at_level(logging.WARNING, logger="repo_context"):
            logger.warning("Warning message")
        
        assert "Warning message" in caplog.text

    def test_error_messages_logged_at_error_level(self, caplog) -> None:
        """Test error messages are logged at ERROR level."""
        logger = get_logger("test_levels")
        
        with caplog.at_level(logging.ERROR, logger="repo_context"):
            logger.error("Error message")
        
        assert "Error message" in caplog.text

    def test_debug_not_logged_at_info_level(self, caplog) -> None:
        """Test debug messages not logged when level is INFO."""
        logger = get_logger("test_levels")
        
        # Set logger level to INFO
        original_level = logger.level
        logger.setLevel(logging.INFO)
        
        try:
            with caplog.at_level(logging.DEBUG, logger="repo_context"):
                logger.debug("Debug message")
            
            assert "Debug message" not in caplog.text
        finally:
            logger.setLevel(original_level)


class TestLoggingWithException:
    """Tests for logging with exceptions."""

    def test_exception_logs_stack_trace(self, caplog) -> None:
        """Test logger.exception logs stack trace."""
        logger = get_logger("test_exception")
        
        with caplog.at_level(logging.ERROR):
            try:
                raise ValueError("Test error")
            except ValueError:
                logger.exception("An error occurred")
        
        assert "An error occurred" in caplog.text
        assert "ValueError" in caplog.text

    def test_error_without_exception(self, caplog) -> None:
        """Test logger.error without exception."""
        logger = get_logger("test_exception")
        
        with caplog.at_level(logging.ERROR):
            logger.error("Simple error")
        
        assert "Simple error" in caplog.text
        # Should not have traceback
        assert "Traceback" not in caplog.text

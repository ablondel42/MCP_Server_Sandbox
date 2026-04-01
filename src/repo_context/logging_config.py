"""Logging configuration for the application."""

import logging
import sys
from pathlib import Path
from typing import Optional

# Flag to track if logging has been initialized
LOGGING_INITIALIZED: bool = False


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
) -> None:
    """Configure logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Default is "INFO".
        log_file: Optional file path for log output. If None, only
                  console output is used.
    
    Note:
        This function should be called once at application startup.
        Subsequent calls will log a warning and not reinitialize.
    """
    global LOGGING_INITIALIZED
    
    if LOGGING_INITIALIZED:
        logging.getLogger("repo_context").warning(
            "Logging already initialized, skipping setup"
        )
        return
    
    # Get root logger for repo_context
    root_logger = logging.getLogger("repo_context")
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Create formatter with source location
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d (%(funcName)s): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Console handler - always added
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler - optional
    if log_file is not None:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except (OSError, IOError) as e:
            # If we can't create file handler, log to console only
            console_handler.setLevel(logging.ERROR)
            root_logger.error(
                f"Failed to create log file handler: {e}. Using console only."
            )
    
    LOGGING_INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given module.
    
    Args:
        name: Module name (e.g., "storage.nodes", "cli.main").
              Will be prefixed with "repo_context.".
    
    Returns:
        A configured logger instance.
    
    Example:
        >>> logger = get_logger("storage.nodes")
        >>> logger.info("Processing node")
    """
    return logging.getLogger(f"repo_context.{name}")

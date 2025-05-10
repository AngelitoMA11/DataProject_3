import logging
import sys
from typing import Optional

# Keep track of configured loggers to prevent duplicate configuration
_configured_loggers = set()

def setup_logger(
    name: str,
    level: int = logging.DEBUG,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Configure and return a logger with the specified settings.
    Ensures only one handler per logger to prevent duplicate logs.
    
    Args:
        name: The name of the logger
        level: The logging level (default: DEBUG)
        format_string: Optional custom format string for the log messages
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # If logger is already configured, return it
    if name in _configured_loggers:
        return logging.getLogger(name)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove any existing handlers
    logger.handlers = []
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Create formatter
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(format_string)
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False
    
    # Mark logger as configured
    _configured_loggers.add(name)
    
    return logger

# Create a default logger instance
logger = setup_logger('api_agent') 
import logging

logger = logging.getLogger("droidrun")
logger.propagate = False  # Don't send to root logger
logger.handlers = []      # No handlers by default
logger.setLevel(logging.INFO)  # Or WARNING
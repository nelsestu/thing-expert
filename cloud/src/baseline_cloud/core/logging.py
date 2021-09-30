import logging

from baseline_cloud.core.config import config

logger = logging.getLogger(config.app_name)
logger.setLevel(logging.INFO)

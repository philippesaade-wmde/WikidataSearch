import logging
import sys
import os

def get_logger(name):
    # Create a logger
    # Source: https://docs.python.org/3/howto/logging.html

    mounted_dir = os.environ.get("TOOL_DATA_DIR", "/")
    logs_path = os.path.join(mounted_dir, 'wdchat_api.log')

    logging.basicConfig(
        filename=logs_path,
        encoding='utf-8',
        level=logging.DEBUG
    )

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Set the logging level

    # Create console handler and set level to debug
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

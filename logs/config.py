from logging.handlers import RotatingFileHandler
from pathlib import Path
import logging
import sys
import os

def log_config(filename, base_path=None):
    script_name = os.path.basename(filename)
    if base_path is None:
        base_path = Path.cwd()

    log_dir = base_path / 'logs'
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"{Path(filename).stem}.log"

    # Set up the RotatingFileHandler
    file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024*10, backupCount=10, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s')
    file_handler.setFormatter(formatter)

    # Create a logger instance
    logger = logging.getLogger(script_name)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)

    # Ensure sys.stdout is using UTF-8
    sys.stdout.reconfigure(encoding='utf-8')

    return logger
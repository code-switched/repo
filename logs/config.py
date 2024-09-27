from logging.handlers import RotatingFileHandler
import logging
import sys
import os

def log_config(script_path):
    script_name = os.path.basename(script_path)
    log_name = script_name.rsplit('.', 1)[0] + '.log'
    log_file = os.path.join('logs', log_name)

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
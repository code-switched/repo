from logging.handlers import RotatingFileHandler
import logging
import sys
import os

def log_config(script_path):
    script_name = os.path.basename(script_path)
    log_name = script_name.rsplit('.', 1)[0] + '.log'
    log_file = os.path.join('logs', log_name)

    # Set up the RotatingFileHandler
    file_handler = RotatingFileHandler(log_file, maxBytes=1024*1024*10, backupCount=5, encoding='utf-8')  # 10 MB per file, keep 5 backup files
    formatter = logging.Formatter('%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s')
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger
    logger = logging.getLogger()
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)

    # Ensure sys.stdout is using UTF-8
    sys.stdout.reconfigure(encoding='utf-8')

    return logger
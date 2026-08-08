import logging
import os
import sys


def setup_logger():
    os.makedirs('logs', exist_ok=True)

    logger = logging.getLogger("SystemLogger")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler('logs/system.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # colorization for console
    class ColorFormatter(logging.Formatter):
        grey = "\x1b[38;20m"
        yellow = "\x1b[33;20m"
        red = "\x1b[31;20m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"
        format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

        FORMATS = {
            logging.DEBUG: grey + format + reset,
            logging.INFO: grey + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
            logging.WARNING: yellow + format + reset,
            logging.ERROR: red + format + reset,
            logging.CRITICAL: bold_red + format + reset
        }

        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno)
            formatter = logging.Formatter(log_fmt)
            return formatter.format(record)

    console_handler.setFormatter(ColorFormatter())

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

logger = setup_logger()

# https://docs.python.org/3/howto/logging.html#logging-basic-tutorial
# https://www.toptal.com/python/in-depth-python-logging
import logging
import sys

LOG_FORMATTER = logging.Formatter("%(asctime)s[%(levelname)s][%(name)s]: %(message)s", datefmt='%Y-%m-%dT%H:%M:%S%z')


def get_console_handler(log_level):
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(LOG_FORMATTER)
    console_handler.setLevel(log_level)
    return console_handler


def get_logger_with_name(log_name, log_level_console="INFO"):
    logger = logging.getLogger(log_name)
    # With this pattern, it's rarely necessary to propagate the error up to parent
    logger.propagate = False
    # Set the root logger to the lowest level so its handlers set logging limits instead
    logger.setLevel(logging.DEBUG)

    # If the logger was initialized earlier, an old handler might be hanging around. Remove it.
    for handler in logger.handlers:
        logger.removeHandler(handler)

    logger.addHandler(get_console_handler(log_level_console))

    return logger

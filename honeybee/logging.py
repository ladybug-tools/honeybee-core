import logging
from logging.handlers import TimedRotatingFileHandler


def get_logger(name):
    """Get a logger to be used for each module.

    Use this only once in __init__.py file.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)


    # create a file handler to log debug and higher level logs
    _file_handler = TimedRotatingFileHandler('honeybee.log', when='midnight')
    _file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _file_handler.setFormatter(_file_format)
    _file_handler.setLevel(logging.DEBUG)

    # create a console handler that only prints out errors and warnings
    _stream_handler = logging.StreamHandler()
    _stream_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    _stream_handler.setFormatter(_stream_format)
    _stream_handler.setLevel(logging.WARNING)

    logger.addHandler(_file_handler)
    logger.addHandler(_stream_handler)

    return logger

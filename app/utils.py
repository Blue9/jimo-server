import logging
import sys


def get_logger(name: str):
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('[%(asctime)s  %(module)s:%(funcName)s] %(levelname)s: %(message)s'))
    log.addHandler(handler)
    return log

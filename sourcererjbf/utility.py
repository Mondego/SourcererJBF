import logging


def create_logger(name):
  logger = logging.getLogger(name)
  logger.setLevel(logging.DEBUG)
  fh = logging.FileHandler(name + ".log")
  fh.setLevel(logging.INFO)
  formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
  fh.setFormatter(formatter)
  logger.addHandler(fh)
  return logger


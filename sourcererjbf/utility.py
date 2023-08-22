import logging
import hashlib
import os.path
from subprocess import check_output

from sourcererjbf.constants import TIMEOUT_SECONDS


def create_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(name + ".log")
    fh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


def getHash_for_class_files(class_file_paths):
    hash_path_pairs = {}
    for cfp in class_file_paths:
        cls_hash = get_md5_hash(cfp)
        hash_path_pairs[cls_hash] = cfp
    return hash_path_pairs


def get_md5_hash(file_path):
    if os.path.exists(file_path):
        checksum = check_output(["sha256sum", file_path], timeout=TIMEOUT_SECONDS, encoding='utf8')
        value = checksum.split()[0]
        return value

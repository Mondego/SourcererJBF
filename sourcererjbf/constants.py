from utils import create_logger

PARTMAP = "TBUILD/project_compile_temp{0}.shelve"
TEMPDIR = "TBUILD/BUILD_{0}/"
TIMEOUT_SECONDS = 1800


# LOGGER = create_logger("COMPILE.log")
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

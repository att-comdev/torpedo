import urllib3
import logging


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger('m1')
log_level = 20
logger.setLevel(log_level)
# set console logging. Change to file by changing to FileHandler
stream_handle = logging.StreamHandler()
# Set logging format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(filename)s -- '
                              '%(message)s')
stream_handle.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(stream_handle)

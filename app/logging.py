import logging
import sys

INFO_FMT = "%(asctime)s - %(levelname)s: %(message)s"
ERROR_FMT = "%(asctime)s - %(levelname)s: %(module)s.%(funcName)s:%(lineno)d - %(message)s"


class LeveledFormatter(logging.Formatter):
    _formats = {}

    def __init__(self, *args, **kwargs):
        super(LeveledFormatter, self).__init__(*args, **kwargs)

    def set_formatter(self, level, formatter):
        self._formats[level] = formatter

    def format(self, record):
        f = self._formats.get(record.levelno)

        if f is None:
            f = super(LeveledFormatter, self)

        return f.format(record)


datefmt = "%Y-%m-%d %H:%M:%S"

formatter = LeveledFormatter(INFO_FMT)
formatter.set_formatter(
    logging.INFO, logging.Formatter(INFO_FMT, datefmt=datefmt)
)
formatter.set_formatter(
    logging.ERROR, logging.Formatter(ERROR_FMT, datefmt=datefmt)
)
formatter.set_formatter(
    logging.DEBUG, logging.Formatter(ERROR_FMT, datefmt=datefmt)
)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler("logs/logging_errors.log")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.ERROR)

logger = logging.getLogger("HandlersApp")

# Disable error logs while running unit tests
if sys.argv[0].split("/")[-1] in ["pytest"]:
    logging.disable(logging.ERROR)

logger.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)
logger.addHandler(file_handler)

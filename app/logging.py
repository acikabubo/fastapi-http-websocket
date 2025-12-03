import logging
import sys

from app.settings import app_settings


def get_correlation_id() -> str:
    """
    Get correlation ID from context, safe wrapper for logging.

    Returns:
        Correlation ID or empty string if not available.
    """
    try:
        from app.middlewares.correlation_id import get_correlation_id as _get_cid

        return _get_cid()
    except Exception:
        return ""


INFO_FMT = "%(asctime)s - [%(correlation_id)s] %(levelname)s: %(message)s"
ERROR_FMT = "%(asctime)s - [%(correlation_id)s] %(levelname)s: %(module)s.%(funcName)s:%(lineno)d - %(message)s"


class LeveledFormatter(logging.Formatter):
    """
    Custom formatter that adds correlation ID and uses different formats per level.

    This formatter:
    - Injects correlation_id into log records
    - Uses different format strings for different log levels
    """

    _formats = {}

    def __init__(self, *args, **kwargs):
        """Initialize the leveled formatter."""
        super(LeveledFormatter, self).__init__(*args, **kwargs)

    def set_formatter(self, level, formatter):
        """
        Set format for a specific log level.

        Args:
            level: The logging level (e.g., logging.INFO).
            formatter: The formatter to use for that level.
        """
        self._formats[level] = formatter

    def format(self, record):
        """
        Format a log record with correlation ID.

        Args:
            record: The log record to format.

        Returns:
            Formatted log string with correlation ID.
        """
        # Inject correlation ID into record
        record.correlation_id = get_correlation_id() or "-"

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
stream_handler.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(app_settings.LOG_FILE_PATH)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.ERROR)

logger = logging.getLogger("HandlersApp")

# Disable error logs while running unit tests
if sys.argv[0].split("/")[-1] in ["pytest"]:
    logging.disable(logging.ERROR)

logger.setLevel(logging.DEBUG)
logger.addHandler(stream_handler)
logger.addHandler(file_handler)

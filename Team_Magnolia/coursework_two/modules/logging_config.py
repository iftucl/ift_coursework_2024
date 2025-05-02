import logging
import sys

def setup_logging(level: str = "INFO") -> None:
    LOG_LEVEL = getattr(logging, level.upper(), logging.INFO)
    fmt = (
        '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
        '"module":"%(module)s","message":%(message)s}'
    )
    logging.basicConfig(
        level=LOG_LEVEL,
        format=fmt,
        stream=sys.stdout,
    )

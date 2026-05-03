# Custom logger class

import logging
import inspect
import sys


DEFAULT_LOG_LEVEL = "INFO"


class CustomLogger:
    def __init__(self, name: str):
        base_level = logging.INFO

        self.logger = logging.getLogger(name)
        self.logger.setLevel(base_level)

        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(base_level)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s | %(lineno)d | %(message)s"
        )
        stdout_handler.setFormatter(formatter)

        self.logger.addHandler(stdout_handler)
    
    def set_level(self, level: str | int):
        if isinstance(level, str):
            level = logging._nameToLevel[level]
        
        self.logger.setLevel(level)
        for handler in self.logger.handlers:
            handler.setLevel(level)
    
    def debug(self, msg: str, **kwargs):
        self._color_log("DEBUG", msg, **kwargs)

    def info(self, msg: str, **kwargs):
        self._color_log("INFO", msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        self._color_log("WARNING", msg, **kwargs)

    def error(self, msg: str, **kwargs):
        self._color_log("ERROR", msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        self._color_log("CRITICAL", msg, **kwargs)

    def _color_log(self, level: str, message: str, **kwargs):
        COLORS = {
            "DEBUG": "\033[94m",
            "INFO": "\033[92m",
            "WARNING": "\033[93m",
            "ERROR": "\033[91m",
            "CRITICAL": "\033[95m"
        }
        color = COLORS[level]
        reset = "\033[0m"

        frame = inspect.currentframe()
        while frame:
            if frame.f_globals.get("__name__") != __name__:
                break
            frame = frame.f_back

        filename = frame.f_code.co_filename if frame else "Unknown"
        lineno = frame.f_lineno if frame else 0

        for handler in self.logger.handlers:
            handler.setFormatter(
                logging.Formatter(
                    f"{color}[%(levelname)s]: %(asctime)s\t| File: {filename} - Line: {lineno} |\tLog: %(name)s\n\t%(message)s{reset}",\
                    datefmt="%Y-%m-%d %H:%M:%S"
                )
            )
        
        getattr(self.logger, level.lower())(message, **kwargs)


logger = CustomLogger("ouichat_backend")
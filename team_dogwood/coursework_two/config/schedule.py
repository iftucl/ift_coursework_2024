from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file
# loaded manually due to subdirectory structure of this project
#       (config dict unable to locate .env file)
load_dotenv()


class ScheduleSettings(BaseSettings):
    """Configuration for scheduling settings.

    This class defines the configuration settings required for scheduling tasks.
    The settings are loaded from environment variables or a `.env` file.

    Attributes:
        SCHEDULE (str): The schedule for running tasks (e.g., "monthly", "weekly", etc.).

    Example:
        >>> schedule_settings = ScheduleSettings()
        >>> print(schedule_settings.SCHEDULE)
        monthly
    """

    FREQUENCY: str = "monthly"
    RUN_NOW: bool = False
    RUN_ONCE: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="SCHEDULE_",
        case_sensitive=True,
        extra="ignore",
    )

    @staticmethod
    def _str_to_bool(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "on"}
        return bool(value)

    @classmethod
    def __get_validators__(cls):
        yield from super().__get_validators__()
        yield cls._convert_run_now_once

    @classmethod
    def _convert_run_now_once(cls, values):
        if "RUN_NOW" in values:
            values["RUN_NOW"] = cls._str_to_bool(values["RUN_NOW"])
        if "RUN_ONCE" in values:
            values["RUN_ONCE"] = cls._str_to_bool(values["RUN_ONCE"])
        return values


schedule_settings = ScheduleSettings()

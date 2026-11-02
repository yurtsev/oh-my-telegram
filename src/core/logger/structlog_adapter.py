"""Structlog-адаптер: JSON-логи с именованным контекстом."""

import inspect
import logging
from typing import Any

import structlog

from src.config import cfg
from src.core.logger.interface import AbstractLogger

SKIP_FRAMES = frozenset(["structlog_adapter.py", "interface.py"])


def configure_structlog() -> None:
	structlog.configure(
		processors=[
			structlog.contextvars.merge_contextvars,
			structlog.processors.add_log_level,
			structlog.dev.set_exc_info,
			structlog.processors.TimeStamper(fmt="iso"),
			structlog.processors.JSONRenderer(ensure_ascii=False),
		],
		context_class=dict,
		logger_factory=structlog.PrintLoggerFactory(),
		cache_logger_on_first_use=True,
		wrapper_class=structlog.make_filtering_bound_logger(
			logging.getLevelNamesMapping().get(
				cfg.logging.level.upper(), logging.INFO
			)
		),
	)


class StructLogger(AbstractLogger):
	def __init__(self, context: dict[str, Any] | None = None) -> None:
		self._context: dict[str, Any] = context or {}

	def _caller_info(self) -> dict[str, Any]:
		for frame in inspect.stack()[2:]:
			filename = frame.filename.rsplit("/", 1)[-1]
			if (
				filename not in SKIP_FRAMES
				and "structlog" not in frame.filename
			):
				return {
					"src": f"{filename}:{frame.lineno}",
					"fn": frame.function,
				}
		return {}

	def _bound(self) -> Any:
		return structlog.get_logger().bind(
			**self._context, **self._caller_info()
		)

	def debug(self, message: str, **kwargs: Any) -> None:
		self._bound().debug(message, **kwargs)

	def info(self, message: str, **kwargs: Any) -> None:
		self._bound().info(message, **kwargs)

	def warning(self, message: str, **kwargs: Any) -> None:
		self._bound().warning(message, **kwargs)

	def error(self, message: str, **kwargs: Any) -> None:
		self._bound().error(message, **kwargs)

	def exception(self, message: str, **kwargs: Any) -> None:
		self._bound().exception(message, **kwargs)

	def bind(self, **kwargs: Any) -> "StructLogger":
		return StructLogger({**self._context, **kwargs})


def get_struct_logger() -> AbstractLogger:
	return StructLogger()

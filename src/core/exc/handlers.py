"""Глобальные обработчики необработанных исключений."""

import asyncio
from typing import Any

from aiogram.types import ErrorEvent

from src.core.logger import AbstractLogger, get_struct_logger


def log_exc(
	log: AbstractLogger, event: str, exc: BaseException, **kwargs: Any
) -> None:
	log.error(event, error=str(exc), exc_type=type(exc).__name__, **kwargs)


def asyncio_exception_handler(
	_loop: asyncio.AbstractEventLoop, context: dict[str, Any]
) -> None:
	log = get_struct_logger()
	exc = context.get("exception")
	msg = context.get("message", "asyncio unhandled exception")
	if exc is not None:
		log_exc(log, "asyncio.unhandled_exception", exc, asyncio_msg=msg)
	else:
		log.error("asyncio.unhandled_exception", asyncio_msg=msg)


async def aiogram_error_handler(event: ErrorEvent) -> None:
	log_exc(
		get_struct_logger(),
		"aiogram.unhandled_exception",
		event.exception,
		update_type=event.update.event_type if event.update else None,
	)

import asyncio
import contextlib
import signal
from collections.abc import Awaitable, Callable

from src.config import cfg
from src.core.exc import asyncio_exception_handler
from src.core.logger import (
	configure_structlog,
	get_struct_logger,
	setup_logging,
)


def run_async_entrypoint(
	main_func: Callable[[], Awaitable[None]],
	*,
	process_name: str,
) -> None:
	"""SIGTERM/SIGINT отменяют главную задачу — `CancelledError` проходит
	по стеку, и `async with`/`finally` (контейнер DI, Telethon, сессия
	бота, пул БД) успевают штатно закрыться."""
	setup_logging(cfg.logging.level)
	configure_structlog()
	log = get_struct_logger()
	log.info("runtime.started", process=process_name)

	loop = asyncio.new_event_loop()
	asyncio.set_event_loop(loop)
	loop.set_exception_handler(asyncio_exception_handler)
	main_task = loop.create_task(main_func())

	def handle_shutdown_signal(sig_name: str) -> None:
		log.info(
			"runtime.shutdown_signal", process=process_name, signal=sig_name
		)
		main_task.cancel()

	for sig in (signal.SIGTERM, signal.SIGINT):
		with contextlib.suppress(NotImplementedError):
			loop.add_signal_handler(sig, handle_shutdown_signal, sig.name)

	try:
		loop.run_until_complete(main_task)
	except (KeyboardInterrupt, asyncio.CancelledError):
		pass
	finally:
		log.info("runtime.stopped", process=process_name)
		with contextlib.suppress(Exception):
			loop.close()

import logging
import sys


def setup_logging(level: str = "INFO") -> None:
	"""Stdlib-логи библиотек (aiogram, telethon, sqlalchemy) — в stdout."""
	logging.basicConfig(
		level=level.upper(),
		stream=sys.stdout,
		format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
		datefmt="%Y-%m-%d %H:%M:%S",
	)
	for noisy in ("telethon", "aiogram.event", "sqlalchemy.engine"):
		logging.getLogger(noisy).setLevel(logging.WARNING)

import asyncio
from contextlib import suppress


class Wakeup:
	"""Будильник для планировщика: тот спит до своего дедлайна, а любой,
	кто поменял расписание, может разбудить его раньше через `notify()`.

	Сигнал не теряется: если `notify()` пришёл, пока планировщик был занят
	(между `clear()` и `wait()`), следующий `wait()` вернётся сразу."""

	def __init__(self) -> None:
		self._event = asyncio.Event()

	def notify(self) -> None:
		self._event.set()

	def clear(self) -> None:
		self._event.clear()

	async def wait(self, timeout: float | None) -> bool:
		"""Ждёт `notify()` не дольше `timeout` секунд (None — бессрочно).
		True — разбудили, False — истёк таймаут."""
		# wait_for с timeout=0 отменяет ожидание, даже если событие уже
		# выставлено, — поэтому уже пришедший сигнал проверяем отдельно.
		if self._event.is_set():
			return True
		with suppress(TimeoutError):
			await asyncio.wait_for(self._event.wait(), timeout)
			return True
		return False

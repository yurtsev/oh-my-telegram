import asyncio
from collections.abc import Coroutine
from typing import Any


class ChatTaskRegistry:
	"""Одна «живая» штука на чат: новая анимация/фейковое действие в том же
	чате отменяет предыдущую, `!stop` — текущую. Без этого две анимации
	в одном чате дрались бы за одно сообщение."""

	def __init__(self) -> None:
		self._tasks: dict[int, asyncio.Task[Any]] = {}

	async def run(self, chat_id: int, coro: Coroutine[Any, Any, Any]) -> None:
		self.cancel(chat_id)
		task = asyncio.create_task(coro)
		self._tasks[chat_id] = task
		try:
			# wait(), а не await task: отмену через !stop не превращаем в
			# CancelledError обработчика — это штатное завершение.
			await asyncio.wait({task})
			if not task.cancelled():
				task.result()
		finally:
			if not task.done():
				task.cancel()
			if self._tasks.get(chat_id) is task:
				del self._tasks[chat_id]

	def cancel(self, chat_id: int) -> bool:
		task = self._tasks.pop(chat_id, None)
		if task is None or task.done():
			return False
		task.cancel()
		return True

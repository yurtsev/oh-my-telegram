from src.exc.base import AppError


class EmojiStatusError(AppError):
	"""Корень ошибок фичи эмодзи-статуса."""


class EmojiStatusApplyError(EmojiStatusError):
	"""Telegram отказал в установке эмодзи-статуса аккаунту."""

	def __init__(self, reason: str, retry_after_sec: int | None = None):
		super().__init__(reason)
		self.reason = reason
		self.retry_after_sec = retry_after_sec


class EmptyEmojiPoolError(EmojiStatusError):
	"""В пуле нет ни одного эмодзи — менять не на что."""


class InvalidRotationIntervalError(EmojiStatusError):
	"""Интервал смены вне допустимого диапазона."""

	def __init__(self, minutes: int, min_minutes: int, max_minutes: int):
		super().__init__(f"{minutes} not in [{min_minutes}, {max_minutes}]")
		self.min_minutes = min_minutes
		self.max_minutes = max_minutes

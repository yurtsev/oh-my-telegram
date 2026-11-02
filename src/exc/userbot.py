from src.exc.base import AppError


class UserbotError(AppError):
	"""Корень ошибок юзербота (сессия аккаунта и вход)."""


class UserbotNotAuthorizedError(UserbotError):
	"""Аккаунт не подключён или сессию отозвали."""


class LoginError(UserbotError):
	"""Корень ошибок входа в аккаунт через бота."""


class InvalidLoginCodeError(LoginError):
	"""Неверный код — можно ввести ещё раз."""


class InvalidPasswordError(LoginError):
	"""Неверный пароль 2FA — можно ввести ещё раз."""


class LoginExpiredError(LoginError):
	"""Вход не начат или истёк — начинать заново."""


class ForeignAccountError(LoginError):
	"""Вошли не в аккаунт владельца бота — сессия сразу отозвана."""


class LoginFailedError(LoginError):
	"""Telegram отказал во входе по иной причине."""

	def __init__(self, reason: str) -> None:
		super().__init__(reason)
		self.reason = reason

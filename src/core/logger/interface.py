from abc import ABC, abstractmethod
from typing import Any, Self


class AbstractLogger(ABC):
	@abstractmethod
	def debug(self, message: str, **kwargs: Any) -> None: ...

	@abstractmethod
	def info(self, message: str, **kwargs: Any) -> None: ...

	@abstractmethod
	def warning(self, message: str, **kwargs: Any) -> None: ...

	@abstractmethod
	def error(self, message: str, **kwargs: Any) -> None: ...

	@abstractmethod
	def exception(self, message: str, **kwargs: Any) -> None: ...

	@abstractmethod
	def bind(self, **kwargs: Any) -> Self: ...

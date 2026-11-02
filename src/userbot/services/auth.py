from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from telethon import TelegramClient
from telethon.errors import (
	FloodWaitError,
	PasswordHashInvalidError,
	PhoneCodeEmptyError,
	PhoneCodeExpiredError,
	PhoneCodeInvalidError,
	RPCError,
	SessionPasswordNeededError,
)

from src.config import cfg
from src.core.logger import get_struct_logger
from src.exc import (
	ForeignAccountError,
	InvalidLoginCodeError,
	InvalidPasswordError,
	LoginExpiredError,
	LoginFailedError,
)
from src.userbot.client import create_userbot_client
from src.userbot.services.session import UserbotSessionService

log = get_struct_logger()


class LoginStep(StrEnum):
	need_password = "need_password"
	done = "done"


@dataclass(slots=True)
class PendingLogin:
	client: TelegramClient
	phone: str
	phone_code_hash: str
	expires_at: datetime


class UserbotAuthService:
	"""Вход в аккаунт владельца по шагам: телефон → код → (пароль 2FA).

	Ничего из этого не сохраняется: телефон, phone_code_hash и
	полувошедший клиент живут только в памяти, пока идёт вход, код и
	пароль вообще не задерживаются дольше одного вызова. В логи попадают
	только события, без значений. Сохраняется лишь итоговая сессия — и
	та зашифрованной (`UserbotSessionService.activate`)."""

	def __init__(self, sessions: UserbotSessionService) -> None:
		self.sessions = sessions
		self._pending: PendingLogin | None = None

	async def start(self, phone: str) -> None:
		await self.cancel()
		client = create_userbot_client()
		await client.connect()
		try:
			sent = await client.send_code_request(phone)
		except FloodWaitError as e:
			await client.disconnect()
			raise LoginFailedError(f"FLOOD_WAIT {e.seconds}s") from e
		except RPCError as e:
			await client.disconnect()
			log.warning("auth.send_code_failed", error=e.message)
			raise LoginFailedError(e.message) from e
		self._pending = PendingLogin(
			client=client,
			phone=phone,
			phone_code_hash=sent.phone_code_hash,
			expires_at=datetime.now(UTC)
			+ timedelta(minutes=cfg.userbot.login_timeout_min),
		)
		log.info("auth.code_sent")

	async def submit_code(self, code: str) -> LoginStep:
		pending = await self._get_pending()
		try:
			await pending.client.sign_in(
				phone=pending.phone,
				code=code,
				phone_code_hash=pending.phone_code_hash,
			)
		except SessionPasswordNeededError:
			log.info("auth.password_required")
			return LoginStep.need_password
		except (PhoneCodeInvalidError, PhoneCodeEmptyError) as e:
			log.info("auth.invalid_code")
			raise InvalidLoginCodeError from e
		except PhoneCodeExpiredError as e:
			await self.cancel()
			raise LoginExpiredError from e
		except RPCError as e:
			await self.cancel()
			log.warning("auth.sign_in_failed", error=e.message)
			raise LoginFailedError(e.message) from e
		return await self._finish(pending)

	async def submit_password(self, password: str) -> LoginStep:
		pending = await self._get_pending()
		try:
			# Telethon считает SRP локально — в Telegram уходит не пароль,
			# а доказательство его знания.
			await pending.client.sign_in(password=password)
		except PasswordHashInvalidError as e:
			log.info("auth.invalid_password")
			raise InvalidPasswordError from e
		except RPCError as e:
			await self.cancel()
			log.warning("auth.password_failed", error=e.message)
			raise LoginFailedError(e.message) from e
		return await self._finish(pending)

	async def cancel(self) -> None:
		pending, self._pending = self._pending, None
		if pending is not None:
			await pending.client.disconnect()

	async def _get_pending(self) -> PendingLogin:
		if self._pending is None:
			raise LoginExpiredError
		if self._pending.expires_at <= datetime.now(UTC):
			await self.cancel()
			raise LoginExpiredError
		return self._pending

	async def _finish(self, pending: PendingLogin) -> LoginStep:
		self._pending = None
		me = await pending.client.get_me()
		if me.id != cfg.bot.owner_id:
			# Бот управляет только аккаунтом владельца — чужую сессию
			# сразу отзываем, не сохраняя.
			await pending.client.log_out()
			await pending.client.disconnect()
			log.warning("auth.foreign_account_rejected")
			raise ForeignAccountError
		await self.sessions.activate(pending.client, me.id)
		log.info("auth.signed_in")
		return LoginStep.done

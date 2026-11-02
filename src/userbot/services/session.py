from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime

from cryptography.exceptions import InvalidTag
from telethon import TelegramClient
from telethon.errors import RPCError

from src.core.crypto import SessionCipher
from src.core.db.uow import UowFactory
from src.core.exc import log_exc
from src.core.logger import get_struct_logger
from src.core.scheduling import Wakeup
from src.exc import UserbotNotAuthorizedError
from src.userbot.client import create_userbot_client

log = get_struct_logger()


@dataclass(frozen=True, slots=True)
class UserbotSessionInfo:
	connected: bool
	tg_user_id: int | None
	created_at: datetime | None


class UserbotSessionService:
	"""Владеет единственным подключённым клиентом аккаунта: поднимает его
	из зашифрованной сессии в БД, подменяет после входа через бота,
	отзывает при выходе. Строка сессии в открытом виде живёт только в
	памяти процесса."""

	def __init__(
		self, uow_factory: UowFactory, cipher: SessionCipher, wakeup: Wakeup
	) -> None:
		self.uow_factory = uow_factory
		self.cipher = cipher
		# Пока аккаунт не подключён, планировщики правил спят бессрочно —
		# вход через бота должен их разбудить.
		self.wakeup = wakeup
		self._client: TelegramClient | None = None
		self._client_listeners: list[
			Callable[[TelegramClient], Awaitable[None]]
		] = []

	def add_client_listener(
		self, listener: Callable[[TelegramClient], Awaitable[None]]
	) -> None:
		"""Вызывается на каждый новый активный клиент (старт и вход через
		бота) — так обработчики событий аккаунта вешаются и на клиент,
		появившийся уже после запуска приложения."""
		self._client_listeners.append(listener)

	@property
	def is_authorized(self) -> bool:
		return self._client is not None

	@property
	def client(self) -> TelegramClient:
		if self._client is None:
			raise UserbotNotAuthorizedError
		return self._client

	async def restore(self) -> bool:
		async with self.uow_factory() as uow:
			row = await uow.userbot_session.get()
		if row is None:
			log.warning("userbot.not_connected")
			return False
		try:
			session_string = self.cipher.decrypt(row.encrypted_session)
		except InvalidTag:
			# Ключ сменили или блоб повреждён — сессию не трогаем, вдруг
			# ключ вернут; владелец увидит «не подключён» в боте.
			log.error("userbot.session_decrypt_failed")
			return False

		client = create_userbot_client(session_string)
		await client.connect()
		if not await client.is_user_authorized():
			await client.disconnect()
			await self._delete_row()
			log.warning("userbot.session_revoked_on_start")
			return False
		self._client = client
		await self._notify_listeners(client)
		log.info("userbot.connected", tg_user_id=row.tg_user_id)
		return True

	async def activate(self, client: TelegramClient, tg_user_id: int) -> None:
		"""Сохраняет сессию свежевошедшего клиента и делает его активным."""
		encrypted = self.cipher.encrypt(client.session.save())
		async with self.uow_factory() as uow:
			await uow.userbot_session.save(tg_user_id, encrypted)
			await uow.commit()
		old, self._client = self._client, client
		if old is not None and old is not client:
			await old.disconnect()
		await self._notify_listeners(client)
		self.wakeup.notify()
		log.info("userbot.session_activated", tg_user_id=tg_user_id)

	async def info(self) -> UserbotSessionInfo:
		async with self.uow_factory() as uow:
			row = await uow.userbot_session.get()
		return UserbotSessionInfo(
			connected=self.is_authorized,
			tg_user_id=row.tg_user_id if row else None,
			created_at=row.created_at if row else None,
		)

	async def logout(self) -> None:
		"""Отзывает сессию на стороне Telegram и стирает её из БД."""
		client, self._client = self._client, None
		if client is not None:
			try:
				await client.log_out()
			except RPCError as e:
				log.warning("userbot.log_out_failed", error=e.message)
			await client.disconnect()
		await self._delete_row()
		log.info("userbot.logged_out")

	async def drop_revoked(self) -> None:
		"""Telegram сказал, что сессия больше не действует (отозвали из
		«Устройств» или сменили пароль) — забываем её."""
		client, self._client = self._client, None
		if client is not None:
			await client.disconnect()
		await self._delete_row()
		log.warning("userbot.session_revoked")

	async def close(self) -> None:
		if self._client is not None:
			await self._client.disconnect()

	async def _notify_listeners(self, client: TelegramClient) -> None:
		for listener in self._client_listeners:
			try:
				await listener(client)
			except Exception as e:
				# Сломанный слушатель не должен ронять вход в аккаунт.
				log_exc(log, "userbot.client_listener_failed", e)

	async def _delete_row(self) -> None:
		async with self.uow_factory() as uow:
			await uow.userbot_session.delete()
			await uow.commit()

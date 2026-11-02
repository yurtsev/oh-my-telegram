from datetime import UTC, datetime, timedelta

from src.core.db.uow import UowFactory
from src.core.logger import get_struct_logger

log = get_struct_logger()


class ChatMuteService:
	"""Мьюты собеседников в личке. Источник правды — БД (мьют на год должен
	пережить рестарт), но каждое входящее сообщение проверяется по кэшу в
	памяти — без запроса в БД на каждое сообщение каждого чата."""

	def __init__(self, uow_factory: UowFactory) -> None:
		self.uow_factory = uow_factory
		self._until: dict[int, datetime] = {}

	async def load(self) -> None:
		now = datetime.now(UTC)
		async with self.uow_factory() as uow:
			await uow.chat_mutes.delete_expired(now)
			mutes = await uow.chat_mutes.list_active(now)
			await uow.commit()
		self._until = {mute.peer_id: mute.until for mute in mutes}
		log.info("chat_mute.loaded", active=len(self._until))

	async def mute(self, peer_id: int, duration: timedelta) -> datetime:
		until = datetime.now(UTC) + duration
		async with self.uow_factory() as uow:
			await uow.chat_mutes.upsert(peer_id, until)
			await uow.commit()
		self._until[peer_id] = until
		log.info("chat_mute.muted", peer_id=peer_id, until=until.isoformat())
		return until

	async def unmute(self, peer_id: int) -> None:
		async with self.uow_factory() as uow:
			await uow.chat_mutes.delete(peer_id)
			await uow.commit()
		self._until.pop(peer_id, None)
		log.info("chat_mute.unmuted", peer_id=peer_id)

	def is_muted(self, peer_id: int) -> bool:
		until = self._until.get(peer_id)
		if until is None:
			return False
		if until <= datetime.now(UTC):
			# Истёкшие строки в БД дочистит load() при следующем старте —
			# ради них не стоит ходить в БД из горячего пути.
			del self._until[peer_id]
			return False
		return True

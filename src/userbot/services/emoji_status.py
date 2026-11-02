from telethon.errors import FloodWaitError, RPCError, UnauthorizedError
from telethon.tl.functions.account import UpdateEmojiStatusRequest
from telethon.tl.types import EmojiStatus, EmojiStatusEmpty

from src.core.logger import get_struct_logger
from src.exc import EmojiStatusApplyError, UserbotNotAuthorizedError
from src.userbot.services.session import UserbotSessionService

log = get_struct_logger()


class AccountEmojiStatusService:
	"""Ставит эмодзи-статус самому аккаунту через MTProto (нужен Premium)."""

	def __init__(self, sessions: UserbotSessionService) -> None:
		self.sessions = sessions

	async def set_status(self, custom_emoji_id: int | None) -> None:
		status = (
			EmojiStatus(document_id=custom_emoji_id)
			if custom_emoji_id is not None
			else EmojiStatusEmpty()
		)
		try:
			await self.sessions.client(
				UpdateEmojiStatusRequest(emoji_status=status)
			)
		except UnauthorizedError as e:
			await self.sessions.drop_revoked()
			raise UserbotNotAuthorizedError from e
		except FloodWaitError as e:
			log.warning("emoji_status.flood_wait", seconds=e.seconds)
			raise EmojiStatusApplyError(
				f"FLOOD_WAIT {e.seconds}s", retry_after_sec=e.seconds
			) from e
		except RPCError as e:
			log.error(
				"emoji_status.apply_failed",
				error=e.message,
				custom_emoji_id=custom_emoji_id,
			)
			raise EmojiStatusApplyError(e.message) from e
		log.info("emoji_status.applied", custom_emoji_id=custom_emoji_id)

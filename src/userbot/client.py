from telethon import TelegramClient
from telethon.sessions import StringSession

from src.config import cfg


def create_userbot_client(session_string: str = "") -> TelegramClient:
	return TelegramClient(
		StringSession(session_string),
		api_id=cfg.userbot.api_id,
		api_hash=cfg.userbot.api_hash,
		device_model=cfg.userbot.device_model,
		# Апдейты нужны для команд в чатах (!mute, !spam). account.updateStatus
		# («в сети») сами не шлём; влияет ли приём апдейтов на «был в сети» —
		# проверить на живом аккаунте.
		receive_updates=True,
	)

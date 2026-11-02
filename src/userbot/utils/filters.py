from telethon import events

from src.config import cfg


def is_dialog_with_person(event: events.NewMessage.Event) -> bool:
	"""Только личка с собеседником: не группы/каналы и не «Избранное»
	(там chat_id — это сам владелец). Нужен только `!mute`/`!unmute`: удалять
	чужие сообщения в группе без прав админа нельзя, а в «Избранном» некого."""
	return event.is_private and event.chat_id != cfg.bot.owner_id

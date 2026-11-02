from datetime import datetime

import pytest
from aiogram.types import Chat, Message, MessageEntity

from src.bot.services.emoji_status import EmojiStatusBotService
from src.bot.utils import format_interval


@pytest.mark.parametrize(
	("raw", "expected"),
	[
		("90", 90),
		("90м", 90),
		("2ч", 120),
		("2 ч", 120),
		("1д", 1440),
		("1ч30м", 90),
		("3H", 180),
		("1d12h", 2160),
		("", None),
		("часик", None),
		("2ч abc", None),
	],
)
def test_parse_interval(raw: str, expected: int | None):
	assert EmojiStatusBotService.parse_interval(raw) == expected


@pytest.mark.parametrize(
	("minutes", "expected"),
	[
		(15, "15 мин"),
		(60, "1 ч"),
		(90, "1 ч 30 мин"),
		(1440, "1 д"),
		(2160, "1 д 12 ч"),
		(0, "0 мин"),
	],
)
def test_format_interval(minutes: int, expected: str):
	assert format_interval(minutes) == expected


async def test_extract_custom_emojis_from_entities():
	# «😎» — 2 UTF-16 code unit, offset второго эмодзи считается в UTF-16.
	text = "😎 и 🔥 и просто 🙂"
	message = Message(
		message_id=1,
		date=datetime.now(),
		chat=Chat(id=1, type="private"),
		text=text,
		entities=[
			MessageEntity(
				type="custom_emoji", offset=0, length=2, custom_emoji_id="111"
			),
			MessageEntity(
				type="custom_emoji", offset=5, length=2, custom_emoji_id="222"
			),
		],
	)
	service = EmojiStatusBotService(rotation=None, bot=None)  # type: ignore[arg-type]

	items, failed = await service.extract_custom_emojis(message)

	assert items == {111: "😎", 222: "🔥"}
	assert failed == []

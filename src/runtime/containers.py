from dishka import AsyncContainer, make_async_container

from src.core.di import (
	AccountProvider,
	DbProvider,
	EmojiStatusProvider,
	MenuProvider,
	TelegramBotProvider,
	UserbotCommandsProvider,
	UserbotProvider,
)


def make_app_container() -> AsyncContainer:
	return make_async_container(
		DbProvider(),
		TelegramBotProvider(),
		UserbotProvider(),
		EmojiStatusProvider(),
		AccountProvider(),
		MenuProvider(),
		UserbotCommandsProvider(),
	)

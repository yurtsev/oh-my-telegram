from aiogram.fsm.state import State, StatesGroup


class EmojiStatusState(StatesGroup):
	wait_emojis = State()  # ждём сообщения с премиум-эмодзи / ссылки на паки
	wait_interval = State()  # ждём свой интервал текстом

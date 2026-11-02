from aiogram.fsm.state import State, StatesGroup


class AccountState(StatesGroup):
	wait_contact = State()  # ждём «Поделиться контактом»
	wait_code = State()  # код набирается инлайн-клавиатурой
	wait_password = State()  # пароль 2FA одним сообщением, сразу удаляется

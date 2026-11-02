from contextlib import suppress

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from src.bot.keyboards import LOGIN_CODE_MAX_LEN, AccountKeyboards
from src.bot.states import AccountState
from src.bot.texts import AccountText
from src.config import cfg
from src.core.logger import get_struct_logger
from src.exc import (
	ForeignAccountError,
	InvalidLoginCodeError,
	InvalidPasswordError,
	LoginExpiredError,
	LoginFailedError,
)
from src.userbot.services.auth import LoginStep, UserbotAuthService
from src.userbot.services.session import UserbotSessionService

log = get_struct_logger()


class AccountBotService:
	"""UI входа в аккаунт и управления сессией. Набранные цифры кода
	лежат в FSM (MemoryStorage — только память процесса) до нажатия ✅,
	пароль не хранится нигде: сообщение удаляется до его обработки."""

	def __init__(
		self,
		sessions: UserbotSessionService,
		auth: UserbotAuthService,
		bot: Bot,
	) -> None:
		self.sessions = sessions
		self.auth = auth
		self.bot = bot

	# --- Экран ---

	async def send_screen(self, message: Message) -> None:
		text, kb = await self._screen()
		await message.answer(text, reply_markup=kb)

	async def show_screen(self, call: CallbackQuery) -> None:
		text, kb = await self._screen()
		await self._edit(call, text, kb)
		await call.answer()

	async def notify_not_connected(self) -> None:
		try:
			await self.bot.send_message(
				cfg.bot.owner_id, AccountText.not_connected_on_start()
			)
		except (TelegramBadRequest, TelegramForbiddenError) as e:
			# Владелец ещё ни разу не писал боту (или заблокировал его) —
			# первым Telegram написать не даст. Ожидаемо: статус он увидит
			# при первом /start.
			log.warning(
				"account.notify_not_connected_skipped", error=e.message
			)

	# --- Вход: контакт ---

	async def start_connect(
		self, call: CallbackQuery, state: FSMContext
	) -> None:
		await state.set_state(AccountState.wait_contact)
		if isinstance(call.message, Message):
			await call.message.answer(
				AccountText.ask_contact(),
				reply_markup=AccountKeyboards.contact_kb(),
			)
		await call.answer()

	async def contact_received(
		self, message: Message, state: FSMContext
	) -> None:
		contact = message.contact
		if (
			contact is None
			or message.from_user is None
			or contact.user_id != message.from_user.id
		):
			await message.answer(AccountText.not_own_contact())
			return

		phone = contact.phone_number
		phone = phone if phone.startswith("+") else f"+{phone}"
		await message.answer(
			AccountText.sending_code(),
			reply_markup=AccountKeyboards.remove_kb(),
		)
		try:
			await self.auth.start(phone)
		except LoginFailedError as e:
			await state.clear()
			await message.answer(AccountText.login_failed(e.reason))
			await self.send_screen(message)
			return

		await state.set_state(AccountState.wait_code)
		await state.update_data(code="")
		await message.answer(
			AccountText.code_prompt(0), reply_markup=AccountKeyboards.code_kb()
		)

	async def cancel_by_message(
		self, message: Message, state: FSMContext
	) -> None:
		await self.auth.cancel()
		await state.clear()
		await message.answer(
			AccountText.cancelled(), reply_markup=AccountKeyboards.remove_kb()
		)
		await self.send_screen(message)

	async def cancel_by_call(
		self, call: CallbackQuery, state: FSMContext
	) -> None:
		await self.auth.cancel()
		await state.clear()
		text, kb = await self._screen()
		await self._edit(call, text, kb)
		await call.answer(AccountText.cancelled())

	# --- Вход: код ---

	async def code_digit(
		self, call: CallbackQuery, state: FSMContext, digit: int
	) -> None:
		code = (await state.get_data()).get("code", "")
		if len(code) < LOGIN_CODE_MAX_LEN:
			code += str(digit)
			await state.update_data(code=code)
		await self._edit(
			call,
			AccountText.code_prompt(len(code)),
			AccountKeyboards.code_kb(),
		)
		await call.answer()

	async def code_backspace(
		self, call: CallbackQuery, state: FSMContext
	) -> None:
		code = (await state.get_data()).get("code", "")[:-1]
		await state.update_data(code=code)
		await self._edit(
			call,
			AccountText.code_prompt(len(code)),
			AccountKeyboards.code_kb(),
		)
		await call.answer()

	async def submit_code(
		self, call: CallbackQuery, state: FSMContext
	) -> None:
		code = (await state.get_data()).get("code", "")
		if len(code) < 5:
			await call.answer(AccountText.code_too_short())
			return
		# Код больше не нужен ни в каком виде — стираем до обращения к
		# Telegram, чтобы он не пережил ошибку.
		await state.update_data(code="")
		try:
			step = await self.auth.submit_code(code)
		except InvalidLoginCodeError:
			await self._edit(
				call,
				AccountText.code_prompt(0, invalid=True),
				AccountKeyboards.code_kb(),
			)
			await call.answer()
			return
		except (LoginExpiredError, LoginFailedError, ForeignAccountError) as e:
			await state.clear()
			await self._finish_with_error_call(call, e)
			return

		if step == LoginStep.need_password:
			await state.set_state(AccountState.wait_password)
			await self._edit(
				call, AccountText.ask_password(), AccountKeyboards.cancel_kb()
			)
			await call.answer()
			return

		await state.clear()
		text, kb = await self._screen()
		await self._edit(call, f"{AccountText.connected()}\n\n{text}", kb)
		await call.answer()

	# --- Вход: пароль ---

	async def password_received(
		self, message: Message, state: FSMContext
	) -> None:
		password = message.text or ""
		# Удаляем раньше, чем что-либо делать: пароль не должен остаться в
		# истории чата, даже если дальше всё упадёт.
		try:
			await message.delete()
		except TelegramBadRequest:
			await message.answer(AccountText.password_not_deleted())

		try:
			await self.auth.submit_password(password)
		except InvalidPasswordError:
			await message.answer(
				AccountText.invalid_password(),
				reply_markup=AccountKeyboards.cancel_kb(),
			)
			return
		except LoginExpiredError:
			await state.clear()
			await message.answer(AccountText.expired())
			await self.send_screen(message)
			return
		except ForeignAccountError:
			await state.clear()
			await message.answer(AccountText.foreign_account())
			await self.send_screen(message)
			return
		except LoginFailedError as e:
			await state.clear()
			await message.answer(AccountText.login_failed(e.reason))
			await self.send_screen(message)
			return

		await state.clear()
		await message.answer(AccountText.connected())
		await self.send_screen(message)

	# --- Выход ---

	async def ask_logout(self, call: CallbackQuery) -> None:
		await self._edit(
			call,
			AccountText.logout_confirm(),
			AccountKeyboards.logout_confirm_kb(),
		)
		await call.answer()

	async def logout(self, call: CallbackQuery) -> None:
		await self.sessions.logout()
		text, kb = await self._screen()
		await self._edit(call, text, kb)
		await call.answer(AccountText.logged_out())

	# --- Внутреннее ---

	async def _screen(self) -> tuple[str, InlineKeyboardMarkup]:
		info = await self.sessions.info()
		return AccountText.screen(info), AccountKeyboards.screen_kb(
			connected=info.connected
		)

	async def _finish_with_error_call(
		self, call: CallbackQuery, error: Exception
	) -> None:
		if isinstance(error, LoginFailedError):
			notice = AccountText.login_failed(error.reason)
		elif isinstance(error, ForeignAccountError):
			notice = AccountText.foreign_account()
		else:
			notice = AccountText.expired()
		text, kb = await self._screen()
		await self._edit(call, f"{notice}\n\n{text}", kb)
		await call.answer()

	@staticmethod
	async def _edit(
		call: CallbackQuery, text: str, kb: InlineKeyboardMarkup
	) -> None:
		if not isinstance(call.message, Message):
			return
		with suppress(TelegramBadRequest):
			await call.message.edit_text(text, reply_markup=kb)

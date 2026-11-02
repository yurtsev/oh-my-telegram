from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from dishka.integrations.aiogram import FromDishka

from src.bot.keyboards import (
	CANCEL_LOGIN_LABEL,
	AccountAction,
	AccountData,
	MenuData,
	MenuSection,
)
from src.bot.services.account import AccountBotService
from src.bot.states import AccountState

router = Router()


@router.message(Command("account"))
async def account_command(
	message: Message,
	state: FSMContext,
	service: FromDishka[AccountBotService],
):
	await state.clear()
	await service.send_screen(message)


@router.callback_query(MenuData.filter(F.section == MenuSection.account))
@router.callback_query(AccountData.filter(F.action == AccountAction.screen))
async def account_screen(
	call: CallbackQuery,
	state: FSMContext,
	service: FromDishka[AccountBotService],
):
	await state.clear()
	await service.show_screen(call)


@router.callback_query(AccountData.filter(F.action == AccountAction.connect))
async def start_connect(
	call: CallbackQuery,
	state: FSMContext,
	service: FromDishka[AccountBotService],
):
	await service.start_connect(call, state)


@router.message(AccountState.wait_contact, F.text == CANCEL_LOGIN_LABEL)
async def cancel_contact(
	message: Message,
	state: FSMContext,
	service: FromDishka[AccountBotService],
):
	await service.cancel_by_message(message, state)


@router.message(AccountState.wait_contact)
async def contact_received(
	message: Message,
	state: FSMContext,
	service: FromDishka[AccountBotService],
):
	await service.contact_received(message, state)


@router.callback_query(
	AccountState.wait_code,
	AccountData.filter(F.action == AccountAction.digit),
)
async def code_digit(
	call: CallbackQuery,
	callback_data: AccountData,
	state: FSMContext,
	service: FromDishka[AccountBotService],
):
	await service.code_digit(call, state, callback_data.digit)


@router.callback_query(
	AccountState.wait_code,
	AccountData.filter(F.action == AccountAction.backspace),
)
async def code_backspace(
	call: CallbackQuery,
	state: FSMContext,
	service: FromDishka[AccountBotService],
):
	await service.code_backspace(call, state)


@router.callback_query(
	AccountState.wait_code,
	AccountData.filter(F.action == AccountAction.submit_code),
)
async def submit_code(
	call: CallbackQuery,
	state: FSMContext,
	service: FromDishka[AccountBotService],
):
	await service.submit_code(call, state)


@router.message(AccountState.wait_password, F.text)
async def password_received(
	message: Message,
	state: FSMContext,
	service: FromDishka[AccountBotService],
):
	await service.password_received(message, state)


@router.callback_query(AccountData.filter(F.action == AccountAction.cancel))
async def cancel_login(
	call: CallbackQuery,
	state: FSMContext,
	service: FromDishka[AccountBotService],
):
	await service.cancel_by_call(call, state)


@router.callback_query(AccountData.filter(F.action == AccountAction.logout))
async def ask_logout(
	call: CallbackQuery, service: FromDishka[AccountBotService]
):
	await service.ask_logout(call)


@router.callback_query(
	AccountData.filter(F.action == AccountAction.logout_confirm)
)
async def logout(call: CallbackQuery, service: FromDishka[AccountBotService]):
	await service.logout(call)

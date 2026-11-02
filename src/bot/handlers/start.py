from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from dishka.integrations.aiogram import FromDishka

from src.bot.keyboards import MenuData, MenuSection
from src.bot.services.emoji_status import EmojiStatusBotService
from src.bot.services.menu import MenuBotService

router = Router()


@router.message(CommandStart())
async def start(
	message: Message,
	state: FSMContext,
	service: FromDishka[MenuBotService],
):
	await state.clear()
	# На старте приложения список команд мог не встать (владелец ещё не
	# писал боту) — /start как раз тот момент, когда чат уже есть.
	await service.setup_commands()
	await service.send_menu(message)


@router.message(Command("menu"))
async def menu(
	message: Message,
	state: FSMContext,
	service: FromDishka[MenuBotService],
):
	await state.clear()
	await service.send_menu(message)


@router.message(Command("help"))
async def help_command(
	message: Message,
	state: FSMContext,
	service: FromDishka[MenuBotService],
):
	await state.clear()
	await service.send_help(message)


@router.message(Command("emoji"))
async def emoji_status_command(
	message: Message,
	state: FSMContext,
	service: FromDishka[EmojiStatusBotService],
):
	await state.clear()
	await service.send_screen(message)


@router.callback_query(MenuData.filter(F.section == MenuSection.main))
async def menu_callback(
	call: CallbackQuery,
	state: FSMContext,
	service: FromDishka[MenuBotService],
):
	await state.clear()
	await service.show_menu(call)


@router.callback_query(MenuData.filter(F.section == MenuSection.help))
async def help_callback(
	call: CallbackQuery,
	state: FSMContext,
	service: FromDishka[MenuBotService],
):
	await state.clear()
	await service.show_help(call)


@router.callback_query(MenuData.filter(F.section == MenuSection.emoji_status))
async def emoji_status_section(
	call: CallbackQuery,
	state: FSMContext,
	service: FromDishka[EmojiStatusBotService],
):
	await state.clear()
	await service.show_screen(call)

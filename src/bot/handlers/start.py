from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from dishka.integrations.aiogram import FromDishka

from src.bot.keyboards import MenuData, MenuKeyboards, MenuSection
from src.bot.services.emoji_status import EmojiStatusBotService
from src.bot.texts import MenuText

router = Router()


@router.message(CommandStart())
@router.message(Command("menu"))
async def main_menu(message: Message, state: FSMContext):
	await state.clear()
	await message.answer(
		MenuText.main(), reply_markup=MenuKeyboards.main_menu_kb()
	)


@router.message(Command("emoji"))
async def emoji_status_command(
	message: Message,
	state: FSMContext,
	service: FromDishka[EmojiStatusBotService],
):
	await state.clear()
	await service.send_screen(message)


@router.callback_query(MenuData.filter(F.section == MenuSection.main))
async def main_menu_callback(call: CallbackQuery, state: FSMContext):
	await state.clear()
	if isinstance(call.message, Message):
		await call.message.edit_text(
			MenuText.main(), reply_markup=MenuKeyboards.main_menu_kb()
		)
	await call.answer()


@router.callback_query(MenuData.filter(F.section == MenuSection.emoji_status))
async def emoji_status_section(
	call: CallbackQuery,
	state: FSMContext,
	service: FromDishka[EmojiStatusBotService],
):
	await state.clear()
	await service.show_screen(call)

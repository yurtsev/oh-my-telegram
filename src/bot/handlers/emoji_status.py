from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from dishka.integrations.aiogram import FromDishka

from src.bot.keyboards import EmojiStatusAction, EmojiStatusData
from src.bot.services.emoji_status import EmojiStatusBotService
from src.bot.states import EmojiStatusState

router = Router()


@router.callback_query(
	EmojiStatusData.filter(F.action == EmojiStatusAction.screen)
)
async def screen(
	call: CallbackQuery,
	state: FSMContext,
	service: FromDishka[EmojiStatusBotService],
):
	await state.clear()
	await service.show_screen(call)


@router.callback_query(
	EmojiStatusData.filter(F.action == EmojiStatusAction.next)
)
async def next_emoji(
	call: CallbackQuery, service: FromDishka[EmojiStatusBotService]
):
	await service.next_emoji(call)


@router.callback_query(
	EmojiStatusData.filter(F.action == EmojiStatusAction.previous)
)
async def previous_emoji(
	call: CallbackQuery, service: FromDishka[EmojiStatusBotService]
):
	await service.previous_emoji(call)


@router.callback_query(
	EmojiStatusData.filter(F.action == EmojiStatusAction.delete_current)
)
async def delete_current(
	call: CallbackQuery, service: FromDishka[EmojiStatusBotService]
):
	await service.delete_current(call)


@router.callback_query(
	EmojiStatusData.filter(F.action == EmojiStatusAction.toggle)
)
async def toggle(
	call: CallbackQuery, service: FromDishka[EmojiStatusBotService]
):
	await service.toggle(call)


@router.callback_query(
	EmojiStatusData.filter(F.action == EmojiStatusAction.add)
)
async def start_add(
	call: CallbackQuery,
	state: FSMContext,
	service: FromDishka[EmojiStatusBotService],
):
	await service.start_add(call, state)


@router.message(EmojiStatusState.wait_emojis)
async def add_from_message(
	message: Message, service: FromDishka[EmojiStatusBotService]
):
	await service.add_from_message(message)


@router.callback_query(
	EmojiStatusData.filter(F.action == EmojiStatusAction.add_done)
)
async def finish_add(
	call: CallbackQuery,
	state: FSMContext,
	service: FromDishka[EmojiStatusBotService],
):
	await service.finish_add(call, state)


@router.callback_query(
	EmojiStatusData.filter(F.action == EmojiStatusAction.pool)
)
async def pool(
	call: CallbackQuery,
	callback_data: EmojiStatusData,
	service: FromDishka[EmojiStatusBotService],
):
	await service.show_pool(call, callback_data.page)


@router.callback_query(
	EmojiStatusData.filter(F.action == EmojiStatusAction.shuffle)
)
async def shuffle(
	call: CallbackQuery, service: FromDishka[EmojiStatusBotService]
):
	await service.shuffle(call)


@router.callback_query(
	EmojiStatusData.filter(F.action == EmojiStatusAction.delete)
)
async def delete_from_pool(
	call: CallbackQuery,
	callback_data: EmojiStatusData,
	service: FromDishka[EmojiStatusBotService],
):
	await service.delete_from_pool(
		call, callback_data.value, callback_data.page
	)


@router.callback_query(
	EmojiStatusData.filter(F.action == EmojiStatusAction.intervals)
)
async def intervals(
	call: CallbackQuery, service: FromDishka[EmojiStatusBotService]
):
	await service.show_intervals(call)


@router.callback_query(
	EmojiStatusData.filter(F.action == EmojiStatusAction.set_interval)
)
async def set_interval(
	call: CallbackQuery,
	callback_data: EmojiStatusData,
	service: FromDishka[EmojiStatusBotService],
):
	await service.set_interval(call, callback_data.value)


@router.callback_query(
	EmojiStatusData.filter(F.action == EmojiStatusAction.custom_interval)
)
async def start_custom_interval(
	call: CallbackQuery,
	state: FSMContext,
	service: FromDishka[EmojiStatusBotService],
):
	await service.start_custom_interval(call, state)


@router.message(EmojiStatusState.wait_interval)
async def custom_interval_from_message(
	message: Message,
	state: FSMContext,
	service: FromDishka[EmojiStatusBotService],
):
	await service.custom_interval_from_message(message, state)

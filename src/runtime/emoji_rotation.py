from datetime import UTC, datetime

from aiogram import Bot

from src.bot.texts import EmojiStatusText
from src.config import cfg
from src.core.exc import log_exc
from src.core.logger import get_struct_logger
from src.core.scheduling import Wakeup
from src.exc import EmojiStatusApplyError, UserbotNotAuthorizedError
from src.services.emoji_rotation import EmojiRotationService
from src.userbot.services.session import UserbotSessionService

log = get_struct_logger()


class EmojiRotationScheduler:
	"""Планировщик смены эмодзи без поллинга: спит ровно до
	`next_change_at` из БД и просыпается раньше только по `Wakeup.notify()`
	— когда кто-то поменял расписание (кнопки, интервал, пауза, новые
	эмодзи, вход в аккаунт). Когда менять нечего (пауза, пустой пул,
	аккаунт не подключён), спит бессрочно. Источник правды — БД, поэтому
	рестарт процесса не сбивает расписание."""

	# Страховка, а не опрос: asyncio меряет сон монотонными часами, которые
	# стоят, пока машина в suspend, — без потолка смена после сна ноутбука
	# опоздала бы на всё время сна.
	MAX_SLEEP_SEC = 60 * 60
	# Пауза после сбоя БД/сети, чтобы не долбить в цикле.
	ERROR_RETRY_SEC = 60
	# Пол на случай непредвиденного «дедлайн уже прошёл, а менять нечего» —
	# чтобы такая ошибка в логике не превратилась в busy loop.
	MIN_SLEEP_SEC = 1

	def __init__(
		self,
		rotation: EmojiRotationService,
		sessions: UserbotSessionService,
		wakeup: Wakeup,
		bot: Bot,
	) -> None:
		self.rotation = rotation
		self.sessions = sessions
		self.wakeup = wakeup
		self.bot = bot
		# Владельцу пишем только о первой ошибке подряд, а не на каждый
		# ретрай — иначе при отозванном Premium бот заспамит.
		self.is_failing = False

	async def run(self) -> None:
		log.info("emoji_scheduler.started")
		while True:
			# clear() до step(): notify(), пришедший во время step(), не
			# потеряется — wait() ниже вернётся сразу.
			self.wakeup.clear()
			delay = await self.step()
			log.info("emoji_scheduler.sleeping", seconds=delay)
			await self.wakeup.wait(delay)

	async def step(self) -> float | None:
		"""Сменить эмодзи, если пора, и вернуть, сколько спать до следующей
		проверки (None — до пробуждения)."""
		if not self.sessions.is_authorized:
			return None
		try:
			await self.rotation.rotate_if_due()
		except UserbotNotAuthorizedError:
			# Сессию только что отозвали — дальше спим до нового входа.
			await self.send_owner(EmojiStatusText.rotation_stopped_revoked())
			return None
		except EmojiStatusApplyError as e:
			# rotate_if_due уже отодвинул next_change_at на время ретрая —
			# дедлайн ниже его и подхватит.
			if not self.is_failing:
				await self.notify_owner_failure(e)
			self.is_failing = True
		except Exception as e:
			# Граница фоновой задачи: сбой одной итерации (БД моргнула) не
			# должен убивать ротацию насовсем.
			log_exc(log, "emoji_scheduler.step_failed", e)
			return self.ERROR_RETRY_SEC
		else:
			self.is_failing = False

		try:
			due = await self.rotation.next_due_at()
		except Exception as e:
			log_exc(log, "emoji_scheduler.next_due_failed", e)
			return self.ERROR_RETRY_SEC
		if due is None:
			return None
		seconds = (due - datetime.now(UTC)).total_seconds()
		return min(max(seconds, self.MIN_SLEEP_SEC), self.MAX_SLEEP_SEC)

	async def notify_owner_failure(self, error: EmojiStatusApplyError) -> None:
		try:
			retry_at = await self.rotation.next_due_at()
		except Exception as e:
			log_exc(log, "emoji_scheduler.next_due_failed", e)
			retry_at = None
		await self.send_owner(
			EmojiStatusText.rotation_failed_notify(error.reason, retry_at)
		)

	async def send_owner(self, text: str) -> None:
		try:
			await self.bot.send_message(cfg.bot.owner_id, text)
		except Exception as e:
			log_exc(log, "emoji_scheduler.notify_failed", e)

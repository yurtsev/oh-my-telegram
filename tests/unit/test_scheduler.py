import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from src.core.scheduling import Wakeup
from src.exc import EmojiStatusApplyError, UserbotNotAuthorizedError
from src.runtime.emoji_rotation import EmojiRotationScheduler


class FakeRotation:
	def __init__(self) -> None:
		self.due: datetime | None = None
		self.error: Exception | None = None
		self.calls = 0

	async def rotate_if_due(self):
		self.calls += 1
		if self.error is not None:
			raise self.error

	async def next_due_at(self):
		return self.due


class FakeSessions:
	is_authorized = True


class FakeBot:
	def __init__(self) -> None:
		self.sent: list[str] = []

	async def send_message(self, _chat_id: int, text: str) -> None:
		self.sent.append(text)


@pytest.fixture
def parts():
	return FakeRotation(), FakeSessions(), Wakeup(), FakeBot()


@pytest.fixture
def scheduler(parts) -> EmojiRotationScheduler:
	rotation, sessions, wakeup, bot = parts
	return EmojiRotationScheduler(
		rotation=rotation,  # type: ignore[arg-type]
		sessions=sessions,  # type: ignore[arg-type]
		wakeup=wakeup,
		bot=bot,  # type: ignore[arg-type]
	)


async def test_wakeup_signal_is_not_lost():
	wakeup = Wakeup()
	wakeup.notify()

	assert await wakeup.wait(timeout=0) is True
	wakeup.clear()
	assert await wakeup.wait(timeout=0.01) is False


async def test_sleeps_until_deadline(scheduler, parts):
	parts[0].due = datetime.now(UTC) + timedelta(seconds=120)

	delay = await scheduler.step()

	assert 118 < delay <= 120


async def test_sleep_is_capped_and_floored(scheduler, parts):
	parts[0].due = datetime.now(UTC) + timedelta(days=1)
	assert await scheduler.step() == scheduler.MAX_SLEEP_SEC

	parts[0].due = datetime.now(UTC) - timedelta(minutes=1)
	assert await scheduler.step() == scheduler.MIN_SLEEP_SEC


async def test_nothing_to_do_sleeps_until_woken(scheduler, parts):
	parts[0].due = None
	assert await scheduler.step() is None

	parts[1].is_authorized = False
	assert await scheduler.step() is None
	assert parts[0].calls == 1  # без аккаунта даже в БД не ходим


async def test_apply_error_notifies_owner_once(scheduler, parts):
	rotation, _, _, bot = parts
	rotation.error = EmojiStatusApplyError("PREMIUM_ACCOUNT_REQUIRED")
	rotation.due = datetime.now(UTC) + timedelta(minutes=10)

	await scheduler.step()
	await scheduler.step()

	assert len(bot.sent) == 1


async def test_revoked_session_stops_until_login(scheduler, parts):
	rotation, _, _, bot = parts
	rotation.error = UserbotNotAuthorizedError()

	assert await scheduler.step() is None
	assert len(bot.sent) == 1


async def test_unexpected_error_backs_off(scheduler, parts):
	parts[0].error = RuntimeError("db is down")

	assert await scheduler.step() == scheduler.ERROR_RETRY_SEC


async def test_notify_wakes_sleeping_scheduler_early(scheduler, parts):
	rotation, _, wakeup, _ = parts
	rotation.due = datetime.now(UTC) + timedelta(hours=1)
	task = asyncio.create_task(scheduler.run())
	await asyncio.sleep(0.05)
	assert rotation.calls == 1

	wakeup.notify()
	await asyncio.sleep(0.05)

	assert rotation.calls == 2
	task.cancel()

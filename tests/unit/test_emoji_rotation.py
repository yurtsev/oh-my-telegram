from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest

from src.config import cfg
from src.core.scheduling import Wakeup
from src.exc import (
	EmojiStatusApplyError,
	EmptyEmojiPoolError,
	InvalidRotationIntervalError,
)
from src.services.emoji_rotation import EmojiRotationService


class FakeEmoji:
	def __init__(
		self, id: int, custom_emoji_id: int, alt: str, position: int
	) -> None:
		self.id = id
		self.custom_emoji_id = custom_emoji_id
		self.alt = alt
		self.position = position


class FakeRotation:
	"""Повторяет ORM-семантику: current_emoji_id следует за relationship."""

	def __init__(self, interval_min: int) -> None:
		self.enabled = True
		self.interval_min = interval_min
		self.current_emoji: FakeEmoji | None = None
		self.changed_at: datetime | None = None
		self.next_change_at: datetime | None = None

	@property
	def current_emoji_id(self) -> int | None:
		return self.current_emoji.id if self.current_emoji else None


class FakeEmojiRepo:
	"""Та же семантика дорожки, что у EmojiRepo: порядок (position, id)."""

	def __init__(self) -> None:
		self.items: dict[int, FakeEmoji] = {}

	def _ordered(self) -> list[FakeEmoji]:
		return sorted(self.items.values(), key=lambda e: (e.position, e.id))

	async def get(self, emoji_id: int):
		return self.items.get(emoji_id)

	async def list_all(self):
		return self._ordered()

	async def count(self):
		return len(self.items)

	async def add_many(self, items: dict[int, str]) -> int:
		existing = {e.custom_emoji_id for e in self.items.values()}
		start = max((e.position for e in self.items.values()), default=-1)
		added = 0
		for offset, (custom_id, alt) in enumerate(items.items(), start=1):
			if custom_id in existing:
				continue
			new_id = max(self.items, default=0) + 1
			self.items[new_id] = FakeEmoji(
				new_id, custom_id, alt, start + offset
			)
			added += 1
		return added

	async def delete(self, emoji_id: int) -> bool:
		return self.items.pop(emoji_id, None) is not None

	async def after(self, emoji):
		key = (emoji.position, emoji.id)
		return next(
			(e for e in self._ordered() if (e.position, e.id) > key), None
		)

	async def before(self, emoji):
		key = (emoji.position, emoji.id)
		return next(
			(e for e in reversed(self._ordered()) if (e.position, e.id) < key),
			None,
		)

	async def first(self):
		ordered = self._ordered()
		return ordered[0] if ordered else None

	async def last(self):
		ordered = self._ordered()
		return ordered[-1] if ordered else None

	async def reorder(self, emoji_ids: list[int]) -> None:
		for position, emoji_id in enumerate(emoji_ids):
			self.items[emoji_id].position = position


class FakeRotationRepo:
	def __init__(self) -> None:
		self.row: FakeRotation | None = None

	async def get_for_update(self, default_interval_min: int) -> FakeRotation:
		if self.row is None:
			self.row = FakeRotation(default_interval_min)
		return self.row


class FakeUow:
	def __init__(self) -> None:
		self.emojis = FakeEmojiRepo()
		self.emoji_rotation = FakeRotationRepo()

	async def commit(self) -> None: ...

	async def flush(self) -> None: ...


class FakeAccountStatus:
	def __init__(self) -> None:
		self.calls: list[int | None] = []
		self.fail_with: EmojiStatusApplyError | None = None

	async def set_status(self, custom_emoji_id: int | None) -> None:
		if self.fail_with is not None:
			raise self.fail_with
		self.calls.append(custom_emoji_id)


@pytest.fixture
def uow() -> FakeUow:
	return FakeUow()


@pytest.fixture
def account() -> FakeAccountStatus:
	return FakeAccountStatus()


@pytest.fixture
def wakeup() -> Wakeup:
	return Wakeup()


@pytest.fixture
def service(
	uow: FakeUow, account: FakeAccountStatus, wakeup: Wakeup
) -> EmojiRotationService:
	@asynccontextmanager
	async def uow_factory():
		yield uow

	return EmojiRotationService(
		uow_factory=uow_factory,  # type: ignore[arg-type]
		account_status=account,  # type: ignore[arg-type]
		wakeup=wakeup,
	)


async def test_empty_pool_is_not_an_error_for_loop(service, account):
	assert await service.rotate_if_due() is None
	assert account.calls == []


async def test_rotate_now_on_empty_pool_raises(service):
	with pytest.raises(EmptyEmojiPoolError):
		await service.rotate_now()


async def test_first_tick_after_adding_sets_status(service, account, uow):
	await service.add_emojis({111: "😎"})

	emoji = await service.rotate_if_due()

	assert emoji is not None and emoji.custom_emoji_id == 111
	assert account.calls == [111]
	rotation = uow.emoji_rotation.row
	assert rotation.next_change_at - rotation.changed_at == timedelta(
		minutes=cfg.emoji_rotation.default_interval_min
	)


async def test_not_due_does_nothing(service, account):
	await service.add_emojis({111: "😎", 222: "🔥"})
	await service.rotate_if_due()

	assert await service.rotate_if_due() is None
	assert len(account.calls) == 1


async def test_paused_rotation_does_nothing(service, account):
	await service.add_emojis({111: "😎"})
	await service.set_enabled(False)

	assert await service.rotate_if_due() is None
	assert account.calls == []


async def test_single_emoji_pool_reapplies_it(service, account):
	await service.add_emojis({111: "😎"})
	await service.rotate_now()
	await service.rotate_now()

	assert account.calls == [111, 111]


async def test_duplicates_are_not_added(service):
	assert await service.add_emojis({111: "😎", 222: "🔥"}) == (2, 2)
	assert await service.add_emojis({111: "😎", 333: "🥶"}) == (1, 3)


async def test_delete_current_switches_to_another(service, account, uow):
	await service.add_emojis({111: "😎", 222: "🔥"})
	current = await service.rotate_now()

	new_current = await service.delete_emoji(current.id)

	assert new_current is not None and new_current.id != current.id
	assert account.calls[-1] == new_current.custom_emoji_id
	assert current.id not in uow.emojis.items


async def test_delete_last_emoji_clears_status(service, account):
	await service.add_emojis({111: "😎"})
	current = await service.rotate_now()

	assert await service.delete_emoji(current.id) is None
	assert account.calls[-1] is None


async def test_delete_not_current_keeps_status(service, account):
	await service.add_emojis({111: "😎", 222: "🔥"})
	current = await service.rotate_now()
	pool = (await service.snapshot()).pool
	other = next(e for e in pool if e.id != current.id)

	assert await service.delete_emoji(other.id) is None
	assert account.calls == [current.custom_emoji_id]


async def test_interval_counts_from_last_change(service, uow):
	await service.add_emojis({111: "😎"})
	await service.rotate_now()
	changed_at = uow.emoji_rotation.row.changed_at

	await service.set_interval(60)

	assert uow.emoji_rotation.row.next_change_at == changed_at + timedelta(
		minutes=60
	)


async def test_interval_out_of_range_rejected(service):
	with pytest.raises(InvalidRotationIntervalError):
		await service.set_interval(cfg.emoji_rotation.min_interval_min - 1)


async def test_apply_failure_postpones_retry(service, account, uow):
	await service.add_emojis({111: "😎"})
	account.fail_with = EmojiStatusApplyError(
		"FLOOD_WAIT", retry_after_sec=3600
	)

	with pytest.raises(EmojiStatusApplyError):
		await service.rotate_if_due()

	retry_in = uow.emoji_rotation.row.next_change_at - datetime.now(UTC)
	assert timedelta(minutes=59) < retry_in <= timedelta(hours=1)
	assert uow.emoji_rotation.row.current_emoji is None


async def test_next_due_none_when_nothing_to_rotate(service):
	assert await service.next_due_at() is None  # пустой пул
	await service.add_emojis({111: "😎"})
	await service.set_enabled(False)
	assert await service.next_due_at() is None  # пауза


async def test_next_due_now_for_fresh_pool(service):
	await service.add_emojis({111: "😎"})

	due = await service.next_due_at()

	assert due is not None and due <= datetime.now(UTC)


async def test_next_due_follows_interval(service):
	await service.add_emojis({111: "😎"})
	await service.rotate_now()
	await service.set_interval(60)

	due = await service.next_due_at()

	assert (
		timedelta(minutes=59)
		< due - datetime.now(UTC)
		<= timedelta(minutes=60)
	)


@pytest.mark.parametrize(
	"change",
	[
		lambda s: s.add_emojis({111: "😎"}),
		lambda s: s.set_enabled(False),
		lambda s: s.set_interval(60),
	],
)
async def test_schedule_changes_wake_scheduler(service, wakeup, change):
	await change(service)

	assert await wakeup.wait(timeout=0) is True


# --- Дорожка как в плеере ---


async def alts_in_order(service) -> list[str]:
	return [e.alt for e in (await service.snapshot()).pool]


async def test_next_goes_in_order_and_wraps(service):
	await service.add_emojis({1: "A", 2: "B", 3: "C"})

	played = [(await service.rotate_now()).alt for _ in range(5)]

	assert played == ["A", "B", "C", "A", "B"]


async def test_previous_goes_back_and_wraps(service):
	await service.add_emojis({1: "A", 2: "B", 3: "C"})
	await service.rotate_now()  # A

	played = [(await service.previous()).alt for _ in range(4)]

	assert played == ["C", "B", "A", "C"]


async def test_timer_follows_the_track(service, uow):
	await service.add_emojis({1: "A", 2: "B"})
	await service.rotate_if_due()
	uow.emoji_rotation.row.next_change_at = datetime.now(UTC)

	emoji = await service.rotate_if_due()

	assert emoji.alt == "B"


async def test_added_emojis_go_to_the_end(service):
	await service.add_emojis({1: "A", 2: "B"})
	await service.shuffle()
	await service.add_emojis({3: "C"})

	assert (await alts_in_order(service))[-1] == "C"


async def test_shuffle_keeps_current_first_and_all_tracks(service):
	await service.add_emojis({i: str(i) for i in range(1, 21)})
	await service.rotate_now()
	current = await service.rotate_now()  # «2»

	await service.shuffle()

	order = await alts_in_order(service)
	assert order[0] == current.alt
	assert sorted(order, key=int) == [str(i) for i in range(1, 21)]
	snapshot = await service.snapshot()
	assert snapshot.current_index == 1
	# ⏭ после 🔀 идёт по новому порядку.
	assert (await service.rotate_now()).alt == order[1]


async def test_delete_current_plays_next_in_track(service):
	await service.add_emojis({1: "A", 2: "B", 3: "C"})
	await service.rotate_now()
	b = await service.rotate_now()

	new_current = await service.delete_emoji(b.id)

	assert new_current.alt == "C"
	assert await alts_in_order(service) == ["A", "C"]


async def test_delete_last_track_wraps_to_first(service):
	await service.add_emojis({1: "A", 2: "B"})
	await service.rotate_now()
	b = await service.rotate_now()

	assert (await service.delete_emoji(b.id)).alt == "A"

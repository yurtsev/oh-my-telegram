import asyncio
from types import SimpleNamespace

import pytest

from src.userbot.handlers import (
	UserbotAnimationHandlers,
	UserbotChatActionHandlers,
)
from src.userbot.services.animations import AnimationService
from src.userbot.services.chat_actions import ChatActionService
from src.userbot.services.chat_tasks import ChatTaskRegistry
from src.userbot.texts.animations import MOON_PHASES, AnimationText
from src.userbot.utils import split_graphemes

# --- Графемы ---


@pytest.mark.parametrize(
	("text", "expected"),
	[
		("abc", ["a", "b", "c"]),
		("hi❤️", ["h", "i", "❤️"]),
		("👍🏽ok", ["👍🏽", "o", "k"]),
		("👨‍👩‍👧!", ["👨‍👩‍👧", "!"]),
		("🇷🇺🇺🇸", ["🇷🇺", "🇺🇸"]),
		("й", ["й"]),  # и + комбинируемая кратка
	],
)
def test_split_graphemes(text, expected):
	assert split_graphemes(text) == expected


# --- Кадры ---


def test_typewriter_frames():
	frames = AnimationText.typewriter("hi!", max_frames=30)

	assert frames == ["▌", "h▌", "hi▌", "hi!▌", "hi!", "hi!▌", "hi!"]


def test_typewriter_never_splits_emoji():
	frames = AnimationText.typewriter("a👨‍👩‍👧", max_frames=30)

	assert "a👨‍👩‍👧▌" in frames
	assert all("‍▌" not in frame for frame in frames)  # ZWJ перед курсором


def test_long_typewriter_is_capped():
	text = "x" * 1000
	frames = AnimationText.typewriter(text, max_frames=30)

	assert len(frames) <= 30 + 4
	assert frames[-1] == text


@pytest.mark.parametrize("start", MOON_PHASES)
def test_moon_full_cycle_returns_to_start(start):
	frames = AnimationText.moon_cycle(start)

	assert frames[0] == frames[-1] == start
	assert sorted(frames[:-1]) == sorted(MOON_PHASES)


def test_hearts_end_with_single_heart():
	frames = AnimationText.hearts()

	assert frames[-1] == "❤️"
	assert all(a != b for a, b in zip(frames, frames[1:], strict=False))
	for frame in frames[:-1]:
		lines = frame.split("\n")
		assert len(lines) == len(AnimationText.HEART_SHAPE)
		assert all(len(split_graphemes(line)) == 7 for line in lines)


# --- Реестр задач чата ---


async def test_new_task_cancels_previous_in_same_chat():
	tasks = ChatTaskRegistry()
	started = asyncio.Event()
	first_cancelled = False

	async def long_job():
		nonlocal first_cancelled
		started.set()
		try:
			await asyncio.sleep(10)
		except asyncio.CancelledError:
			first_cancelled = True
			raise

	first = asyncio.create_task(tasks.run(1, long_job()))
	await started.wait()
	await tasks.run(1, asyncio.sleep(0))

	await first  # завершился штатно, без CancelledError наружу
	assert first_cancelled


async def test_stop_cancels_running_task():
	tasks = ChatTaskRegistry()
	runner = asyncio.create_task(tasks.run(1, asyncio.sleep(10)))
	await asyncio.sleep(0)

	assert tasks.cancel(1) is True
	await runner
	assert tasks.cancel(1) is False


# --- Анимации и действия на фейковых событиях ---


class FakeEvent:
	def __init__(self, text: str, groups: tuple = ()) -> None:
		self.raw_text = text
		self.chat_id = 10
		self.pattern_match = SimpleNamespace(group=lambda i: groups[i - 1])
		self.edits: list[str] = []
		self.deleted = False
		self.client = FakeActionClient()

	async def edit(self, text, parse_mode=()):
		assert parse_mode is None
		self.edits.append(text)

	async def delete(self):
		self.deleted = True


class FakeActionClient:
	def __init__(self) -> None:
		self.actions: list[str] = []

	def action(self, _chat_id, action):
		client = self

		class Ctx:
			async def __aenter__(self):
				client.actions.append(action)

			async def __aexit__(self, *_):
				client.actions.append("cancel")

		return Ctx()


@pytest.fixture
def fast(monkeypatch):
	from src.config import cfg

	monkeypatch.setattr(cfg.userbot_commands, "typewriter_delay_sec", 0)
	monkeypatch.setattr(cfg.userbot_commands, "animation_delay_sec", 0)
	monkeypatch.setattr(cfg.userbot_commands, "chat_action_default_sec", 0)


@pytest.mark.usefixtures("fast")
async def test_moon_animation_edits_message():
	event = FakeEvent("!🌕", groups=("🌕",))

	await AnimationService(ChatTaskRegistry()).moon(event)

	assert event.edits == AnimationText.moon_cycle("🌕")


@pytest.mark.usefixtures("fast")
async def test_fake_action_deletes_command_and_holds_action():
	event = FakeEvent("!voice", groups=("voice", None))

	await ChatActionService(ChatTaskRegistry()).fake_action(event)

	assert event.deleted
	assert event.client.actions == ["record-voice", "cancel"]


@pytest.mark.usefixtures("fast")
async def test_fake_action_with_typo_is_ignored():
	event = FakeEvent("!voice 10x", groups=("voice", "10x"))

	await ChatActionService(ChatTaskRegistry()).fake_action(event)

	assert not event.deleted
	assert event.client.actions == []


# --- Паттерны ---


class FakeClient:
	def __init__(self) -> None:
		self.builders: dict[str, object] = {}

	def add_event_handler(self, callback, event):
		self.builders[callback.__name__] = event


@pytest.fixture
async def builders():
	client = FakeClient()
	tasks = ChatTaskRegistry()
	await UserbotAnimationHandlers(AnimationService(tasks)).attach(client)  # type: ignore[arg-type]
	await UserbotChatActionHandlers(ChatActionService(tasks)).attach(client)  # type: ignore[arg-type]
	return client.builders


@pytest.mark.parametrize(
	("handler", "text", "matches"),
	[
		("typewriter", "!type привет", True),
		("typewriter", "!type две\nстроки", True),
		("typewriter", "!type", False),
		("moon", "!🌑", True),
		("moon", "!🌖", True),
		("moon", "!🌚", False),
		("moon", "!🌑🌑", False),
		("hearts", "!❤️", True),
		("hearts", "!❤", True),
		("hearts", "!🧡", False),
		("fake_action", "!typing", True),
		("fake_action", "!voice 2m", True),
		("fake_action", "!round 30s", True),
		("fake_action", "!sticker", True),
		("fake_action", "!dance", False),
		("stop", "!stop", True),
	],
)
async def test_patterns(builders, handler, text, matches):
	assert bool(builders[handler].pattern(text)) is matches


async def test_animations_and_actions_work_in_any_chat(builders):
	assert all(builder.func is None for builder in builders.values())

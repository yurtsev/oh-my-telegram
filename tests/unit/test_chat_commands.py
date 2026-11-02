from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from src.config import cfg
from src.userbot.handlers.commands import UserbotCommandHandlers
from src.userbot.services.commands import ChatCommandService
from src.userbot.services.mute import ChatMuteService
from src.userbot.texts.commands import CommandText
from src.userbot.utils import is_dialog_with_person, parse_duration

# --- Длительность ---


@pytest.mark.parametrize(
	("raw", "expected"),
	[
		("30s", timedelta(seconds=30)),
		("10min", timedelta(minutes=10)),
		("10 min", timedelta(minutes=10)),
		("2h", timedelta(hours=2)),
		("1d", timedelta(days=1)),
		("1w", timedelta(weeks=1)),
		("10m", timedelta(minutes=10)),
		("10м", timedelta(minutes=10)),
		("1mo", timedelta(days=30)),
		("1мес", timedelta(days=30)),
		("1y", timedelta(days=365)),
		("15мин", timedelta(minutes=15)),
		("3д", timedelta(days=3)),
		("1MIN", timedelta(minutes=1)),
		("0s", None),
		("10", None),
		("10x", None),
		("abc", None),
		("100y", None),
	],
)
def test_parse_duration(raw, expected):
	assert parse_duration(raw) == expected


# --- Мьют ---


class FakeMuteRepo:
	def __init__(self) -> None:
		self.rows: dict[int, datetime] = {}

	async def upsert(self, peer_id, until):
		self.rows[peer_id] = until

	async def delete(self, peer_id):
		self.rows.pop(peer_id, None)

	async def delete_expired(self, now):
		self.rows = {p: u for p, u in self.rows.items() if u > now}

	async def list_active(self, now):
		return [
			SimpleNamespace(peer_id=p, until=u)
			for p, u in self.rows.items()
			if u > now
		]


class FakeUow:
	def __init__(self) -> None:
		self.chat_mutes = FakeMuteRepo()

	async def commit(self): ...


@pytest.fixture
def uow() -> FakeUow:
	return FakeUow()


@pytest.fixture
def mutes(uow) -> ChatMuteService:
	@asynccontextmanager
	async def uow_factory():
		yield uow

	return ChatMuteService(uow_factory)  # type: ignore[arg-type]


async def test_mute_and_unmute(mutes):
	await mutes.mute(10, timedelta(minutes=5))
	assert mutes.is_muted(10)
	assert not mutes.is_muted(11)

	await mutes.unmute(10)
	assert not mutes.is_muted(10)


async def test_expired_mute_is_not_active(mutes):
	mutes._until[10] = datetime.now(UTC) - timedelta(seconds=1)

	assert not mutes.is_muted(10)


async def test_mute_survives_restart(uow, mutes):
	await mutes.mute(10, timedelta(days=365))
	uow.chat_mutes.rows[11] = datetime.now(UTC) - timedelta(days=1)

	@asynccontextmanager
	async def uow_factory():
		yield uow

	restarted = ChatMuteService(uow_factory)  # type: ignore[arg-type]
	await restarted.load()

	assert restarted.is_muted(10)
	assert 11 not in uow.chat_mutes.rows  # истёкший дочищен


# --- Команды ---


class FakeEvent:
	def __init__(self, chat_id: int, groups: tuple = ()) -> None:
		self.chat_id = chat_id
		self.pattern_match = SimpleNamespace(group=lambda i: groups[i - 1])
		self.client = object()
		self.edited: str | None = None
		self.deleted = False

	async def edit(self, text):
		self.edited = text

	async def delete(self):
		self.deleted = True


class FakeSpam:
	def __init__(self) -> None:
		self.calls: list[tuple] = []

	async def spam(self, _client, chat_id, count, text):
		self.calls.append((chat_id, count, text))
		return count


@pytest.fixture
def spam() -> FakeSpam:
	return FakeSpam()


@pytest.fixture
def commands(mutes, spam) -> ChatCommandService:
	return ChatCommandService(mutes=mutes, spam=spam)  # type: ignore[arg-type]


async def test_mute_command_edits_and_deletes_peer_messages(commands):
	command = FakeEvent(chat_id=10, groups=("10s",))
	await commands.mute(command)

	assert command.edited == CommandText.muted()
	incoming = FakeEvent(chat_id=10)
	await commands.on_incoming_private(incoming)
	assert incoming.deleted

	other_chat = FakeEvent(chat_id=11)
	await commands.on_incoming_private(other_chat)
	assert not other_chat.deleted


async def test_mute_with_typo_leaves_message_alone(commands, mutes):
	command = FakeEvent(chat_id=10, groups=("10x",))
	await commands.mute(command)

	assert command.edited is None
	assert not mutes.is_muted(10)


async def test_unmute_command(commands, mutes):
	await mutes.mute(10, timedelta(minutes=5))
	command = FakeEvent(chat_id=10)
	await commands.unmute(command)

	assert command.edited == CommandText.unmuted()
	assert not mutes.is_muted(10)


async def test_spam_deletes_command_and_sends(commands, spam):
	command = FakeEvent(chat_id=10, groups=("3", "привет\nмир"))
	await commands.spam(command)

	assert command.deleted
	assert spam.calls == [(10, 3, "привет\nмир")]


# --- Регистрация обработчиков ---


class FakeClient:
	def __init__(self) -> None:
		self.handlers: dict[str, object] = {}

	def add_event_handler(self, callback, event):
		self.handlers[callback.__name__] = event


@pytest.fixture
async def builders(commands):
	client = FakeClient()
	await UserbotCommandHandlers(commands).attach(client)  # type: ignore[arg-type]
	return client.handlers


@pytest.mark.parametrize(
	("handler", "text", "matches"),
	[
		("mute", "!mute 30s", True),
		("mute", "!mute 10 min", True),
		("mute", "!MUTE 1y", True),
		("mute", "!mute", False),
		("mute", "что за !mute 10s", False),
		("unmute", "!unmute", True),
		("unmute", "!unmute now", False),
		("spam", "!spam 5 привет", True),
		("spam", "!spam 2 строка\nвторая", True),
		("spam", "!spam привет", False),
		("spam", "!spam 5", False),
	],
)
async def test_command_patterns(builders, handler, text, matches):
	assert bool(builders[handler].pattern(text)) is matches


@pytest.mark.parametrize(
	("is_private", "chat_id", "expected"),
	[
		(True, 555, True),  # личка с собеседником
		(False, -100123, False),  # группа
		(True, None, False),  # «Избранное» — chat_id подставим владельца
	],
)
def test_commands_only_in_dialog_with_person(is_private, chat_id, expected):
	chat_id = cfg.bot.owner_id if chat_id is None else chat_id
	event = SimpleNamespace(is_private=is_private, chat_id=chat_id)

	assert is_dialog_with_person(event) is expected


async def test_only_mute_is_private_only(builders):
	private_only = {"mute", "unmute", "on_incoming_private"}

	for name, builder in builders.items():
		has_filter = builder.func is is_dialog_with_person
		assert has_filter is (name in private_only), name

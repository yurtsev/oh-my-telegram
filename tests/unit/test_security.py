from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from cryptography.exceptions import InvalidTag

from src.config import cfg
from src.core.crypto import SessionCipher
from src.exc import ForeignAccountError, LoginExpiredError
from src.userbot.services import auth as auth_module
from src.userbot.services.auth import (
	LoginStep,
	PendingLogin,
	UserbotAuthService,
)


def test_cipher_roundtrip_and_fresh_nonce():
	cipher = SessionCipher(SessionCipher.generate_key())

	first = cipher.encrypt("1BVtsOK8Bu...")
	second = cipher.encrypt("1BVtsOK8Bu...")

	assert first != second
	assert cipher.decrypt(first) == "1BVtsOK8Bu..."


def test_cipher_rejects_wrong_key():
	blob = SessionCipher(SessionCipher.generate_key()).encrypt("secret")

	with pytest.raises(InvalidTag):
		SessionCipher(SessionCipher.generate_key()).decrypt(blob)


def test_cipher_rejects_bad_key():
	with pytest.raises(ValueError):
		SessionCipher("short")


class FakeClient:
	def __init__(self, user_id: int) -> None:
		self.user_id = user_id
		self.logged_out = False
		self.disconnected = False
		self.session = SimpleNamespace(save=lambda: "session-string")

	async def sign_in(self, **_kwargs):
		return None

	async def get_me(self):
		return SimpleNamespace(id=self.user_id)

	async def log_out(self):
		self.logged_out = True

	async def disconnect(self):
		self.disconnected = True


class FakeSessions:
	def __init__(self) -> None:
		self.activated: list[int] = []

	async def activate(self, _client, tg_user_id: int) -> None:
		self.activated.append(tg_user_id)


def make_auth(client: FakeClient, minutes: int = 5):
	sessions = FakeSessions()
	auth = UserbotAuthService(sessions=sessions)  # type: ignore[arg-type]
	auth._pending = PendingLogin(
		client=client,  # type: ignore[arg-type]
		phone="+70000000000",
		phone_code_hash="hash",
		expires_at=datetime.now(UTC) + timedelta(minutes=minutes),
	)
	return auth, sessions


async def test_owner_login_is_saved(monkeypatch):
	monkeypatch.setattr(auth_module.cfg.bot, "owner_id", 42)
	auth, sessions = make_auth(FakeClient(user_id=42))

	assert await auth.submit_code("12345") == LoginStep.done
	assert sessions.activated == [42]
	assert auth._pending is None


async def test_foreign_account_is_revoked_not_saved(monkeypatch):
	monkeypatch.setattr(cfg.bot, "owner_id", 42)
	client = FakeClient(user_id=777)
	auth, sessions = make_auth(client)

	with pytest.raises(ForeignAccountError):
		await auth.submit_code("12345")
	assert client.logged_out and client.disconnected
	assert sessions.activated == []


async def test_expired_login_is_rejected_and_dropped():
	client = FakeClient(user_id=42)
	auth, sessions = make_auth(client, minutes=-1)

	with pytest.raises(LoginExpiredError):
		await auth.submit_code("12345")
	assert client.disconnected
	assert auth._pending is None
	assert sessions.activated == []


async def test_code_without_started_login_is_rejected():
	auth = UserbotAuthService(sessions=FakeSessions())  # type: ignore[arg-type]

	with pytest.raises(LoginExpiredError):
		await auth.submit_code("12345")

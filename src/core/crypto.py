import base64
import binascii
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class SessionCipher:
	"""AES-256-GCM для строки сессии юзербота. Ключ живёт в конфиге, а не в
	БД — утечка дампа/бэкапа БД без ключа не даёт доступ к аккаунту.
	Формат блоба: nonce (12 байт) + шифротекст с тегом."""

	# Привязка шифротекста к назначению: блоб нельзя «переиспользовать»
	# в другом поле, даже если когда-то тем же ключом зашифруют что-то ещё.
	AAD = b"oh-my-telegram:userbot-session:v1"

	def __init__(self, key_b64: str) -> None:
		try:
			key = base64.urlsafe_b64decode(key_b64)
		except (binascii.Error, ValueError):
			key = b""
		if len(key) != 32:
			raise ValueError(
				"security.session_key должен быть 32 байтами в base64 — "
				"сгенерируй через `make gen-key`"
			)
		self.aead = AESGCM(key)

	@staticmethod
	def generate_key() -> str:
		return base64.urlsafe_b64encode(os.urandom(32)).decode()

	def encrypt(self, plaintext: str) -> bytes:
		nonce = os.urandom(12)
		return nonce + self.aead.encrypt(nonce, plaintext.encode(), self.AAD)

	def decrypt(self, blob: bytes) -> str:
		"""Бросает `cryptography.exceptions.InvalidTag`, если ключ не тот
		или блоб повреждён."""
		return self.aead.decrypt(blob[:12], blob[12:], self.AAD).decode()

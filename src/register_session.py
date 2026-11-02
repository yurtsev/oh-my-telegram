"""Запасной вход в аккаунт из терминала (основной — через бота, «👤 Аккаунт»).

Использование: `make register`. Telethon спросит телефон, код и пароль 2FA
прямо в терминале; сессия сразу шифруется ключом `security.session_key` и
сохраняется в БД — в консоль и в файлы она не выводится.
"""

import asyncio

from src.config import cfg
from src.core.crypto import SessionCipher
from src.core.db.db import Session, engine
from src.core.db.uow import UnitOfWork
from src.userbot.client import create_userbot_client


async def main() -> None:
	if not cfg.userbot.api_id or not cfg.userbot.api_hash:
		raise SystemExit(
			"Заполни userbot.api_id и userbot.api_hash в config.toml"
		)
	cipher = SessionCipher(cfg.security.session_key)

	client = create_userbot_client()
	await client.start()
	try:
		me = await client.get_me()
		if me.id != cfg.bot.owner_id:
			await client.log_out()
			raise SystemExit(
				f"Вошли в аккаунт {me.id}, а bot.owner_id = "
				f"{cfg.bot.owner_id}. Сессия отозвана и не сохранена."
			)
		async with Session() as session:
			uow = UnitOfWork(session)
			await uow.userbot_session.save(
				me.id, cipher.encrypt(client.session.save())
			)
			await uow.commit()
		print(
			"✅ Сессия зашифрована и сохранена в БД. Перезапусти приложение."
		)
		if not getattr(me, "premium", False):
			print("⚠️  Нет Telegram Premium — эмодзи-статус ставить не выйдет.")
	finally:
		await client.disconnect()
		await engine.dispose()


if __name__ == "__main__":
	asyncio.run(main())

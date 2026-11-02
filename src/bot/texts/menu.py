from src.config import cfg


class MenuText:
	@staticmethod
	def main() -> str:
		return (
			"🎛 <b>oh-my-telegram</b>\n"
			"Пульт управления твоим аккаунтом. Выбери раздел:"
		)

	@staticmethod
	def commands() -> dict[str, str]:
		"""Команды для кнопки «Меню» в Telegram: команда → описание."""
		return {
			"menu": "Главное меню",
			"emoji": "Эмодзи-статус",
			"account": "Подключение аккаунта",
			"help": "Что умеет бот",
			"start": "Главное меню",
		}

	@staticmethod
	def help() -> str:
		commands = cfg.userbot_commands
		return (
			"❓ <b>Что умеет бот</b>\n"
			"\n"
			"<b>Команды бота</b>\n"
			"/menu или /start — главное меню\n"
			"/emoji — эмодзи-статус · /account — аккаунт · /help — эта "
			"справка\n"
			"\n"
			"<b>👤 Аккаунт</b>\n"
			"Подключить → поделиться контактом → код набрать кнопками → "
			"пароль 2FA одним сообщением (бот сразу его удалит). «Выйти» "
			"отзывает сессию в Telegram.\n"
			"\n"
			"<b>🎭 Эмодзи-статус</b> (нужен Premium)\n"
			"Пул — закольцованная дорожка, как плейлист.\n"
			"⏮ / ⏭ — предыдущий / следующий, ⏸ — пауза\n"
			"🗑 — удалить текущий, ➕ — добавить: пришли премиум-эмодзи или "
			"ссылку <code>t.me/addemoji/…</code> на пак целиком\n"
			"📋 Пул — порядок, удаление, 🔀 перемешать\n"
			"⏱ Интервал — пресеты или своё: <code>90</code>, <code>3ч</code>, "
			"<code>1д</code>, <code>1ч30м</code>\n"
			"\n"
			"<b>💬 Команды в чатах</b>\n"
			"Пишешь со своего аккаунта в любом чате:\n"
			"<code>!type текст</code> — печатная машинка с курсором\n"
			"<code>!🌑</code> — лунный цикл от любой фазы до неё же\n"
			"<code>!❤️</code> — анимация сердца\n"
			f"<code>!spam 5 текст</code> — текст 5 раз (до "
			f"{commands.spam_max_count})\n"
			"<code>!typing</code> <code>!voice</code> <code>!round</code> "
			"<code>!video</code> <code>!file</code> <code>!photo</code> "
			"<code>!sticker</code> — собеседник видит «печатает…», "
			"«записывает голосовое…» и т.п. Можно со сроком: "
			f"<code>!voice 2m</code> (по умолчанию "
			f"{commands.chat_action_default_sec}s, максимум "
			f"{commands.chat_action_max_min}m)\n"
			"<code>!stop</code> — остановить анимацию или действие\n"
			"\n"
			"Только в личке:\n"
			"<code>!mute 10m</code> — «тише тише 🤫», сообщения собеседника "
			"удаляются, пока не истечёт срок\n"
			"<code>!unmute</code> — снять досрочно\n"
			"\n"
			"<b>Сроки:</b> <code>30s</code> <code>10m</code> <code>2h</code> "
			"<code>1d</code> <code>1w</code> <code>1mo</code> <code>1y</code> "
			"(или <code>с м ч д нед мес г</code>)\n"
			"Команда с опечаткой просто уходит обычным сообщением."
		)

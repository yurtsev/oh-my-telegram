from datetime import datetime
from html import escape

from src.bot.utils import format_interval, format_local_dt
from src.config import cfg
from src.services.emoji_rotation import RotationSnapshot


class EmojiStatusText:
	@staticmethod
	def screen(snapshot: RotationSnapshot) -> str:
		tz = cfg.app.tz
		state = "✅ включена" if snapshot.enabled else "⏸ на паузе"

		if snapshot.current is not None and snapshot.changed_at is not None:
			position = (
				f" · {snapshot.current_index}/{len(snapshot.pool)}"
				if snapshot.current_index is not None
				else ""
			)
			current = (
				f"{escape(snapshot.current.alt) or '❔'}{position} · с "
				f"{format_local_dt(snapshot.changed_at, tz)}"
			)
		else:
			current = "—"

		if not snapshot.enabled or not snapshot.pool:
			next_change = "—"
		elif snapshot.next_change_at is None:
			next_change = "в течение минуты"
		else:
			next_change = format_local_dt(snapshot.next_change_at, tz)

		# Дорожка по порядку, текущий трек выделен — как плейлист.
		current_id = snapshot.current.id if snapshot.current else None
		track = "".join(
			f"[{escape(e.alt) or '❔'}]"
			if e.id == current_id
			else (escape(e.alt) or "❔")
			for e in snapshot.pool[:30]
		)
		if len(snapshot.pool) > 30:
			track += "…"
		track_line = track if snapshot.pool else "пусто"

		return (
			"🎭 <b>Эмодзи-статус</b>\n"
			"\n"
			f"Ротация: {state}\n"
			f"Интервал: каждые {format_interval(snapshot.interval_min)}\n"
			f"Сейчас: {current}\n"
			f"Следующая смена: {next_change}\n"
			f"Дорожка ({len(snapshot.pool)}): {track_line}\n"
			"\n"
			"<i>В боте эмодзи показаны обычными — у ботов нет права "
			"рисовать премиум-эмодзи. В статусе стоит настоящий.</i>"
		)

	@staticmethod
	def add_prompt() -> str:
		return (
			"➕ <b>Добавление в пул</b>\n"
			"\n"
			"Пришли сообщение с премиум-эмодзи — можно сразу много.\n"
			"Или ссылку на пак: <code>t.me/addemoji/…</code> — добавлю "
			"его целиком.\n"
			"\n"
			"Когда закончишь — жми «Готово»."
		)

	@staticmethod
	def added(added: int, total: int, failed_packs: list[str]) -> str:
		lines = [f"✅ Добавлено: {added}. Всего в пуле: {total}."]
		if failed_packs:
			names = ", ".join(escape(name) for name in failed_packs)
			lines.append(f"⚠️ Не нашёл паки: {names}")
		lines.append("Пришли ещё или жми «Готово».")
		return "\n".join(lines)

	@staticmethod
	def nothing_found() -> str:
		return (
			"🤷 Не вижу премиум-эмодзи. Обычные эмодзи в статус ставить "
			"нельзя — только кастомные (из паков). Пришли их или ссылку "
			"на пак."
		)

	@staticmethod
	def pool_screen(count: int) -> str:
		if count == 0:
			return (
				"📋 <b>Пул пуст</b>\nДобавь эмодзи, чтобы ротация заработала."
			)
		return (
			f"📋 <b>Дорожка: {count}</b>\n"
			"Эмодзи идут по порядку и по кругу, ▶️ — сейчас в статусе.\n"
			"Нажми на эмодзи, чтобы удалить его, 🔀 — перемешать."
		)

	@staticmethod
	def interval_prompt(current_min: int) -> str:
		return (
			"⏱ <b>Как часто менять?</b>\n"
			f"Сейчас: каждые {format_interval(current_min)}."
		)

	@staticmethod
	def custom_interval_prompt(min_min: int, max_min: int) -> str:
		return (
			"✏️ Пришли интервал: <code>90</code> (минуты), "
			"<code>2ч</code>, <code>1д</code>, <code>1ч30м</code>.\n"
			f"От {format_interval(min_min)} до {format_interval(max_min)}."
		)

	@staticmethod
	def interval_invalid(min_min: int, max_min: int) -> str:
		return (
			"❌ Не понял интервал. Нужно от "
			f"{format_interval(min_min)} до {format_interval(max_min)}, "
			"например <code>3ч</code>."
		)

	@staticmethod
	def interval_set(minutes: int) -> str:
		return f"⏱ Теперь меняю каждые {format_interval(minutes)}"

	@staticmethod
	def rotated(alt: str) -> str:
		return f"Поставил {alt or 'новый'}"

	@staticmethod
	def deleted(new_alt: str | None) -> str:
		if new_alt is None:
			return "🗑 Удалено"
		return f"🗑 Удалено, теперь в статусе {new_alt or 'другой'}"

	@staticmethod
	def shuffled() -> str:
		return "🔀 Перемешал — текущий играет дальше, остальные вразнобой"

	@staticmethod
	def account_not_connected() -> str:
		return "Аккаунт не подключён — зайди в «👤 Аккаунт» и подключи его"

	@staticmethod
	def deleted_not_connected() -> str:
		return "🗑 Удалено из пула. Статус сменится, когда подключишь аккаунт"

	@staticmethod
	def rotation_stopped_revoked() -> str:
		return (
			"🔌 <b>Сессия аккаунта больше не действует</b>\n"
			"Её отозвали в «Устройствах» или сменили пароль. Ротация "
			"эмодзи остановлена — подключи аккаунт заново в «👤 Аккаунт»."
		)

	@staticmethod
	def no_current() -> str:
		return "Сейчас в статусе ничего из пула"

	@staticmethod
	def empty_pool() -> str:
		return "Пул пуст — сначала добавь эмодзи"

	@staticmethod
	def apply_failed(reason: str) -> str:
		return (
			f"Telegram не дал сменить статус: {reason}. "
			"Эмодзи-статус работает только с Telegram Premium."
		)

	@staticmethod
	def rotation_failed_notify(reason: str, retry_at: datetime | None) -> str:
		retry = (
			f"\nПовторю в {format_local_dt(retry_at, cfg.app.tz)}."
			if retry_at is not None
			else ""
		)
		return (
			"⚠️ <b>Не получилось сменить эмодзи-статус</b>\n"
			f"Telegram ответил: <code>{escape(reason)}</code>{retry}"
		)

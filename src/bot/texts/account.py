from html import escape

from src.bot.utils import format_local_dt
from src.config import cfg
from src.userbot.services.session import UserbotSessionInfo


class AccountText:
	@staticmethod
	def screen(info: UserbotSessionInfo) -> str:
		if info.connected and info.created_at is not None:
			status = (
				"✅ подключён\n"
				f"Сессия выпущена: {format_local_dt(info.created_at, cfg.app.tz)}\n"
				"В Telegram она видна в «Настройки → Устройства» как "
				f"«{escape(cfg.userbot.device_model)}»."
			)
		else:
			status = "❌ не подключён"
		return (
			"👤 <b>Аккаунт</b>\n"
			"\n"
			f"Статус: {status}\n"
			"\n"
			"<i>Храню только зашифрованную сессию. Телефон, код и пароль "
			"нигде не сохраняются.</i>"
		)

	@staticmethod
	def ask_contact() -> str:
		return (
			"📱 Нажми «Поделиться контактом» — на этот номер Telegram "
			"пришлёт код входа."
		)

	@staticmethod
	def not_own_contact() -> str:
		return "Это не твой контакт. Нажми кнопку «Поделиться контактом»."

	@staticmethod
	def sending_code() -> str:
		return "⏳ Запрашиваю код…"

	@staticmethod
	def code_prompt(entered: int, *, invalid: bool = False) -> str:
		# Код не показываем даже самому себе — только сколько цифр набрано.
		slots = " ".join(["●"] * entered + ["_"] * max(0, 5 - entered))
		warning = "❌ Неверный код, набери заново.\n\n" if invalid else ""
		return (
			f"{warning}🔢 <b>Код из Telegram</b>\n"
			"Набери его кнопками ниже. <b>Не пересылай и не вставляй код "
			"сообщением</b> — Telegram аннулирует код, увидев его в "
			"переписке.\n"
			"\n"
			f"<code>{slots}</code>"
		)

	@staticmethod
	def code_too_short() -> str:
		return "Код — минимум 5 цифр"

	@staticmethod
	def ask_password() -> str:
		return (
			"🔐 <b>Включена двухэтапная проверка</b>\n"
			"Пришли пароль одним сообщением — я сразу удалю его из чата "
			"и никуда не сохраню."
		)

	@staticmethod
	def invalid_password() -> str:
		return "❌ Неверный пароль. Пришли ещё раз (сообщение я удалил)."

	@staticmethod
	def password_not_deleted() -> str:
		return (
			"⚠️ Не смог удалить сообщение с паролем — удали его из чата "
			"вручную."
		)

	@staticmethod
	def expired() -> str:
		return "⌛️ Вход истёк или не был начат. Начни заново."

	@staticmethod
	def login_failed(reason: str) -> str:
		return (
			"❌ Telegram отказал во входе: "
			f"<code>{escape(reason)}</code>\nПопробуй позже."
		)

	@staticmethod
	def foreign_account() -> str:
		return (
			"🚫 Это не твой аккаунт (ID не совпадает с owner_id). Сессию "
			"я сразу отозвал и не сохранил."
		)

	@staticmethod
	def connected() -> str:
		return "✅ Аккаунт подключён."

	@staticmethod
	def cancelled() -> str:
		return "Вход отменён."

	@staticmethod
	def logout_confirm() -> str:
		return (
			"🚪 Выйти? Сессия будет отозвана в Telegram и стёрта из БД. "
			"Правила (ротация эмодзи) перестанут работать до нового входа."
		)

	@staticmethod
	def logged_out() -> str:
		return "Сессия отозвана"

	@staticmethod
	def not_connected_on_start() -> str:
		return (
			"🔌 Аккаунт не подключён — правила не работают.\n"
			"Подключи его: /account"
		)

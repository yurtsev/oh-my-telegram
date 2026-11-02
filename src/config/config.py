from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from pydantic_settings import (
	BaseSettings,
	PydanticBaseSettingsSource,
	SettingsConfigDict,
	TomlConfigSettingsSource,
)

BASE_DIR = Path(__file__).parent.parent.parent
TOML_SETTINGS_PATH = BASE_DIR / "config.toml"


class Logging(BaseModel):
	level: str = "INFO"


class App(BaseModel):
	timezone: str = "Europe/Moscow"

	@property
	def tz(self) -> ZoneInfo:
		return ZoneInfo(self.timezone)


class Bot(BaseModel):
	token: str = ""
	owner_id: int = 0


class Userbot(BaseModel):
	api_id: int = 0
	api_hash: str = ""
	# Так новая сессия подписана в «Настройки → Устройства».
	device_model: str = "oh-my-telegram"
	login_timeout_min: int = 5


class UserbotCommands(BaseModel):
	# Потолок для `!spam` — больше Telegram быстро ответит flood wait'ом
	# и может временно ограничить аккаунт.
	spam_max_count: int = 50
	spam_delay_sec: float = 0.4
	# Анимации: пауза между кадрами (правками сообщения). Чаще ~0.3 с
	# Telegram начинает отвечать flood wait'ом.
	typewriter_delay_sec: float = 0.4
	typewriter_max_frames: int = 30
	animation_delay_sec: float = 0.6
	# Фейковые «печатает…»/«записывает голосовое…».
	chat_action_default_sec: int = 30
	chat_action_max_min: int = 10


class Security(BaseModel):
	# 32 байта в base64 — ключ шифрования сессии аккаунта в БД.
	session_key: str = ""


class Database(BaseModel):
	postgres_username: str = "postgres"
	postgres_db: str = "oh_my_telegram"
	postgres_port: int = 5432
	postgres_host: str = "localhost"
	postgres_password: str = "postgres"

	def _get_effective_host(self) -> str:
		# Один config.toml и для локального запуска, и для Compose: внутри
		# контейнера localhost — это сам контейнер, а не postgres.
		in_docker = Path("/.dockerenv").exists()
		if in_docker and self.postgres_host in ("localhost", "127.0.0.1"):
			return "postgres"
		return self.postgres_host

	@property
	def async_database_url(self) -> str:
		return (
			f"postgresql+asyncpg://{self.postgres_username}:"
			f"{self.postgres_password}@{self._get_effective_host()}:"
			f"{self.postgres_port}/{self.postgres_db}"
		)


class EmojiRotation(BaseModel):
	default_interval_min: int = 24 * 60
	min_interval_min: int = 5
	max_interval_min: int = 7 * 24 * 60
	retry_delay_min: int = 10


class Config(BaseSettings):
	model_config = SettingsConfigDict(
		extra="ignore",
		env_nested_delimiter="__",
		toml_file=TOML_SETTINGS_PATH,
	)

	logging: Logging = Logging()
	app: App = App()
	bot: Bot = Bot()
	userbot: Userbot = Userbot()
	security: Security = Security()
	userbot_commands: UserbotCommands = UserbotCommands()
	database: Database = Database()
	emoji_rotation: EmojiRotation = EmojiRotation()

	@classmethod
	def settings_customise_sources(
		cls,
		settings_cls: type[BaseSettings],
		init_settings: PydanticBaseSettingsSource,
		env_settings: PydanticBaseSettingsSource,
		dotenv_settings: PydanticBaseSettingsSource,
		file_secret_settings: PydanticBaseSettingsSource,
	) -> tuple[PydanticBaseSettingsSource, ...]:
		del init_settings, dotenv_settings, file_secret_settings
		# Переменные окружения (BOT__TOKEN=...) перекрывают config.toml.
		return env_settings, TomlConfigSettingsSource(settings_cls)


cfg = Config()

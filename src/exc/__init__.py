from src.exc.base import AppError
from src.exc.emoji_status import (
	EmojiStatusApplyError,
	EmojiStatusError,
	EmptyEmojiPoolError,
	InvalidRotationIntervalError,
)
from src.exc.userbot import (
	ForeignAccountError,
	InvalidLoginCodeError,
	InvalidPasswordError,
	LoginError,
	LoginExpiredError,
	LoginFailedError,
	UserbotError,
	UserbotNotAuthorizedError,
)

__all__ = [
	"AppError",
	"EmojiStatusApplyError",
	"EmojiStatusError",
	"EmptyEmojiPoolError",
	"ForeignAccountError",
	"InvalidLoginCodeError",
	"InvalidPasswordError",
	"InvalidRotationIntervalError",
	"LoginError",
	"LoginExpiredError",
	"LoginFailedError",
	"UserbotError",
	"UserbotNotAuthorizedError",
]

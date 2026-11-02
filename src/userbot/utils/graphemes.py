import unicodedata

ZWJ = "‍"


def is_extending(char: str) -> bool:
	"""Символ, который приклеивается к предыдущему: вариационные
	селекторы, ZWJ, тон кожи, теги флагов, keycap, комбинируемые знаки."""
	code = ord(char)
	return (
		char == ZWJ
		or char in "︎️⃣"
		or 0x1F3FB <= code <= 0x1F3FF
		or 0xE0020 <= code <= 0xE007F
		or unicodedata.combining(char) != 0
	)


def is_regional_indicator(char: str) -> bool:
	return 0x1F1E6 <= ord(char) <= 0x1F1FF


def split_graphemes(text: str) -> list[str]:
	"""Делит текст на видимые символы так, чтобы не разрывать эмодзи:
	«👨‍👩‍👧», «👍🏽», флаги «🇷🇺» и «❤️» остаются целыми. Упрощённая версия
	UAX #29 — без внешней зависимости, для эффекта печатной машинки
	этого достаточно."""
	clusters: list[str] = []
	for char in text:
		if clusters and (
			is_extending(char)
			or clusters[-1].endswith(ZWJ)
			or (
				len(clusters[-1]) == 1
				and is_regional_indicator(clusters[-1])
				and is_regional_indicator(char)
			)
		):
			clusters[-1] += char
		else:
			clusters.append(char)
	return clusters

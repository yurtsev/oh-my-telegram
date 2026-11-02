from math import ceil

from src.userbot.utils import split_graphemes

MOON_PHASES = ("🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘")


class AnimationText:
	"""Кадры анимаций — то, что собеседник видит в редактируемом
	сообщении. Каждый метод возвращает готовый список кадров."""

	TYPE_CURSOR = "▌"

	HEART_SHAPE = (
		"0110110",
		"1111111",
		"1111111",
		"0111110",
		"0011100",
		"0001000",
	)
	HEART_COLORS = ("❤️", "🧡", "💛", "💚", "💙", "💜")
	HEART_BACKGROUND = "🤍"

	@staticmethod
	def typewriter(text: str, max_frames: int) -> list[str]:
		"""Печатная машинка с курсором: «▌» → «пр▌» → «прив▌» → … →
		мигание курсора в конце → чистый текст."""
		cursor = AnimationText.TYPE_CURSOR
		chars = split_graphemes(text)
		# Длинный текст печатаем по нескольку символов за кадр — число
		# правок ограничено, иначе Telegram ответит flood wait'ом.
		step = max(1, ceil(len(chars) / max_frames))
		frames = [cursor]
		for end in range(step, len(chars) + step, step):
			frames.append("".join(chars[:end]) + cursor)
		frames += [text, text + cursor, text]
		return frames

	@staticmethod
	def moon_cycle(start: str) -> list[str]:
		"""Полный цикл от `start` до него же: 🌒 → 🌓 → … → 🌑 → 🌒."""
		index = MOON_PHASES.index(start)
		return [
			MOON_PHASES[(index + step) % len(MOON_PHASES)]
			for step in range(len(MOON_PHASES) + 1)
		]

	@staticmethod
	def hearts() -> list[str]:
		"""Пиксельное сердце: рисуется построчно, переливается цветами,
		идёт радугой и сворачивается в один ❤️ — одиночное эмодзи Telegram
		показывает большим анимированным (бьющимся) сердцем."""
		colors = AnimationText.HEART_COLORS
		rows = len(AnimationText.HEART_SHAPE)

		drawing = [
			AnimationText._heart(
				lambda row, shown=shown: colors[0] if row < shown else None
			)
			for shown in range(1, rows + 1)
		]
		color_cycle = [
			AnimationText._heart(lambda _row, color=color: color)
			for color in colors[1:] + colors[:1]
		]
		rainbow = [
			AnimationText._heart(
				lambda row, shift=shift: colors[(row + shift) % len(colors)]
			)
			for shift in range(len(colors))
		]
		return [*drawing, *color_cycle, *rainbow, colors[0]]

	@staticmethod
	def _heart(color_for_row) -> str:
		"""Рендер сетки сердца; `color_for_row(row)` — цвет строки или None,
		если строка ещё не нарисована (остаётся фоном)."""
		background = AnimationText.HEART_BACKGROUND
		lines = []
		for row, mask in enumerate(AnimationText.HEART_SHAPE):
			color = color_for_row(row)
			lines.append(
				"".join(
					color if cell == "1" and color is not None else background
					for cell in mask
				)
			)
		return "\n".join(lines)

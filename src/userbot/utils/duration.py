import re
from datetime import timedelta

DURATION_RE = re.compile(r"^(\d+)\s*([a-zа-яё]+)$", re.IGNORECASE)

# «m» — минуты, месяц — только «mo»/«мес»: так короче для самого частого
# случая (мьют на 10m), а месяц не спутать с минутой.
DURATION_UNITS: dict[str, timedelta] = {
	**dict.fromkeys(("s", "sec", "с", "сек"), timedelta(seconds=1)),
	**dict.fromkeys(("m", "min", "мин", "м"), timedelta(minutes=1)),
	**dict.fromkeys(("h", "hr", "ч", "час"), timedelta(hours=1)),
	**dict.fromkeys(("d", "day", "д", "дн"), timedelta(days=1)),
	**dict.fromkeys(("w", "wk", "нед"), timedelta(weeks=1)),
	**dict.fromkeys(("mo", "mon", "мес"), timedelta(days=30)),
	**dict.fromkeys(("y", "yr", "г", "год"), timedelta(days=365)),
}

MAX_DURATION = timedelta(days=5 * 365)


def parse_duration(raw: str) -> timedelta | None:
	"""«30s» → 30 сек, «10m»/«10min» → 10 мин, «1d», «1mo» (месяц), «1y».
	None — не разобралось, ноль или длиннее MAX_DURATION."""
	match = DURATION_RE.match(raw.strip())
	if match is None:
		return None
	amount, unit = int(match.group(1)), match.group(2).lower()
	if unit not in DURATION_UNITS or amount == 0:
		return None
	duration = DURATION_UNITS[unit] * amount
	return duration if duration <= MAX_DURATION else None

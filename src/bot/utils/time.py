from datetime import datetime
from zoneinfo import ZoneInfo


def format_interval(minutes: int) -> str:
	"""90 → «1 ч 30 мин», 1440 → «1 д», 2160 → «1 д 12 ч»."""
	days, rest = divmod(minutes, 24 * 60)
	hours, mins = divmod(rest, 60)
	parts = [
		f"{value} {unit}"
		for value, unit in ((days, "д"), (hours, "ч"), (mins, "мин"))
		if value
	]
	return " ".join(parts) or "0 мин"


def format_local_dt(dt: datetime, tz: ZoneInfo) -> str:
	return dt.astimezone(tz).strftime("%d.%m %H:%M")

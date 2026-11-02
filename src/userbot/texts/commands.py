class CommandText:
	"""То, во что превращаются команды в чате — это видит собеседник."""

	@staticmethod
	def muted() -> str:
		return "тише тише 🤫"

	@staticmethod
	def unmuted() -> str:
		return "ладно, говори 🗣"

from dishka import Provider, Scope, provide

from src.core.db.uow import UowFactory
from src.userbot.handlers import (
	UserbotAnimationHandlers,
	UserbotChatActionHandlers,
	UserbotCommandHandlers,
	UserbotRouter,
)
from src.userbot.services.animations import AnimationService
from src.userbot.services.chat_actions import ChatActionService
from src.userbot.services.chat_tasks import ChatTaskRegistry
from src.userbot.services.commands import ChatCommandService
from src.userbot.services.mute import ChatMuteService
from src.userbot.services.spam import SpamService


class UserbotCommandsProvider(Provider):
	@provide(scope=Scope.APP)
	def chat_mute_service(self, uow_factory: UowFactory) -> ChatMuteService:
		return ChatMuteService(uow_factory)

	@provide(scope=Scope.APP)
	def spam_service(self) -> SpamService:
		return SpamService()

	@provide(scope=Scope.APP)
	def chat_command_service(
		self, mutes: ChatMuteService, spam: SpamService
	) -> ChatCommandService:
		return ChatCommandService(mutes=mutes, spam=spam)

	@provide(scope=Scope.APP)
	def userbot_command_handlers(
		self, commands: ChatCommandService
	) -> UserbotCommandHandlers:
		return UserbotCommandHandlers(commands)

	@provide(scope=Scope.APP)
	def chat_task_registry(self) -> ChatTaskRegistry:
		return ChatTaskRegistry()

	@provide(scope=Scope.APP)
	def animation_service(self, tasks: ChatTaskRegistry) -> AnimationService:
		return AnimationService(tasks)

	@provide(scope=Scope.APP)
	def chat_action_service(
		self, tasks: ChatTaskRegistry
	) -> ChatActionService:
		return ChatActionService(tasks)

	@provide(scope=Scope.APP)
	def userbot_animation_handlers(
		self, animations: AnimationService
	) -> UserbotAnimationHandlers:
		return UserbotAnimationHandlers(animations)

	@provide(scope=Scope.APP)
	def userbot_chat_action_handlers(
		self, actions: ChatActionService
	) -> UserbotChatActionHandlers:
		return UserbotChatActionHandlers(actions)

	@provide(scope=Scope.APP)
	def userbot_router(
		self,
		commands: UserbotCommandHandlers,
		animations: UserbotAnimationHandlers,
		chat_actions: UserbotChatActionHandlers,
	) -> UserbotRouter:
		return UserbotRouter(commands, animations, chat_actions)

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from src.core.db.db import Session, engine
from src.core.db.uow import UnitOfWork, UowFactory


class SqlAlchemyUowFactory:
	def __init__(self, session_factory: async_sessionmaker):
		self.session_factory = session_factory

	@asynccontextmanager
	async def __call__(self) -> AsyncIterator[UnitOfWork]:
		async with self.session_factory() as session:
			uow = UnitOfWork(session)
			try:
				yield uow
			except Exception:
				await uow.rollback()
				raise


class DbProvider(Provider):
	@provide(scope=Scope.APP)
	async def get_engine(self) -> AsyncIterator[AsyncEngine]:
		yield engine
		await engine.dispose()

	@provide(scope=Scope.APP)
	def get_uow_factory(self, _engine: AsyncEngine) -> UowFactory:
		# Зависимость от engine — чтобы dispose() отработал при закрытии
		# контейнера, даже если engine больше никто не запрашивает.
		return SqlAlchemyUowFactory(Session)

"""
Database connection and session management for the intelligence pipeline.

Provides async SQLAlchemy session management with proper lifecycle handling.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from .models import Base


class DatabaseManager:
    """
    Manages database connections and sessions.

    Provides async context managers for database sessions and handles
    engine lifecycle management.
    """

    def __init__(self, database_url: str, echo: bool = False):
        """
        Initialize the database manager.

        Args:
            database_url: SQLAlchemy database URL (use sqlite+aiosqlite:// for async SQLite)
            echo: Whether to log SQL statements (useful for debugging)
        """
        self.database_url = database_url
        self.echo = echo
        self._engine = None
        self._session_factory = None

    def _create_engine(self):
        """Create the async SQLAlchemy engine."""
        # Use NullPool for SQLite to avoid connection pool issues
        # For other databases, you may want to use a different pooling strategy
        return create_async_engine(
            self.database_url,
            echo=self.echo,
            poolclass=NullPool,
            future=True,
        )

    def _create_session_factory(self):
        """Create the async session factory."""
        return async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    async def init_db(self) -> None:
        """
        Initialize the database by creating all tables.

        This should be called on application startup.
        """
        self._engine = self._create_engine()
        self._session_factory = self._create_session_factory()

        # Create all tables
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        """
        Close the database engine.

        This should be called on application shutdown.
        """
        if self._engine:
            await self._engine.dispose()

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session.

        Usage:
            async with db_manager.get_session() as session:
                result = await session.execute(...)
                await session.commit()

        Yields:
            AsyncSession: An async SQLAlchemy session
        """
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call init_db() first.")

        async with self._session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Global database manager instance
_db_manager: DatabaseManager | None = None


def init_database(database_url: str, echo: bool = False) -> DatabaseManager:
    """
    Initialize the global database manager.

    Args:
        database_url: SQLAlchemy database URL
        echo: Whether to log SQL statements

    Returns:
        DatabaseManager instance
    """
    global _db_manager
    _db_manager = DatabaseManager(database_url, echo=echo)
    return _db_manager


def get_db_manager() -> DatabaseManager:
    """
    Get the global database manager instance.

    Returns:
        DatabaseManager instance

    Raises:
        RuntimeError: If database has not been initialized
    """
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get a database session.

    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db_session)):
            result = await db.execute(select(Item))
            return result.scalars().all()

    Yields:
        AsyncSession: An async SQLAlchemy session
    """
    db_manager = get_db_manager()
    async with db_manager.get_session() as session:
        yield session

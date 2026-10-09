"""SQLAlchemy ORM models for HabitPact."""

from __future__ import annotations

import datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class Guild(Base):
    """Represents a Discord guild (server) where the bot is installed."""

    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    joined_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    users: Mapped[list[User]] = relationship(
        back_populates="guild", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Guild id={self.id} name={self.name!r}>"


class User(Base):
    """A Discord user's profile within a specific guild."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("discord_id", "guild_id", name="uq_user_discord_guild"),
        Index("idx_users_discord_guild", "discord_id", "guild_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    discord_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False
    )
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    remind_at: Mapped[datetime.time | None] = mapped_column(Time, nullable=True, default=None)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    guild: Mapped[Guild] = relationship(back_populates="users")
    habits: Mapped[list[Habit]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} discord_id={self.discord_id} guild_id={self.guild_id}>"


class Habit(Base):
    """A habit that a user wants to track."""

    __tablename__ = "habits"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_habit_user_name"),
        Index("idx_habits_user_active", "user_id", postgresql_where="archived_at IS NULL"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    archived_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="habits")
    checkins: Mapped[list[Checkin]] = relationship(
        back_populates="habit", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        """Whether this habit is still being tracked (not archived)."""
        return self.archived_at is None

    def __repr__(self) -> str:
        return f"<Habit id={self.id} name={self.name!r} active={self.is_active}>"


class Checkin(Base):
    """A single daily check-in for a habit."""

    __tablename__ = "checkins"
    __table_args__ = (
        UniqueConstraint("habit_id", "checked_date", name="uq_checkin_habit_date"),
        Index("idx_checkins_habit_date", "habit_id", "checked_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    habit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False
    )
    checked_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    habit: Mapped[Habit] = relationship(back_populates="checkins")

    def __repr__(self) -> str:
        return f"<Checkin id={self.id} habit_id={self.habit_id} date={self.checked_date}>"

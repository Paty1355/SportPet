
from sqlalchemy import Connection, Engine, text

import app.models
from app.db.base import Base
from app.db.session import engine

USER_COLUMNS = {
    "sex": "VARCHAR(1)",
    "birth_date": "DATE",
    "weight_kg": "DOUBLE PRECISION",
    "height_cm": "DOUBLE PRECISION",
    "share_pet": "BOOLEAN NOT NULL DEFAULT TRUE",
    "post_workout_reporting_frequency": "VARCHAR(16) NOT NULL DEFAULT 'weekly'",
    "timezone": "VARCHAR(64) NOT NULL DEFAULT 'Europe/Warsaw'",
}


def upgrade_connection(connection: Connection) -> None:
    if connection.dialect.name == "postgresql":
        connection.execute(text("SELECT pg_advisory_xact_lock(20261004)"))
    Base.metadata.create_all(bind=connection)
    if connection.dialect.name != "postgresql":
        return
    for name, definition in USER_COLUMNS.items():
        connection.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {name} {definition}"))
    connection.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS post_workout_checkin_id VARCHAR(36)"))
    constraints = {
        (
            "users",
            "ck_users_post_workout_frequency",
        ): "CHECK (post_workout_reporting_frequency IN ('daily', 'weekly', 'monthly'))",
        (
            "messages",
            "fk_messages_post_workout_owner",
        ): (
            "FOREIGN KEY (post_workout_checkin_id, user_id) "
            "REFERENCES post_workout_checkins(id, user_id) ON DELETE CASCADE"
        ),
        (
            "messages",
            "ck_messages_post_workout_agent",
        ): "CHECK (post_workout_checkin_id IS NULL OR agent = 'post_workout')",
    }
    for (table, name), definition in constraints.items():
        connection.execute(
            text(f"""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = '{name}' AND conrelid = '{table}'::regclass
                ) THEN
                    ALTER TABLE {table} ADD CONSTRAINT {name} {definition};
                END IF;
            END $$;
        """)
        )
    connection.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_messages_post_workout_session "
            "ON messages (user_id, post_workout_checkin_id, created_at)"
        )
    )


def initialize_database(database_engine: Engine = engine) -> None:
    with database_engine.begin() as connection:
        upgrade_connection(connection)


if __name__ == "__main__":
    initialize_database()
    print("Database schema is up to date.")

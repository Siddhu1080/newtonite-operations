
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app import models  # Registers all SQLAlchemy models


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError(
        "Set TEST_DATABASE_URL to your separate test database before running tests."
    )

test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    # Ensure tests never run against the development database.
    with test_engine.connect() as connection:
        database_name = connection.execute(
            text("SELECT DATABASE()")
        ).scalar_one()

    if database_name != "newtonite_operations_test":
        pytest.fail(
            "Tests must use newtonite_operations_test, "
            f"not {database_name!r}."
        )

    Base.metadata.create_all(bind=test_engine)

    # Create the idempotency table after its referenced tables exist.
    with test_engine.begin() as connection:
        connection.execute(
            text("""
                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    idempotency_key VARCHAR(255) NOT NULL,
                    request_hash CHAR(64) NOT NULL,
                    work_item_id INT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_user_idempotency_key
                        UNIQUE (user_id, idempotency_key),
                    CONSTRAINT fk_idempotency_user
                        FOREIGN KEY (user_id) REFERENCES users(id),
                    CONSTRAINT fk_idempotency_work_item
                        FOREIGN KEY (work_item_id) REFERENCES work_items(id)
                )
            """)
        )

    yield

    # Drop the referencing table first to avoid foreign-key errors.
    with test_engine.begin() as connection:
        connection.execute(
            text("DROP TABLE IF EXISTS idempotency_keys")
        )

    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()

    session = TestingSessionLocal(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()

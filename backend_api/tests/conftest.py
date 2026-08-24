import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from database import Base, get_db
from main import app
from core.security import create_access_token
from passlib.context import CryptContext

# In-memory SQLite for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Provides a fresh transactional session for each test function."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    """Creates a default admin user in the test database."""
    hashed_pwd = pwd_context.hash("AdminPassword123!")
    user = models.User(
        email="test_admin@example.com",
        password_hash=hashed_pwd,
        role="admin"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    perm = models.UserPermission(
        user_id=user.id,
        can_view_screenshots=True,
        can_manage_rules=True,
        can_view_logs=True,
        can_remote_control=True,
        can_manage_users=True
    )
    db_session.add(perm)
    db_session.commit()

    token = create_access_token({
        "sub": user.email,
        "user_id": str(user.id),
        "role": "admin",
        "is_system_admin": True
    })
    return {"user": user, "token": token, "password": "AdminPassword123!"}

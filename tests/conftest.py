import tempfile

import pytest
from fastapi.testclient import TestClient

# Use a temp file for test database to avoid in-memory SQLite connection issues
_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
import os
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file.name}"

# Now import app modules (they'll read the env var)
from app.database import engine, Base
from app.main import app


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_client(client):
    r = client.post("/auth/register", json={
        "email": "auth@test.pl",
        "username": "authuser",
        "password": "Test1234!"
    })
    token = r.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client

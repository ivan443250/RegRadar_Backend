import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ai.gateway.config import reset_config


@pytest.fixture()
def client():
    """FastAPI TestClient с сбросом конфигурации gateway между тестами."""
    reset_config()
    with TestClient(app) as c:
        yield c
    reset_config()

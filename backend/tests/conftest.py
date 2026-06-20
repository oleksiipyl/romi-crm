import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.services.ai_brain import AIBrain, OpenAIChatClient
from app.services.kb import load_kb_from_path
from pathlib import Path


@pytest.fixture(autouse=True)
def fast_typing_delay(monkeypatch):
    """Skip real 4-8s webhook delay in tests unless overridden."""

    async def instant_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr("app.api.v1.ai_responder.asyncio.sleep", instant_sleep)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    kb_src = Path(__file__).resolve().parent.parent / "data" / "fast_glass_kb.json"
    return Settings(
        database_url="sqlite://",
        openai_api_key="",
        openai_model="gpt-4o",
        zapier_webhook_secret="",
        kb_path=str(kb_src),
        app_env="test",
    )


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def kb(settings: Settings):
    return load_kb_from_path(settings.kb_file_path)


class MockMessage:
    def __init__(self, content: str | None = None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class MockChatClient:
    def __init__(self, responses: list[MockMessage] | None = None):
        self.responses = responses or [
            MockMessage(
                content=(
                    "MSG1: Hey Victor! This is Robert from Fast Glass. What's the best "
                    "number to reach you? I'll call right back with an exact price!\n"
                    "MSG2: We handle patio door glass replacement and similar work across "
                    "LA — typical range is $400-$900 depending on size and glass type."
                )
            )
        ]
        self.calls = 0

    def generate(self, messages, tools):
        msg = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1
        return {
            "message": msg,
            "tokens_input": 120,
            "tokens_output": 45,
        }


@pytest.fixture
def mock_brain(settings: Settings, kb, mock_chat_client: MockChatClient):
    return AIBrain(kb=kb, settings=settings, client=mock_chat_client)


@pytest.fixture
def mock_chat_client():
    return MockChatClient()


@pytest.fixture
def client(db_engine, settings: Settings, mock_brain: AIBrain):
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db] = override_get_db
    from app.services.ai_brain import get_ai_brain

    app.dependency_overrides[get_ai_brain] = lambda: mock_brain

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

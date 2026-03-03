"""Unit tests for mailbox models and service."""
import pytest
from uuid import uuid4
from api.models import MailboxMessageCreate, MailboxMessageResponse


def test_mailbox__message_create__valid():
    m = MailboxMessageCreate(
        problem_id=uuid4(), from_agent="orchestrator",
        to_agent="data-engineer", body="Please ingest data.csv",
    )
    assert m.from_agent == "orchestrator"
    assert m.subject is None


def test_mailbox__message_create__requires_body():
    import pydantic
    with pytest.raises(pydantic.ValidationError):
        MailboxMessageCreate(  # type: ignore[call-arg]
            problem_id=uuid4(), from_agent="a", to_agent="b"
        )


def test_mailbox__service__publish__handles_no_redis():
    """MailboxService publish should not raise when Redis unavailable."""
    import asyncio
    from api.services.mailbox_service import MailboxService
    svc = MailboxService("redis://localhost:9999")  # bad port
    # Should not raise — Redis errors are silently swallowed
    asyncio.get_event_loop().run_until_complete(
        svc.publish("test-agent", "msg-1", "hello")
    )


def test_mailbox__service__unread_count__returns_zero_without_redis():
    import asyncio
    from api.services.mailbox_service import MailboxService
    svc = MailboxService("redis://localhost:9999")
    count = asyncio.get_event_loop().run_until_complete(svc.get_unread_count("agent-1"))
    assert count == 0

"""Mailbox router — agent-to-agent messaging."""
__pattern__ = "Repository"

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from api.db.connection import get_db
from api.dependencies import get_settings
from api.config import OAKSettings
from api.models import MailboxMessageCreate, MailboxMessageResponse
from api.services.mailbox_service import MailboxService

router = APIRouter(prefix="/api/mailbox", tags=["mailbox"])


@router.post("", response_model=MailboxMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    body: MailboxMessageCreate,
    db: AsyncSession = Depends(get_db),
    settings: OAKSettings = Depends(get_settings),
) -> MailboxMessageResponse:
    """Send a message from one agent to another."""
    msg_id = uuid4()
    result = await db.execute(
        text("""
            INSERT INTO mailbox (id, problem_id, from_agent, to_agent, subject, body)
            VALUES (:id, :problem_id, :from_agent, :to_agent, :subject, :body)
            RETURNING id, problem_id, from_agent, to_agent, subject, body, read_at, created_at
        """),
        {
            "id": str(msg_id), "problem_id": str(body.problem_id),
            "from_agent": body.from_agent, "to_agent": body.to_agent,
            "subject": body.subject, "body": body.body,
        },
    )
    await db.commit()
    row = result.mappings().one()
    svc = MailboxService(str(settings.redis_url))
    await svc.publish(body.to_agent, str(msg_id), body.body)
    return MailboxMessageResponse(**dict(row))


@router.get("/{to_agent}/inbox", response_model=list[MailboxMessageResponse])
async def get_inbox(
    to_agent: str,
    problem_id: UUID | None = None,
    unread_only: bool = False,
    db: AsyncSession = Depends(get_db),
) -> list[MailboxMessageResponse]:
    """Return messages for an agent, optionally filtered by problem and read status."""
    filters = ["to_agent = :to_agent"]
    params: dict = {"to_agent": to_agent}
    if problem_id:
        filters.append("problem_id = :problem_id")
        params["problem_id"] = str(problem_id)
    if unread_only:
        filters.append("read_at IS NULL")
    where = " AND ".join(filters)
    result = await db.execute(
        text(f"SELECT id, problem_id, from_agent, to_agent, subject, body, read_at, created_at FROM mailbox WHERE {where} ORDER BY created_at DESC"),
        params,
    )
    return [MailboxMessageResponse(**dict(row)) for row in result.mappings()]


@router.patch("/{message_id}/read", response_model=MailboxMessageResponse)
async def mark_read(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> MailboxMessageResponse:
    """Mark a message as read."""
    result = await db.execute(
        text("""
            UPDATE mailbox SET read_at = NOW()
            WHERE id = :id AND read_at IS NULL
            RETURNING id, problem_id, from_agent, to_agent, subject, body, read_at, created_at
        """),
        {"id": str(message_id)},
    )
    await db.commit()
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Message not found or already read")
    return MailboxMessageResponse(**dict(row))

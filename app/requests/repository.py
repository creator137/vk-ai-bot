from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.requests.models import AcceptedRequestRecord


class AcceptedRequestRecordRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        user_id: int,
        peer_id: int,
        request_text: str,
        response_text: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
    ) -> AcceptedRequestRecord:
        record = AcceptedRequestRecord(
            user_id=user_id,
            peer_id=peer_id,
            request_text=request_text,
            response_text=response_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
        self._session.add(record)
        return record

    def list_recent_for_dialog(
        self,
        *,
        user_id: int,
        peer_id: int,
        limit: int,
    ) -> list[AcceptedRequestRecord]:
        statement = (
            select(AcceptedRequestRecord)
            .where(
                AcceptedRequestRecord.user_id == user_id,
                AcceptedRequestRecord.peer_id == peer_id,
            )
            .order_by(AcceptedRequestRecord.id.desc())
            .limit(limit)
        )
        records = list(self._session.scalars(statement))
        records.reverse()
        return records

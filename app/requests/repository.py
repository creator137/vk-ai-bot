from __future__ import annotations

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
    ) -> AcceptedRequestRecord:
        record = AcceptedRequestRecord(
            user_id=user_id,
            peer_id=peer_id,
            request_text=request_text,
            response_text=response_text,
        )
        self._session.add(record)
        return record

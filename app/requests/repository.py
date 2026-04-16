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

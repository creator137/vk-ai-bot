from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.requests.models import AcceptedRequestRecord
from app.requests.repository import AcceptedRequestRecordRepository


@dataclass(frozen=True, slots=True)
class AcceptedTextExchange:
    id: int
    user_id: int
    peer_id: int
    request_text: str
    response_text: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


class AcceptedRequestPersistenceService:
    def __init__(
        self,
        session: Session,
        repository: AcceptedRequestRecordRepository | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or AcceptedRequestRecordRepository(session)

    def record_text_exchange(
        self,
        *,
        user_id: int,
        peer_id: int,
        request_text: str,
        response_text: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
    ) -> AcceptedTextExchange:
        record = self._repository.create(
            user_id=user_id,
            peer_id=peer_id,
            request_text=request_text,
            response_text=response_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )
        self._session.commit()
        self._session.refresh(record)
        return _build_exchange(record)


def _build_exchange(record: AcceptedRequestRecord) -> AcceptedTextExchange:
    return AcceptedTextExchange(
        id=record.id,
        user_id=record.user_id,
        peer_id=record.peer_id,
        request_text=record.request_text,
        response_text=record.response_text,
        input_tokens=record.input_tokens,
        output_tokens=record.output_tokens,
        total_tokens=record.total_tokens,
    )

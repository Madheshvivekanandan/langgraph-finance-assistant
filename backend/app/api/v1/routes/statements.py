"""Statement upload and listing endpoints."""

from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, File, Query, Response, UploadFile, status

from app.api.deps import (
    StatementIngestionServiceDep,
    StatementQueryServiceDep,
    StatementReviewServiceDep,
)
from app.domain.category_decision import CategoryDecision
from app.domain.exceptions import StatementParseError
from app.schemas.statement_list_out import StatementListOut
from app.schemas.statement_out import StatementOut
from app.schemas.statement_review_decisions_in import StatementReviewDecisionsIn
from app.schemas.statement_review_out import StatementReviewOut

router = APIRouter(prefix="/statements", tags=["statements"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_STATEMENT_PAGE_SIZE = 100
DEFAULT_STATEMENT_PAGE_SIZE = 50
_FALLBACK_FILENAME = "statement.csv"


def _safe_filename(raw: str | None) -> str:
    """Reduce an uploaded filename to a bare basename.

    The value is only ever displayed, never used as a path, but stripping any
    directory component keeps it that way even if a later change forgets.
    """
    if not raw:
        return _FALLBACK_FILENAME
    return PurePosixPath(raw.replace("\\", "/")).name or _FALLBACK_FILENAME


@router.post(
    "",
    response_model=StatementOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a bank statement CSV",
    description=(
        "Parses the file into transactions and stores them. The response carries "
        "the resulting status: COMPLETED; FAILED with an error_message; or "
        "AWAITING_REVIEW, meaning some categorizations need a person's confirmation "
        "before storing - see GET/POST .../review."
    ),
)
def upload_statement(
    response: Response,
    service: StatementIngestionServiceDep,
    file: Annotated[UploadFile, File(description="Bank statement in CSV format")],
) -> StatementOut:
    """Accept a statement file and run it through the ingestion graph.

    Raises:
        StatementParseError: If the upload is empty or over the size limit.
    """
    # Read one byte past the cap so an oversized file is detected without
    # pulling the whole thing into memory.
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise StatementParseError("the uploaded file is empty")
    if len(content) > MAX_UPLOAD_BYTES:
        raise StatementParseError(
            f"the file is larger than the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit"
        )

    statement = service.ingest(filename=_safe_filename(file.filename), content=content)
    response.headers["Location"] = f"/api/v1/statements/{statement.id}"
    return StatementOut.model_validate(statement)


@router.get(
    "",
    response_model=StatementListOut,
    summary="List uploaded statements, newest first",
)
def list_statements(
    service: StatementQueryServiceDep,
    limit: Annotated[int, Query(ge=1, description="Rows to return; capped at 100")] = (
        DEFAULT_STATEMENT_PAGE_SIZE
    ),
) -> StatementListOut:
    """Return recent statements.

    Not cursor-paginated: this collection grows by one row per uploaded file, so
    a bounded limit is sufficient. Oversized requests are clamped, not rejected.
    """
    statements = service.list_recent(limit=min(limit, MAX_STATEMENT_PAGE_SIZE))
    return StatementListOut(items=[StatementOut.model_validate(item) for item in statements])


@router.get(
    "/{statement_id}/review",
    response_model=StatementReviewOut,
    summary="Get the rows a paused statement is asking a person to confirm",
    description=(
        "404 if the statement does not exist; 409 if it is not currently AWAITING_REVIEW."
    ),
)
def get_statement_review(
    statement_id: int,
    service: StatementReviewServiceDep,
) -> StatementReviewOut:
    """Return the pending review payload for one statement.

    Raises:
        StatementNotFoundError: If no such statement exists.
        StatementNotAwaitingReviewError: If it is not paused for review.
    """
    payload = service.get_pending(statement_id)
    return StatementReviewOut.model_validate(payload)


@router.post(
    "/{statement_id}/review",
    response_model=StatementOut,
    summary="Submit review decisions and resume a paused statement",
    description=(
        "Applies any corrections, approves the rest as suggested, and resumes the "
        "same run. Not idempotent by replacement (hence POST, not PUT): a second "
        "submission finds the statement already COMPLETED and gets 409."
    ),
)
def submit_statement_review(
    statement_id: int,
    body: StatementReviewDecisionsIn,
    service: StatementReviewServiceDep,
) -> StatementOut:
    """Resolve a statement's pending review and resume its run.

    Raises:
        StatementNotFoundError: If no such statement exists.
        StatementNotAwaitingReviewError: If it is not paused for review (this is
            what makes a second submission safe: it 409s instead of resuming twice).
        StatementReviewUnavailableError: If a decision names a row that is not
            actually pending.
    """
    decisions = [
        CategoryDecision(index=item.index, category=item.category) for item in body.decisions
    ]
    statement = service.submit(statement_id, decisions)
    return StatementOut.model_validate(statement)

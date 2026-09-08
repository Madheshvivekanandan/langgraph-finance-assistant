"""Statement upload and listing endpoints."""

from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, File, Query, Response, UploadFile, status

from app.api.deps import StatementIngestionServiceDep, StatementQueryServiceDep
from app.domain.exceptions import StatementParseError
from app.schemas.statement_list_out import StatementListOut
from app.schemas.statement_out import StatementOut

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
        "the resulting status: COMPLETED, or FAILED with an error_message."
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

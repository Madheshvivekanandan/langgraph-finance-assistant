"""RFC 9457 problem+json error body."""

from pydantic import BaseModel


class ProblemDetail(BaseModel):
    """Machine-readable error, served as application/problem+json.

    Clients branch on `code`, which is stable, rather than on `detail`, which is
    human-facing prose and may be reworded at any time.
    """

    type: str
    title: str
    status: int
    detail: str
    code: str

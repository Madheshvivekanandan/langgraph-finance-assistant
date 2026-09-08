"""Opaque page token for keyset pagination over transactions."""

import binascii
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from datetime import date

from app.domain.exceptions import InvalidPageTokenError


@dataclass(frozen=True, slots=True)
class TransactionCursor:
    """Points at the last row of a page, so the next page starts just after it.

    The token is opaque to clients but deliberately unsigned: this is a
    single-user application, so the cursor carries no tenant or authorization
    scope that could be tampered with. Signing becomes necessary the moment
    more than one person's data lives here.
    """

    transaction_date: date
    transaction_id: int

    def encode(self) -> str:
        """Render this cursor as a URL-safe token."""
        raw = f"{self.transaction_date.isoformat()}:{self.transaction_id}"
        return urlsafe_b64encode(raw.encode()).decode().rstrip("=")

    @classmethod
    def decode(cls, token: str) -> "TransactionCursor":
        """Parse a token produced by `encode`.

        Raises:
            InvalidPageTokenError: If the token is not a cursor this API issued.
        """
        try:
            padded = token + "=" * (-len(token) % 4)
            raw = urlsafe_b64decode(padded.encode()).decode()
            date_part, id_part = raw.rsplit(":", 1)
            return cls(
                transaction_date=date.fromisoformat(date_part),
                transaction_id=int(id_part),
            )
        except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
            raise InvalidPageTokenError("page_token is not a valid cursor") from exc

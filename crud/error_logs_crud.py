from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Session

from models import ErrorLog


class ErrorLogsCRUD:
    def __init__(self, session: Session):
        self.session = session

    def add_log(self, text: str) -> int:
        result = self.session.execute(
            sa.insert(ErrorLog)
            .values(
                {
                    ErrorLog.text: text,
                }
            )
            .returning(ErrorLog.id)
        )
        return result.scalar()

    def pop_log(self) -> Optional[ErrorLog]:
        q = sa.select(*ErrorLog.__table__.c).order_by(ErrorLog.id)
        row = self.session.execute(q).fetchone()
        if row is None:
            return None
        error_log = ErrorLog(**row)
        self.session.execute(sa.delete(ErrorLog).where(ErrorLog.id == error_log.id))
        return error_log


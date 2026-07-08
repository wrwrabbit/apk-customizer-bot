from typing import Optional

import sqlalchemy as sa

from crud.base_crud import BaseCRUD
from models import ErrorLog


class ErrorLogsCRUD(BaseCRUD):
    def add_log(self, text: str) -> int:
        with self._session_factory.begin() as session:
            log = ErrorLog(text=text)
            session.add(log)
            session.flush()
            return log.id

    def pop_log(self) -> Optional[ErrorLog]:
        with self._session_factory.begin() as session:
            q = sa.select(ErrorLog).order_by(ErrorLog.id)
            log = session.scalars(q).first()
            if log is not None:
                session.delete(log)
            return log

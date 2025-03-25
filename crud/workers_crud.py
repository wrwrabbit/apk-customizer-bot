from datetime import datetime
from typing import Iterator

import sqlalchemy as sa
from sqlalchemy.orm import Session

from models import Worker


class WorkersCRUD:
    def __init__(self, session: Session):
        self.session = session

    def create_worker(self, name: str, ip: str = None) -> int:
        result = self.session.execute(
            sa.insert(Worker)
            .values(
                {
                    Worker.name: name,
                    Worker.ip: ip,
                }
            )
            .returning(Worker.id)
        )
        return result.scalar()

    def remove_worker(self, worker_id: int):
        self.session.execute(sa.delete(Worker).where(Worker.id == worker_id))

    def update_worker_online(self, worker_id: int) -> int:
        result = self.session.execute(
            sa.update(Worker)
            .values(
                {
                    Worker.last_online_date: datetime.now(),
                }
            )
            .where(Worker.id == worker_id)
            .returning(Worker.id)
        )
        return result.scalar()

    def get_worker(self, worker_id: int) -> Worker:
        q = sa.select(*Worker.__table__.c).where(Worker.id == worker_id)
        row = self.session.execute(q).fetchone()
        return Worker(**row) if row else None

    def get_worker_by_name(self, name: str) -> Worker:
        q = sa.select(*Worker.__table__.c).where(Worker.name == name)
        row = self.session.execute(q).fetchone()
        return Worker(**row) if row else None

    def get_all_worker_names(self) -> Iterator[str]:
        q = sa.select(Worker.name)
        self.session.execute(q).fetchall()
        records = self.session.execute(q).fetchall()

        for record in records:
            yield record[0]


from datetime import datetime, timedelta
from typing import Optional

import sqlalchemy as sa

from crud.base_crud import BaseCRUD
from models import Worker


class WorkersCRUD(BaseCRUD):
    def create_worker(self, name: str, ip: str = None) -> int:
        with self._session_factory.begin() as session:
            worker = Worker(name=name, ip=ip)
            session.add(worker)
            session.flush()
            return worker.id

    def remove_worker(self, worker_id: int):
        with self._session_factory.begin() as session:
            session.execute(sa.delete(Worker).where(Worker.id == worker_id))

    def update_worker_online(self, worker_id: int) -> int:
        with self._session_factory.begin() as session:
            result = session.execute(
                sa.update(Worker)
                .values(last_online_date=datetime.now())
                .where(Worker.id == worker_id)
                .returning(Worker.id)
            )
            return result.scalar()

    def get_worker(self, worker_id: int) -> Optional[Worker]:
        with self._session_factory() as session:
            return session.get(Worker, worker_id)

    def get_worker_by_name(self, name: str) -> Optional[Worker]:
        q = sa.select(Worker).where(Worker.name == name)
        with self._session_factory() as session:
            return session.scalars(q).first()

    def get_all_worker_names(self) -> list[str]:
        q = sa.select(Worker.name)
        with self._session_factory() as session:
            return list(session.scalars(q))

    def get_all_workers(self) -> list[Worker]:
        q = sa.select(Worker)
        with self._session_factory() as session:
            return list(session.scalars(q))

    def get_workers_count(self) -> int:
        q = sa.select(sa.func.count(Worker.id))
        with self._session_factory() as session:
            return session.scalar(q)

    def get_online_workers_count(self, offline_after_sec: int) -> int:
        cutoff = datetime.now() - timedelta(seconds=offline_after_sec)
        q = sa.select(sa.func.count(Worker.id)).where(Worker.last_online_date >= cutoff)
        with self._session_factory() as session:
            return session.scalar(q)

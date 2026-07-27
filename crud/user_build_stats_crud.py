from datetime import datetime
from typing import Optional

import sqlalchemy as sa

from crud.base_crud import BaseCRUD
from models.user_order_stats import UserBuildStats


class UserBuildStatsCRUD(BaseCRUD):
    def add_user_build_stats(self, stats: UserBuildStats):
        with self._session_factory.begin() as session:
            session.execute(
                sa.insert(UserBuildStats)
                .values(
                    user_id_hash=stats.user_id_hash,
                    last_build_date=stats.last_build_date,
                    successful_build_count=stats.successful_build_count,
                    failed_build_count=stats.failed_build_count,
                )
            )

    def update_user_build_stats(self, stats: UserBuildStats):
        with self._session_factory.begin() as session:
            session.execute(
                sa.update(UserBuildStats)
                .values(
                    last_build_date=stats.last_build_date,
                    successful_build_count=stats.successful_build_count,
                    failed_build_count=stats.failed_build_count,
                )
                .where(UserBuildStats.user_id_hash == stats.user_id_hash)
            )

    def get_user_build_stats(self, user_id_hash: str) -> Optional[UserBuildStats]:
        with self._session_factory() as session:
            return session.get(UserBuildStats, user_id_hash)

    def remove_user_build_stats(self, user_id_hash: str):
        with self._session_factory.begin() as session:
            session.execute(sa.delete(UserBuildStats).where(UserBuildStats.user_id_hash == user_id_hash))

    def remove_old_user_build_stats(self, before_date: datetime):
        with self._session_factory.begin() as session:
            session.execute(sa.delete(UserBuildStats).where(UserBuildStats.last_build_date <= before_date))

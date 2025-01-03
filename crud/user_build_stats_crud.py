from datetime import datetime
from typing import Optional, Iterator

import sqlalchemy as sa
from sqlalchemy.orm import Session

from models.user_order_stats import UserBuildStats


class UserBuildStatsCRUD:
    def __init__(self, session: Session):
        self.session = session

    def add_user_build_stats(self, stats: UserBuildStats) -> int:
        self.session.execute(
            sa.insert(UserBuildStats)
            .values(
                {
                    UserBuildStats.user_id_hash: stats.user_id_hash,
                    UserBuildStats.last_build_date: stats.last_build_date,
                    UserBuildStats.successful_build_count: stats.successful_build_count,
                    UserBuildStats.failed_build_count: stats.failed_build_count,
                }
            )
        )

    def update_user_build_stats(self, stats: UserBuildStats):
        self.session.execute(
            sa.update(UserBuildStats)
            .values(
                {
                    UserBuildStats.last_build_date: stats.last_build_date,
                    UserBuildStats.successful_build_count: stats.successful_build_count,
                    UserBuildStats.failed_build_count: stats.failed_build_count,
                }
            )
            .where(UserBuildStats.user_id_hash == UserBuildStats.user_id_hash)
        )

    def get_user_build_stats(self, user_id_hash: str) -> Optional[UserBuildStats]:
        q = sa.select(*UserBuildStats.__table__.c).where(UserBuildStats.user_id_hash == user_id_hash)
        record = self.session.execute(q).fetchone()
        return UserBuildStats(**record) if record else None

    def remove_user_build_stats(self, user_id_hash: str):
        self.session.execute(sa.delete(UserBuildStats).where(UserBuildStats.user_id_hash == user_id_hash))

    def remove_old_user_build_stats(self, before_date: datetime):
        self.session.execute(sa.delete(UserBuildStats).where(UserBuildStats.last_build_date <= before_date))

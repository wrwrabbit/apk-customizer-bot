import sqlalchemy as sa

from .base import Base


class UserBuildStats(Base):
    __tablename__ = "user_build_stats"

    user_id_hash = sa.Column(sa.String, primary_key=True)
    last_build_date = sa.Column(sa.DateTime, nullable=False, index=True)
    successful_build_count = sa.Column(sa.Integer, nullable=False, server_default="0")
    failed_build_count = sa.Column(sa.Integer, nullable=False, server_default="0")

    @classmethod
    def create(cls, user_id_hash: str):
        stats = cls()
        stats.user_id_hash = user_id_hash
        stats.successful_build_count = 0
        stats.failed_build_count = 0
        return stats

import sqlalchemy as sa

from .base import Base


class Worker(Base):
    __tablename__ = "workers"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)

    record_created = sa.Column(
        sa.DateTime,
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP)"),
    )

    name = sa.Column(sa.String, nullable=False, unique=True, index=True)
    ip = sa.Column(sa.String, nullable=True)

    last_online_date = sa.Column(
        sa.DateTime,
        nullable=False,
        server_default='1970-01-01 00:00:00',
    )

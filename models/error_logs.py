import sqlalchemy as sa

from .base import Base


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)

    record_created = sa.Column(
        sa.DateTime,
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP)"),
    )

    text = sa.Column(sa.String, nullable=False)

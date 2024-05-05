import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import BYTEA

from schemas.order_status import OrderStatus
from .base import Base


class Order(Base):
    __tablename__ = "orders"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)

    user_id = sa.Column(sa.BIGINT, nullable=False)
    record_created = sa.Column(
        sa.DateTime,
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP)"),
    )

    app_name = sa.Column(sa.String)
    app_id = sa.Column(sa.String)
    app_icon = sa.Column(BYTEA)

    status = sa.Column(sa.String, server_default=OrderStatus.appname)

    build_attempts = sa.Column(sa.Integer, server_default="0")

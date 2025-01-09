import base64

import sqlalchemy as sa
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import BYTEA

from schemas.order_status import OrderStatus, get_next_status
from .base import Base


class Order(Base):
    __tablename__ = "orders"

    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)

    user_id = sa.Column(sa.BIGINT, nullable=False, index=True)
    record_created = sa.Column(
        sa.DateTime,
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP)"),
    )

    app_name = sa.Column(sa.String)
    app_id = sa.Column(sa.String)
    app_icon = sa.Column(BYTEA)
    app_version_code = sa.Column(sa.INT, server_default="100")
    app_version_name = sa.Column(sa.String, server_default="1.0.0")
    app_notification_icon = sa.Column(BYTEA)
    app_notification_color = sa.Column(sa.INT, server_default="0") # primary app color
    app_masked_passcode_screen = sa.Column(sa.String, server_default="calculator")
    app_notification_text = sa.Column(sa.String, server_default="Update Available!")
    permissions = sa.Column(sa.String, server_default="Update Available!")

    keystore = sa.Column(BYTEA, nullable=True)
    keystore_password_salt = sa.Column(sa.String, nullable=True)
    update_tag = sa.Column(sa.String, nullable=True)
    sources_only = sa.Column(sa.BOOLEAN, nullable=False, server_default="FALSE")
    priority = sa.Column(sa.INT, nullable=False, server_default="1") # The higher the number, the lower the priority

    status = sa.Column(sa.String, server_default=get_next_status(None))
    worker_id = sa.Column(
        sa.Integer,
        ForeignKey('workers.id', ondelete='SET NULL'),
        nullable=True,
        unique=True,
        index=True,
    )

    build_attempts = sa.Column(sa.Integer, server_default="0")

    def make_dict_for_worker(self) -> dict:
        fields = {'id', 'app_name', 'app_id', 'app_icon', 'app_version_code', 'app_version_name',
                  'app_notification_icon', 'app_notification_color', 'app_masked_passcode_screen',
                  'app_notification_text', 'permissions', 'keystore', 'keystore_password_salt', 'sources_only'}
        result = {k: v for k, v in self.__dict__.items() if k in fields}
        result['app_icon'] = base64.b64encode(result['app_icon']).decode("UTF-8")
        result['app_notification_icon'] = base64.b64encode(result['app_notification_icon']).decode("UTF-8")
        if result['keystore'] is not None:
            result['keystore'] = base64.b64encode(result['keystore']).decode("UTF-8")
        return result

    @staticmethod
    def create_order_from_dict(d: dict):
        order = Order(**d)
        order.app_icon = base64.b64decode(str(order.app_icon))
        order.app_notification_icon = base64.b64decode(str(order.app_notification_icon))
        if order.keystore is not None:
            order.keystore = base64.b64decode(str(order.keystore))
        return order

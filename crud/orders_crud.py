from typing import Iterator, Optional, Union

import sqlalchemy as sa
from sqlalchemy.orm import Session

from models import Order
from schemas.order_status import OrderStatus, get_next_status


class OrdersCRUD:
    def __init__(self, session: Session):
        self.session = session

    def create_order(self, user_id: int, priority: int) -> int:
        result = self.session.execute(
            sa.insert(Order)
            .values(
                {
                    Order.user_id: user_id,
                    Order.status: get_next_status(None),
                    Order.priority: priority,
                }
            )
            .returning(Order.id)
        )
        return result.scalar()

    def insert_configured_order(self, user_id: int, order: Order) -> Optional[Order]:
        result = self.session.execute(
            sa.insert(Order)
            .values(
                {
                    Order.user_id: user_id,
                    Order.app_icon: order.app_icon,
                    Order.app_name: order.app_name,
                    Order.app_id: order.app_id,
                    Order.app_version_code: order.app_version_code,
                    Order.app_version_name: order.app_version_name,
                    Order.app_notification_icon: order.app_notification_icon,
                    Order.app_notification_color: order.app_notification_color,
                    Order.app_masked_passcode_screen: order.app_masked_passcode_screen,
                    Order.app_notification_text: order.app_notification_text,
                    Order.permissions: order.permissions,
                    Order.keystore: order.keystore,
                    Order.keystore_password_salt: order.keystore_password_salt,
                    Order.update_tag: order.update_tag,
                    Order.priority: order.priority,

                    Order.status: OrderStatus.queued,
                }
            )
            .returning(*Order.__table__.c)
        )
        row = result.fetchone()
        return Order(**row) if row else None

    def update_app_id(
        self,
        order_id: int,
        app_id: str,
    ):
        result = self.session.execute(
            sa.update(Order)
            .values({Order.app_id: app_id})
            .where(Order.id == order_id)
            .returning(Order.id)
        )
        return result.scalar()

    def update_appname(
        self,
        order_id: int,
        appname: str,
    ) -> int:
        result = self.session.execute(
            sa.update(Order)
            .values({Order.app_name: appname})
            .where(Order.id == order_id)
            .returning(Order.id)
        )
        return result.scalar()

    def update_appicon(
        self,
        order_id: int,
        appicon: bytes,
    ) -> int:
        result = self.session.execute(
            sa.update(Order)
            .values({Order.app_icon: appicon})
            .where(Order.id == order_id)
            .returning(Order.id)
        )
        return result.scalar()

    def update_order(
        self,
        order: Order,
    ) -> int:
        result = self.session.execute(
            sa.update(Order)
            .values(
                {
                    Order.app_icon: order.app_icon,
                    Order.app_name: order.app_name,
                    Order.app_id: order.app_id,
                    Order.app_version_code: order.app_version_code,
                    Order.app_version_name: order.app_version_name,
                    Order.app_notification_icon: order.app_notification_icon,
                    Order.app_notification_color: order.app_notification_color,
                    Order.app_masked_passcode_screen: order.app_masked_passcode_screen,
                    Order.app_notification_text: order.app_notification_text,
                    Order.permissions: order.permissions,
                    Order.keystore: order.keystore,
                    Order.keystore_password_salt: order.keystore_password_salt,
                    Order.status: order.status,
                    Order.worker_id: order.worker_id,
                    Order.build_attempts: order.build_attempts,
                    Order.record_created: order.record_created,
                    Order.sources_only: order.sources_only,
                    Order.priority: order.priority,
                }
            )
            .where(Order.id == order.id)
            .returning(Order.id)
        )
        return result.scalar()

    def update_order_status(self, order: Order, status: OrderStatus):
        order.status = status
        result = self.session.execute(
            sa.update(Order)
            .values(
                {
                    "status": status,
                }
            )
            .where(Order.id == order.id)
        )

    def update_order_build_attempts(self, order_id: int, build_attempts: int) -> int:
        result = self.session.execute(
            sa.update(Order)
            .values(
                {
                    Order.build_attempts: build_attempts,
                }
            )
            .where(Order.id == order_id)
            .returning(Order.id)
        )
        return result.scalar()

    def remove_order(self, order_id: int):
        self.session.execute(sa.delete(Order).where(Order.id == order_id))

    def get_order(self, order_id: int) -> Optional[Order]:
        q = sa.select(*Order.__table__.c).where(Order.id == order_id)

        record = self.session.execute(q).fetchone()
        return Order(**record) if record else None

    def get_user_order(self, user_id: int, status: OrderStatus = None) -> Optional[Order]:
        q = sa.select(*Order.__table__.c).where(Order.user_id == user_id)
        if status:
            q = q.where(Order.status == status)
        q = q.order_by(Order.record_created.desc())

        record = self.session.execute(q).fetchone()
        return Order(**record) if record else None

    def get_orders_by_status(self, status: OrderStatus) -> Iterator[Order]:
        q = sa.select(*Order.__table__.c)
        if status:
            q = q.where(Order.status == status)
        q = q.order_by(Order.record_created)

        records = self.session.execute(q).fetchall()

        for record in records:
            yield Order(**record)

    def get_order_for_build(self) -> Optional[Order]:
        q = (sa.select(*Order.__table__.c)
             .where((Order.status == OrderStatus.queued) & (Order.sources_only == False))
             .order_by(Order.record_created))

        row = self.session.execute(q).fetchone()

        return Order(**row) if row else None

    def get_sources_only_order(self) -> Optional[Order]:
        q = (sa.select(*Order.__table__.c)
             .where((Order.status == OrderStatus.get_sources_queued) & (Order.sources_only == True))
             .order_by(Order.priority, Order.record_created))

        row = self.session.execute(q).fetchone()

        return Order(**row) if row else None

    def get_worker_order(self, worker_id: int) -> Optional[Order]:
        q = (sa.select(*Order.__table__.c)
             .where(Order.worker_id == worker_id))
        row = self.session.execute(q).fetchone()
        return Order(**row) if row else None

    def get_order_queue_position(self, order: Order) -> int:
        q = sa.select(sa.func.count(Order.id)).where(
            (Order.status == OrderStatus.queued) &
            ((Order.priority < order.priority) | ((Order.priority == order.priority) & (Order.record_created < order.record_created)))
        )

        result = self.session.execute(q).scalar() + 1
        return result

    def order_for_user_exists(self, user_id: int) -> bool:
        q = (sa.select(sa.func.count(Order.id))
             .where(Order.user_id == user_id))
        return self.session.execute(q).scalar() > 0

    def order_for_user_not_exists(self, user_id: int) -> bool:
        return not self.order_for_user_exists(user_id)

    def get_orders_count(self) -> int:
        q = sa.select(sa.func.count(Order.id))
        return self.session.execute(q).scalar()

    def get_count_of_orders_by_status(self, status: Union[list, OrderStatus]) -> int:
        q = sa.select([sa.func.count()]).select_from(Order.__table__)
        if status:
            if isinstance(status, list):
                q = q.where(Order.status.in_(status))
            elif isinstance(status, OrderStatus):
                q = q.where(Order.status == status)
        return self.session.execute(q).scalar()

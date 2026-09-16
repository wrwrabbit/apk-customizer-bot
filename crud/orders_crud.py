from datetime import datetime, timedelta
from typing import Optional, Union

import pytz
import sqlalchemy as sa

import config
from crud.base_crud import BaseCRUD
from models import Order
from schemas.order_status import OrderStatus, get_next_status


class OrdersCRUD(BaseCRUD):
    def create_order(self, user_id: int, priority: int) -> int:
        with self._session_factory.begin() as session:
            order = Order(
                user_id=user_id,
                status=get_next_status(None),
                priority=priority,
            )
            session.add(order)
            session.flush()
            return order.id

    def insert_configured_order(self, user_id: int, order: Order) -> Order:
        record_created = datetime.now().astimezone(pytz.utc) + timedelta(seconds=config.DELAY_BEFORE_UPDATE_ORDER_BUILD_SEC)
        new_order = Order(
            user_id=user_id,
            record_created=record_created,
            app_icon=order.app_icon,
            app_name=order.app_name,
            app_id=order.app_id,
            app_version_code=order.app_version_code,
            app_version_name=order.app_version_name,
            app_notification_icon=order.app_notification_icon,
            app_notification_color=order.app_notification_color,
            app_masked_passcode_screen=order.app_masked_passcode_screen,
            app_notification_text=order.app_notification_text,
            permissions=order.permissions,
            keystore=order.keystore,
            keystore_password_salt=order.keystore_password_salt,
            update_tag=order.update_tag,
            priority=order.priority,

            status=OrderStatus.update_queued,
        )
        with self._session_factory.begin() as session:
            session.add(new_order)
            session.flush()
            session.refresh(new_order)
        return new_order

    def update_app_id(
        self,
        order_id: int,
        app_id: str,
    ):
        with self._session_factory.begin() as session:
            result = session.execute(
                sa.update(Order)
                .values(app_id=app_id)
                .where(Order.id == order_id)
                .returning(Order.id)
            )
            return result.scalar()

    def update_appname(
        self,
        order_id: int,
        appname: str,
    ) -> int:
        with self._session_factory.begin() as session:
            result = session.execute(
                sa.update(Order)
                .values(app_name=appname)
                .where(Order.id == order_id)
                .returning(Order.id)
            )
            return result.scalar()

    def update_appicon(
        self,
        order_id: int,
        appicon: bytes,
    ) -> int:
        with self._session_factory.begin() as session:
            result = session.execute(
                sa.update(Order)
                .values(app_icon=appicon)
                .where(Order.id == order_id)
                .returning(Order.id)
            )
            return result.scalar()

    def update_order(
        self,
        order: Order,
    ) -> int:
        with self._session_factory.begin() as session:
            result = session.execute(
                sa.update(Order)
                .values(
                    app_icon=order.app_icon,
                    app_name=order.app_name,
                    app_id=order.app_id,
                    app_version_code=order.app_version_code,
                    app_version_name=order.app_version_name,
                    app_notification_icon=order.app_notification_icon,
                    app_notification_color=order.app_notification_color,
                    app_masked_passcode_screen=order.app_masked_passcode_screen,
                    app_notification_text=order.app_notification_text,
                    permissions=order.permissions,
                    keystore=order.keystore,
                    keystore_password_salt=order.keystore_password_salt,
                    status=order.status,
                    worker_id=order.worker_id,
                    build_attempts=order.build_attempts,
                    record_created=order.record_created,
                    sources_only=order.sources_only,
                    priority=order.priority,
                )
                .where(Order.id == order.id)
                .returning(Order.id)
            )
            return result.scalar()

    def update_order_status(self, order: Order, status: OrderStatus):
        order.status = status
        with self._session_factory.begin() as session:
            session.execute(
                sa.update(Order)
                .values(status=status)
                .where(Order.id == order.id)
            )

    def update_order_build_attempts(self, order_id: int, build_attempts: int) -> int:
        with self._session_factory.begin() as session:
            result = session.execute(
                sa.update(Order)
                .values(build_attempts=build_attempts)
                .where(Order.id == order_id)
                .returning(Order.id)
            )
            return result.scalar()

    def remove_order(self, order_id: int):
        with self._session_factory.begin() as session:
            session.execute(sa.delete(Order).where(Order.id == order_id))

    def get_order(self, order_id: int) -> Optional[Order]:
        with self._session_factory() as session:
            return session.get(Order, order_id)

    def get_user_order(self, user_id: int, status: OrderStatus = None) -> Optional[Order]:
        q = sa.select(Order).where(Order.user_id == user_id)
        if status:
            q = q.where(Order.status == status)
        q = q.order_by(Order.record_created.desc())

        with self._session_factory() as session:
            return session.scalars(q).first()

    def get_orders_by_status(self, status: OrderStatus) -> list[Order]:
        q = sa.select(Order)
        if status:
            q = q.where(Order.status == status)
        q = q.order_by(Order.record_created)

        with self._session_factory() as session:
            return list(session.scalars(q))

    def get_order_for_build(self) -> Optional[Order]:
        q = (sa.select(Order)
             .where(((Order.status == OrderStatus.queued) | (Order.status == OrderStatus.update_queued)) & (Order.sources_only == False))
             .where(Order.record_created < datetime.now().astimezone(pytz.utc))
             .order_by(Order.record_created))

        with self._session_factory() as session:
            return session.scalars(q).first()

    def get_sources_only_order(self) -> Optional[Order]:
        q = (sa.select(Order)
             .where((Order.status == OrderStatus.get_sources_queued) & (Order.sources_only == True))
             .order_by(Order.priority, Order.record_created))

        with self._session_factory() as session:
            return session.scalars(q).first()

    def get_worker_order(self, worker_id: int) -> Optional[Order]:
        q = (sa.select(Order)
             .where(Order.worker_id == worker_id))
        with self._session_factory() as session:
            return session.scalars(q).first()

    def get_order_queue_position(self, order: Order) -> int:
        q = sa.select(sa.func.count(Order.id)).where(
            (Order.status == OrderStatus.queued) &
            ((Order.priority < order.priority) | ((Order.priority == order.priority) & (Order.record_created < order.record_created)))
        )

        with self._session_factory() as session:
            return session.scalar(q) + 1

    def order_for_user_exists(self, user_id: int) -> bool:
        q = (sa.select(sa.func.count(Order.id))
             .where(Order.user_id == user_id))
        with self._session_factory() as session:
            return session.scalar(q) > 0

    def order_for_user_not_exists(self, user_id: int) -> bool:
        return not self.order_for_user_exists(user_id)

    def get_orders_count(self) -> int:
        q = sa.select(sa.func.count(Order.id))
        with self._session_factory() as session:
            return session.scalar(q)

    def get_count_of_orders_by_status(self, status: Union[list, OrderStatus]) -> int:
        q = sa.select(sa.func.count()).select_from(Order)
        if status:
            if isinstance(status, list):
                q = q.where(Order.status.in_(status))
            elif isinstance(status, OrderStatus):
                q = q.where(Order.status == status)
        with self._session_factory() as session:
            return session.scalar(q)

    def get_oldest_queued_order_date(self) -> Optional[datetime]:
        q = sa.select(sa.func.min(Order.record_created)).where(
            Order.status.in_([OrderStatus.queued, OrderStatus.update_queued])
        )
        with self._session_factory() as session:
            return session.scalar(q)

    def get_order_ids_by_status(self, status: list) -> list[int]:
        q = sa.select(Order.id).where(Order.status.in_(status))
        with self._session_factory() as session:
            return list(session.scalars(q))

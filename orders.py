import os
import subprocess
from typing import Iterator, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Session

from models import Order
from schemas.order_status import OrderStatus


class OrdersCRUD:
    def __init__(self, session: Session):
        self.session = session

    def create_order(self, user_id: int) -> int:
        result = self.session.execute(
            sa.insert(Order)
            .values(
                {
                    Order.user_id: user_id,
                }
            )
            .returning(Order.id)
        )
        return result.scalar()

    def update_appid(
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
        appicon: str,
    ) -> int:
        result = self.session.execute(
            sa.update(Order)
            .values({Order.app_icon: appicon})
            .where(Order.id == order_id)
            .returning(Order.id)
        )
        return result.scalar()

    def update(
        self,
        order_id: int,
        order: Order,
    ) -> int:
        result = self.session.execute(
            sa.update(Order)
            .values(
                {
                    Order.app_icon: order.app_icon,
                    Order.app_name: order.app_name,
                    Order.app_id: order.app_id,
                    Order.status: order.status,
                }
            )
            .where(Order.id == order_id)
            .returning(Order.id)
        )
        return result.scalar()

    def update_order_status(self, order_id: int, status: OrderStatus) -> int:
        result = self.session.execute(
            sa.update(Order)
            .values(
                {
                    "status": status,
                }
            )
            .where(Order.id == order_id)
            .returning(Order.id)
        )
        return result.scalar()

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

    def get_user_orders(self, user_id: int, status: OrderStatus = None):
        q = sa.select(*Order.__table__.c).where(Order.user_id == user_id)
        if status:
            q = q.where(Order.status == status)
        else:
            q = q.where(Order.status.notin_([OrderStatus.canceled, OrderStatus.completed]))
        q = q.order_by(Order.record_created.desc())

        records = self.session.execute(q).fetchall()

        for record in records:
            yield Order(**record)

    def get_orders(self, status: OrderStatus = None) -> Iterator[Order]:
        q = sa.select(*Order.__table__.c)
        if status:
            q = q.where(Order.status == status)
        else:
            q = q.where(Order.status.notin_([OrderStatus.canceled, OrderStatus.completed]))
        q = q.order_by(Order.record_created)

        records = self.session.execute(q).fetchall()

        for record in records:
            yield Order(**record)


class OrdersQueue:
    def __init__(self, session: Session):
        self.session = session
        self.orders = OrdersCRUD(session)

    def get_users(self):
        users = (
            self.session.execute(
                sa.select(Order.user_id).where(
                    Order.status.notin_([OrderStatus.canceled, OrderStatus.completed])
                )
            )
            .scalars()
            .fetchall()
        )

        for user in users:
            yield user

    def record_user(self, userid: int) -> int:
        result = self.session.execute(
            sa.insert(Order)
            .values(
                {
                    Order.user_id: userid,
                    Order.status: OrderStatus.appname,
                }
            )
            .returning(Order.id)
        )
        return result.scalar()

    def update_order(self, order: Order) -> int:
        return self.orders.update(order.id, order)

    def get_order(self, user_id: int) -> Optional[Order]:
        for i in self.orders.get_user_orders(user_id):
            return i

    def get_orders(self, status: OrderStatus = None):
        return self.orders.get_orders(status)


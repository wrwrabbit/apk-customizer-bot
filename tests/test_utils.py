from bot.bot import on_order_status
from crud.orders_crud import OrdersCRUD
from schemas.order_status import OrderStatus


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id


class FakeMessage:
    def __init__(self, user_id):
        self.from_user = FakeUser(user_id)


def test_on_order_status(session):
    orders = OrdersCRUD(session)
    fun = lambda message: on_order_status(orders, [OrderStatus.queued], message)

    user_id = orders.create_order(1984)
    user_message = FakeMessage(user_id)

    result = fun(user_message)
    assert result is False

    orders.create_order(user_id)

    result = fun(user_message)
    assert result is True

    order = orders.get_user_order(1984)
    orders.update_order_status(order, OrderStatus.building)

    result = fun(user_message)
    assert result is False

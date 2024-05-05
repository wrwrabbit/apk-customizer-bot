from bot.bot import on_order_status
from orders import OrdersQueue
from schemas.order_status import OrderStatus


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id


class FakeMessage:
    def __init__(self, user_id):
        self.from_user = FakeUser(user_id)


def test_on_order_status(session):
    queue = OrdersQueue(session)
    fun = lambda message: on_order_status(queue, OrderStatus.queued, message)

    user_id = queue.record_user(1984)
    user_message = FakeMessage(user_id)

    result = fun(user_message)
    assert result is False

    order_id = queue.orders.create_order(user_id)

    result = fun(user_message)
    assert result is True

    queue.orders.update_order_status(order_id, OrderStatus.building)

    result = fun(user_message)
    assert result is False

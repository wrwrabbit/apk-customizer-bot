from orders import OrdersQueue
from schemas.order_status import OrderStatus


def test_create_order(session):
    queue = OrdersQueue(session)
    user_id = int(1e12)
    order_id = queue.record_user(user_id)
    queue.orders.update_appname(order_id, "TestApp")
    queue.orders.update_appid(order_id, "TestApp")

    orders = list(queue.orders.get_user_orders(user_id))
    assert len(orders) == 1
    assert orders[0].app_name == "TestApp"
    assert orders[0].app_id == "TestApp"
    assert orders[0].status == OrderStatus.appname

    orders = list(queue.orders.get_orders())

    assert len(orders) == 1
    assert orders[0].status == OrderStatus.appname

    orders = list(queue.orders.get_orders(OrderStatus.appname))

    assert len(orders) == 1
    assert orders[0].status == OrderStatus.appname

    orders = list(queue.orders.get_orders(OrderStatus.built))

    assert len(orders) == 0

    queue.orders.update_order_status(order_id, OrderStatus.built)

    orders = list(queue.orders.get_orders(OrderStatus.built))
    assert len(orders) == 1
    assert orders[0].status == OrderStatus.built

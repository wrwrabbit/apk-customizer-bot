from crud.orders_crud import OrdersCRUD
from schemas.order_status import OrderStatus


def test_create_order(session):
    orders = OrdersCRUD(session)
    user_id = int(1e12)
    order_id = orders.create_order(user_id)
    orders.update_appname(order_id, "TestApp")
    orders.update_app_id(order_id, "TestApp")

    order_list = list(orders.get_orders_by_status(OrderStatus.app_name))

    assert len(order_list) == 1
    assert order_list[0].status == OrderStatus.app_name

    order_list = list(orders.get_orders_by_status(OrderStatus.built))

    assert len(order_list) == 0

    order = orders.get_user_order(user_id)
    orders.update_order_status(order, OrderStatus.built)

    order_list = list(orders.get_orders_by_status(OrderStatus.built))
    assert len(order_list) == 1
    assert order_list[0].status == OrderStatus.built

import time
from datetime import datetime, timedelta

import pytz

import config
from crud.user_build_stats_crud import UserBuildStatsCRUD
from db import engine
from crud.orders_crud import OrdersCRUD
from schemas.order_status import OrderStatus, get_next_status
from crud.workers_crud import WorkersCRUD


def fail_stuck_builds(orders: OrdersCRUD):
    # If the bot was stopped during building, the order may get stuck.
    # It's status will be one of STATUSES_BUILDING.
    # So after restart we must reset status to build the order or send the apk again.
    stuck_statuses = [
        OrderStatus.build_started,
        OrderStatus.building,
        OrderStatus.sending_apk,
    ]
    for status in stuck_statuses:
        for order in orders.get_orders_by_status(status):
            print(f"Cleaning building status for order {order.id}")
            orders.update_order_status(order.id, get_next_status(order.status, "repeat"))


def reset_build_status_for_offline_workers(orders: OrdersCRUD):
    for order in orders.get_orders_by_status(OrderStatus.building):
        workers = WorkersCRUD(orders.session)
        worker = workers.get_worker(order.worker_id)
        if datetime.now() - worker.last_online_date > timedelta(seconds=config.CONSIDER_WORKER_OFFLINE_AFTER_SEC):
            print(f"Worker {worker.id} is offline for order {order.id}", datetime.now() - worker.last_online_date)
            order.status = get_next_status(order.status, "repeat")
            order.worker_id = None
            orders.update_order(order)


def delete_old_user_build_stats(user_build_stats_crud: UserBuildStatsCRUD):
    before_date = (datetime.now() - timedelta(seconds=config.DELETE_USER_BUILD_STATS_AFTER_SEC)).astimezone(pytz.utc)
    user_build_stats_crud.remove_old_user_build_stats(before_date)


def main():
    print("Clean process started")
    orders = OrdersCRUD(engine)
    user_build_stats_crud = UserBuildStatsCRUD(engine)
    fail_stuck_builds(orders)
    while True:
        reset_build_status_for_offline_workers(orders)
        delete_old_user_build_stats(user_build_stats_crud)
        time.sleep(1)


if __name__ == "__main__":
    main()

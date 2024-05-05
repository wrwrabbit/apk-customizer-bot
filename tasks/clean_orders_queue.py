import os
import shutil
import time

import config
from db import engine
from orders import OrdersQueue
from schemas.order_status import OrderStatus, STATUSES_IN_PROGRESS


def fail_stucked_builds(db: OrdersQueue):
    # If the bot was stopped during assembly, the order may get stuck.
    # It's status will be one of STATUSES_IN_PROGRESS. 
    # So after restart we must set 'failed' status to allow users restart their builds.
    for status in STATUSES_IN_PROGRESS:
        for order in db.get_orders(status):
            print(f"Cleaning building status for order {order.id}")
            db.orders.update_order_status(order.id, OrderStatus.failed)


def clean_orders_queue(db: OrdersQueue):
    for status in [OrderStatus.canceled, OrderStatus.completed]:
        for order in db.get_orders(status):
            print(f"Cleaning data for {order.status} order {order.id}")

            build_dir = os.path.join(config.TMP_DIR, str(order.id))
            if os.path.isdir(build_dir):
                print(f"Removing directory {build_dir}")
                shutil.rmtree(build_dir)

            db.orders.remove_order(order.id)


def main():
    print("Clean process started")
    db = OrdersQueue(engine)
    fail_stucked_builds(db)
    while True:
        clean_orders_queue(db)
        time.sleep(1)


if __name__ == "__main__":
    main()

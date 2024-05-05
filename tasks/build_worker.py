import os
import subprocess
import sys
import time
import traceback

import config
from db import engine
from models import Order
from orders import OrdersQueue
from schemas.order_status import OrderStatus
from configure_build import update_sources


def build_task(order: Order):
    print(f"Starting build for order #{order.id}")

    queue = OrdersQueue(engine)

    queue.orders.update_order_status(order.id, OrderStatus.build_started)

    scripts_dir = os.path.abspath(config.BUILD_SCRIPT)
    data_dir = os.path.abspath(config.DATA_DIR)
    order_dir = os.path.join(config.TMP_DIR, str(order.id))
    if not os.path.isdir(order_dir):
        os.mkdir(order_dir)

    if not config.MOCK_BUILD:
        subprocess.run(
            [
                "/bin/sh",
                os.path.join(scripts_dir, "copy_repo.sh"),
                os.path.abspath(order_dir)
            ],
            stdout=sys.stdout,
            stderr=sys.stdout,
            cwd=data_dir,
            encoding="utf-8",
        )
        iconfile = os.path.join(order_dir, f"{order.app_id}.icon")
        with open(iconfile, "wb") as f:
            f.write(order.app_icon)

        update_sources(order_dir, order.app_id, order.app_name, iconfile)

    if config.MOCK_BUILD:
        build_sh = "mock_build.sh"
    else:
        build_sh = "build.sh"

    is_error = "error" in order.app_id and order.build_attempts == 0
    subprocess.run(
        [
            "/bin/sh",
            os.path.join(scripts_dir, build_sh),
            str(order.id),
            str(is_error)
        ],
        stdout=sys.stdout,
        stderr=sys.stdout,
        cwd=order_dir,
        encoding="utf-8",
    )
    queue.orders.update_order_build_attempts(order.id, order.build_attempts + 1)

    if os.path.isfile(os.path.join(order_dir, "done")):
        queue.orders.update_order_status(order.id, OrderStatus.built)
        print(f"Build for order #{order.id} successful")
    else:
        print(f"During build the following exception occurred:")
        traceback.print_exc()
        queue.orders.update_order_status(order.id, OrderStatus.failed)
        print(f"Build for order #{order.id} failed")


def main():
    db = OrdersQueue(engine)
    print(f"Build daemon started")
    while True:
        for order in db.get_orders(status=OrderStatus.queued):
            build_task(order)
        time.sleep(1)


if __name__ == "__main__":
    main()

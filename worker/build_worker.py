import os
import signal
import sys
import threading
import time
import traceback
from typing import Optional

import config
from models import Order
from worker.application_builder import ApplicationBuilder, application_builder_critical_lock
from worker.worker_controller_api import WorkerControllerApi

global_current_order: Optional[Order] = None
global_current_order_lock = threading.Lock()

controller_api = WorkerControllerApi(config.WORKER_CONTROLLER_HOST)
graceful_shutdown = False


def signal_handler(sig, frame):
    if sig == signal.SIGTERM:
        print('SIGTERM received. The worker will stop as soon as possible.')
        # Wait until critical operations are completed before terminating the worker.
        with application_builder_critical_lock:
            sys.exit(0)
    elif sig == signal.SIGINT:
        print('SIGINT received. The worker will stop after finishing current build if it builds any app.')
        global graceful_shutdown
        graceful_shutdown = True


def process_current_order():
    global global_current_order
    with global_current_order_lock:
        if global_current_order is None:
            print("Current order is None")
            return
        current_order = global_current_order

    ApplicationBuilder(controller_api, current_order).build()

    with global_current_order_lock:
        global_current_order = None


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    global global_current_order
    print("Build daemon started")
    try:
        os.makedirs(config.TMP_DIR, exist_ok=True)
        while True:
            controller_api.send_keep_alive()
            with global_current_order_lock:
                if global_current_order is None:
                    if graceful_shutdown: # Shutdown the worker only when current order is None
                        sys.exit(0)
                    global_current_order = controller_api.receive_order()
                    thread = threading.Thread(target=process_current_order)
                    thread.start()
            time.sleep(config.WORKER_CHECK_INTERVAL_SEC)
    except Exception as e:
        print("During main the following exception occurred:", e)
        traceback.print_exc()


if __name__ == "__main__":
    main()

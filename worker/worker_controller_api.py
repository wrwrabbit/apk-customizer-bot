import os
import traceback
from typing import Optional

import requests
from requests import Response
from requests.adapters import HTTPAdapter, Retry

import config
from models import Order
import utils


class WorkerControllerApi:
    def __init__(self, host: str):
        self.http_session = requests.Session()
        self.http_session.headers.update({"Authorization": "Bearer " + config.WORKER_JWT})
        self.http_session.verify = "worker/cert.pem"
        # on error retry reconnect after 0 sec, 2 sec, 4 sec ... 60 sec
        retries = Retry(total=100, backoff_factor=1, backoff_max=60, status_forcelist=[ 502, 503, 504 ])
        self.http_session.mount('https://', HTTPAdapter(max_retries=retries))
        self.host = host

    def make_url(self, path: str) -> str:
        return "https://" + self.host + path

    def log_response(self, prefix: str, response: Response):
        if 200 <= response.status_code < 300:
            print(prefix, response.status_code)
        else:
            print(prefix, response.status_code, response.text)

    def send_keep_alive(self):
        try:
            response = self.http_session.get(self.make_url("/keep-alive"))
            self.log_response("Keep alive:", response)
        except Exception as e:
            print(f"During send_keep_alive the following exception occurred:", e)
            traceback.print_exc()

    def receive_order(self) -> Optional[Order]:
        try:
            response = self.http_session.get(self.make_url("/receive-order"))
            self.log_response(f"Receive order:", response)
            if response.status_code == 400:
                response = self.http_session.get(self.make_url("/get-current-order"))
                self.log_response(f"Get current order:", response)
            values = response.json()
            return Order.create_order_from_dict(values) if values is not None else None
        except Exception as e:
            print(f"During send_keep_alive the following exception occurred:", e)
            traceback.print_exc()
            return None

    def send_order_completed(self, order: Order):
        filepath = os.path.join(
            utils.make_order_building_dir_path(order.id),
            "Partisan-Telegram-Android",
            "TMessagesProj",
            "build",
            "outputs",
            "apk",
            "afat",
            "standalone",
            "app.apk",
        )
        with open(filepath, "rb") as file:
            response = self.http_session.post(self.make_url("/order-completed"), files={"file": file})
            self.log_response(f"Order completed:", response)

    def send_order_failed(self, error_text = None):
        json = {"error_text": error_text} if error_text else None
        response = self.http_session.post(self.make_url("/order-failed"), json=json)
        self.log_response(f"Order failed:", response)

import os
from datetime import datetime
from functools import wraps
from typing import Callable

import pytz
from argon2 import PasswordHasher
from flask import Flask
from flask import jsonify
from flask import request
from flask_jwt_extended import JWTManager
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required

import config
import utils
from crud.error_logs_crud import ErrorLogsCRUD
from crud.user_build_stats_crud import UserBuildStatsCRUD
from db import engine
from models import Worker, UserBuildStats
from crud.orders_crud import OrdersCRUD
from schemas.order_status import OrderStatus, get_next_status
from crud.workers_crud import WorkersCRUD

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = config.JWT_SECRET_KEY
jwt = JWTManager(app)
orders = OrdersCRUD(engine)
workers = WorkersCRUD(engine)
error_logs = ErrorLogsCRUD(engine)
user_build_stats_crud = UserBuildStatsCRUD(engine)

password_hasher = PasswordHasher()


def check_worker_id(fun: Callable):
    @wraps(fun)
    def wrapper():
        worker_id = get_jwt_identity()
        worker = workers.get_worker(worker_id) if isinstance(worker_id, int) else None
        if not worker or (worker.ip and worker.ip != request.remote_addr):
            return jsonify(msg="Signature verification failed"), 422
        return fun(worker)

    return wrapper


@app.route("/keep-alive", methods=["GET"])
@jwt_required()
@check_worker_id
def keep_alive(worker: Worker):
    workers.update_worker_online(worker.id)
    return "", 204


@app.route("/receive-order", methods=["GET"])
@jwt_required()
@check_worker_id
def receive_order(worker: Worker):
    previous_order = orders.get_worker_order(worker.id)
    if previous_order is not None:
        return jsonify({"error": "Build has already started"}), 400
    new_order = next(orders.get_orders_by_status(status=OrderStatus.queued), None)
    if new_order is None:
        return jsonify(new_order), 200
    new_order.status = get_next_status(new_order.status)
    new_order.worker_id = worker.id
    orders.update_order(new_order)
    workers.update_worker_online(worker.id)
    return jsonify(new_order.make_dict_for_worker()), 200


@app.route("/get-current-order", methods=["GET"])
@jwt_required()
@check_worker_id
def get_current_order(worker: Worker):
    previous_order = orders.get_worker_order(worker.id)
    if previous_order is None:
        return jsonify({"error": "Build did not start"}), 400
    return jsonify(previous_order.make_dict_for_worker()), 200


@app.route("/order-completed", methods=["POST"])
@jwt_required()
@check_worker_id
def order_completed(worker: Worker):
    previous_order = orders.get_worker_order(worker.id)
    if previous_order is None:
        return jsonify({"error": "Build did not start"}), 400
    if 'file' not in request.files:
        return jsonify({"error": "No file sent"}), 400
    apk_dir = utils.make_order_apk_dir_path(previous_order.id)
    os.makedirs(apk_dir, exist_ok=True)
    filepath = os.path.join(
        apk_dir,
        "app.apk",
    )
    file = request.files['file']
    file.save(filepath)
    previous_order.build_attempts += 1
    previous_order.status = get_next_status(previous_order.status, "success")
    previous_order.worker_id = None
    orders.update_order(previous_order)
    increase_user_build_stats(previous_order.user_id, successful=True)
    return "", 204


@app.route("/order-failed", methods=["POST"])
@jwt_required()
@check_worker_id
def order_failed(worker: Worker):
    previous_order = orders.get_worker_order(worker.id)
    if previous_order is None:
        return jsonify({"error": "Build did not start"}), 400
    previous_order.build_attempts += 1
    previous_order.status = get_next_status(previous_order.status, "fail")
    previous_order.worker_id = None
    orders.update_order(previous_order)
    if request.json is not None and "error_text" in request.json:
        print("###ERROR_TEXT###")
        print(request.json["error_text"])
        error_logs.add_log(request.json["error_text"])
    increase_user_build_stats(previous_order.user_id, successful=False)
    return "", 204


def increase_user_build_stats(user_id: int, successful: bool):
    user_id_hash = password_hasher.hash(str(user_id), salt=config.USER_ID_HASH_SALT.encode())
    old_stats = user_build_stats_crud.get_user_build_stats(user_id_hash)
    new_stats = old_stats if old_stats else UserBuildStats.create(user_id_hash)
    new_stats.last_build_date = datetime.now().astimezone(pytz.utc)
    if successful:
        new_stats.successful_build_count += 1
    else:
        new_stats.failed_build_count += 1

    if old_stats is None:
        user_build_stats_crud.add_user_build_stats(new_stats)
    else:
        user_build_stats_crud.update_user_build_stats(new_stats)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, ssl_context=("web/cert.pem", "web/key.pem"))

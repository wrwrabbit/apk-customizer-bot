import logging
import os
import shutil
import subprocess
import threading
import traceback
from os.path import abspath
from typing import Optional

import config
import utils
from models import Order
from worker.configure_build import BuildConfigurator
from worker.worker_controller_api import WorkerControllerApi


application_builder_critical_lock = threading.Lock()


class ApplicationBuilder:
    def __init__(self, controller_api: WorkerControllerApi, order: Order):
        self.controller_api = controller_api
        self.order = order

    def build(self):
        try:
            logging.info(f"Starting build for order #{self.order.id}")
            self.recreate_order_dir()
            self.configure_build()

            if not self.order.sources_only:
                self.run_build_script()
            else:
                self.make_sources_archive()

            if self.is_successful_build():
                self.handle_successful_build()
            else:
                self.handle_failed_build()
            self.remove_order_dir()
        except Exception as e:
            self.handle_failed_build(e)
            self.remove_order_dir()

    def recreate_order_dir(self):
        order_dir = self.make_order_dir_path()
        if os.path.isdir(order_dir):
            shutil.rmtree(order_dir, ignore_errors=True)
        os.makedirs(order_dir)

    def make_order_dir_path(self) -> str:
        return utils.make_order_building_dir_path(self.order.id)

    def configure_build(self):
        if config.MOCK_BUILD and not self.order.sources_only:
            return
        args = [
            abspath(self.make_order_dir_path()),
            config.BUILD_DOCKER_IMAGE_NAME
        ]
        with application_builder_critical_lock: # Wait until the repo is updated before terminating the worker.
            try:
                self.run_script("copy_repo.sh", args, cwd=abspath(config.DATA_DIR))
            except subprocess.CalledProcessError:
                repo_path = os.path.join(config.DATA_DIR, "Partisan-Telegram-Android")
                shutil.rmtree(repo_path, ignore_errors=True)
                raise
        BuildConfigurator.configure_build(self.order)

    def run_build_script(self):
        if config.MOCK_BUILD:
            args = [
                str(self.need_mock_error())
            ]
            self.run_script("mock_build.sh", args, cwd=abspath(self.make_order_dir_path()))
        else:
            args = [
                os.path.join(
                    config.PROJECT_ROOT_ABSPATH_ON_HOST,
                    self.make_order_dir_path(),
                    "Partisan-Telegram-Android"
                ),
                config.BUILD_DOCKER_IMAGE_NAME
            ]
            self.run_script("build.sh", args, cwd=abspath(self.make_order_dir_path()))

    def run_script(self, script: str, args: list[str], cwd: str):
        subprocess.run(
            [
                "/bin/sh",
                abspath(os.path.join("scripts", script)),
                *args
            ],
            check=True,
            capture_output=True,
            cwd=cwd,
            encoding="utf-8",
        )

    def need_mock_error(self) -> bool:
        if config.MOCK_BUILD:
            return "error" in self.order.app_id and self.order.build_attempts == 0
        else:
            return False

    def make_sources_archive(self):
        order_dir = self.make_order_dir_path()
        sources_dir = os.path.join(order_dir, "Partisan-Telegram-Android")

        shutil.rmtree(os.path.join(sources_dir, ".git"), ignore_errors=False)
        os.remove(os.path.join(sources_dir, "TMessagesProj/config/release.keystore"))

        shutil.make_archive(os.path.join(order_dir, "sources"), 'zip', sources_dir)

    def is_successful_build(self):
        return os.path.isfile(os.path.join(self.make_order_dir_path(), "done")) or self.order.sources_only

    def handle_successful_build(self):
        with application_builder_critical_lock: # Wait until the order_completed is sent before terminating the worker.
            if not self.order.sources_only:
                self.controller_api.send_order_completed(self.order)
            else:
                self.controller_api.send_sources_only_order_completed(self.order)
        logging.info(f"Build for order #{self.order.id} successful")

    def handle_failed_build(self, exception: Optional[Exception] = None):
        if exception is not None:
            logging.error(f"During build the following exception occurred:", exception)
        else:
            logging.error(f"The build completed but there is no confirmation of success")
        traceback.print_exc()
        with application_builder_critical_lock: # Wait until the order_failed is sent before terminating the worker.
            if exception is None:
                exception_text = None
            elif isinstance(exception, subprocess.CalledProcessError):
                exception_text = f"{type(exception)}\n\nstderr: {exception.stderr}\n\nstdout: {exception.stdout}"
            else:
                exception_text = f"{type(exception)} {str(exception)}\n\n{traceback.format_exc()}"
            logging.error(f"exception_text {exception_text}")
            self.controller_api.send_order_failed(exception_text)
        logging.error(f"Build for order #{self.order.id} failed")

    def remove_order_dir(self):
        shutil.rmtree(self.make_order_dir_path(), ignore_errors=True)

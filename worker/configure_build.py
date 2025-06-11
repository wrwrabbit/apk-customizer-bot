import glob
import io
import json
import logging
import os
import re
import xml.sax.saxutils
from pathlib import Path

from PIL import Image
from PIL.Image import Resampling

import config
from models import Order
from schemas.android_app_permission import AndroidAppPermission
import utils
from worker.app_signature_signer import extract_and_sign_app_signature


class BuildConfigurator:
    def __init__(self, order: Order):
        self.order = order

    @staticmethod
    def configure_build(order: Order) -> None:
        configurator = BuildConfigurator(order)
        configurator.update_project()

    def update_project(self) -> None:
        self.update_text_sources()
        self.replace_icons()
        if not self.order.sources_only:
            self.replace_keystore()
            self.update_keystore_related_text_sources()
        self.save_update_request_template()

    def update_text_sources(self) -> None:
        self.copy_version()
        self.update_permissions()
        self.update_text_source_file(
            relative_path="TMessagesProj/src/main/res/values*/strings.xml", search_by_path=True,
            src=r'(?<=<string name="AppName">)Telegram(?=</string>)',
            dst=self.xml_escape(self.order.app_name),
        )
        self.update_text_source_file(
            relative_path="TMessagesProj/src/main/res/values*/strings.xml", search_by_path=True,
            src=r'(?<=<string name="AppNameBeta">)Telegram Beta(?=</string>)',
            dst=self.xml_escape(self.order.app_name),
        )

        self.update_text_source_file(
            relative_path="TMessagesProj/src/main/assets/strings/overrides.xml",
            src=r'(?<=<string name="AppName">)Telegram(?=</string>)',
            dst=self.xml_escape(self.order.app_name),
        )
        self.update_text_source_file(
            relative_path="TMessagesProj/src/main/assets/strings/overrides.xml",
            src=r'(?<=<string name="AppNameBeta">)Telegram(?=</string>)',
            dst=self.xml_escape(self.order.app_name),
        )
        self.update_text_source_file(
            relative_path="TMessagesProj/src/main/assets/strings/overrides.xml",
            src=r'(?<=<string name="NotificationHiddenName">)Telegram(?=</string>)',
            dst=self.xml_escape(self.order.app_name),
        )
        self.update_text_source_file(
            relative_path="TMessagesProj/src/main/assets/strings/overrides.xml",
            src=r'(?<=<string name="NotificationHiddenChatName">)Telegram(?=</string>)',
            dst=self.xml_escape(self.order.app_name),
        )
        self.update_text_source_file(
            relative_path="TMessagesProj/src/main/assets/strings/overrides.xml",
            src=r'(?<=<string name="SecretChatName">)Telegram(?=</string>)',
            dst=self.xml_escape(self.order.app_name),
        )
        self.update_text_source_file(
            relative_path="TMessagesProj/src/main/assets/strings/overrides.xml",
            src=r'(?<=<string name="NotificationHiddenMessage">)Update Available!(?=</string>)',
            dst=self.xml_escape(self.order.app_notification_text),
        )

        self.update_text_source_file(
            relative_path="gradle.properties",
            src=r'(?<=APP_PACKAGE=)org.telegram.messenger',
            dst=self.order.app_id,
        )
        self.update_text_source_file(
            relative_path="gradle.properties",
            src=r'(?<=APP_VERSION_CODE=)\d+',
            dst=str(self.order.app_version_code),
        )
        self.update_text_source_file(
            relative_path="gradle.properties",
            src=r'(?<=APP_VERSION_NAME=).+',
            dst=self.order.app_version_name,
        )
        self.update_text_source_file(
            relative_path="TMessagesProj_AppStandalone/google-services.json",
            src=r'(?<="package_name": ")org.telegram.messenger(?=")',
            dst=self.order.app_id,
        )

        self.update_text_source_file(
            relative_path="TMessagesProj/src/main/java/org/telegram/messenger/partisan/masked_ptg/MaskedPtgConfig.java",
            src=r'(?<=import org\.telegram\.messenger\.partisan.masked_ptg\.)original\.OriginalScreenFactory(?=;)',
            dst=f'{self.order.app_masked_passcode_screen}.{self.get_masked_screen_factory_class()}',
        )
        self.update_text_source_file(
            relative_path="TMessagesProj/src/main/java/org/telegram/messenger/partisan/masked_ptg/MaskedPtgConfig.java",
            src=r'(?<=IMaskedPasscodeScreenFactory FACTORY = new )OriginalScreenFactory(?=\(\);)',
            dst=self.get_masked_screen_factory_class(),
        )
        if self.order.app_notification_color != -1:
            self.update_text_source_file(
                relative_path="TMessagesProj/src/main/java/org/telegram/messenger/partisan/masked_ptg/MaskedPtgConfig.java",
                src=r'(?<=private static final Integer PRIMARY_COLOR = )null(?=;)',
                dst=f"0xff{self.order.app_notification_color:0>6x}",
            )

    def copy_version(self):
        with open(self.build_absolute_path("gradle.properties"), "rt") as file:
            content = file.read()
            version_code = re.findall("(?<=APP_VERSION_CODE=)\d+", content)[0]
            version_name = re.findall("(?<=APP_VERSION_NAME=).+", content)[0]
        self.update_text_source_file(
            relative_path="TMessagesProj/src/main/java/org/telegram/messenger/partisan/masked_ptg/OriginalVersion.java",
            src=r'(?<=public static final String ORIGINAL_VERSION_STRING = )null(?=;)',
            dst=f'"{version_name}"'
        )
        self.update_text_source_file(
            relative_path="TMessagesProj/src/main/java/org/telegram/messenger/partisan/masked_ptg/OriginalVersion.java",
            src=r'(?<=public static final Integer ORIGINAL_BUILD_VERSION = )null(?=;)',
            dst=f'{version_code}2' # '2' is the code of 'store bundled' version
        )

    def update_permissions(self):
        permissions_mapping = {
            AndroidAppPermission.camera : [
                "android.permission.CAMERA",
                "android.permission.FOREGROUND_SERVICE_CAMERA",
            ],
            AndroidAppPermission.location : [
                "android.permission.ACCESS_COARSE_LOCATION",
                "android.permission.ACCESS_FINE_LOCATION",
                "android.permission.ACCESS_BACKGROUND_LOCATION",
                "android.permission.FOREGROUND_SERVICE_LOCATION",
                "${applicationId}.permission.MAPS_RECEIVE",
            ],
            AndroidAppPermission.microphone : [
                "android.permission.RECORD_AUDIO",
                "android.permission.FOREGROUND_SERVICE_MICROPHONE",
            ],
            AndroidAppPermission.notifications : [
                "android.permission.POST_NOTIFICATIONS",
            ],
            AndroidAppPermission.photos_and_video: [
                "android.permission.READ_MEDIA_IMAGES",
                "android.permission.READ_MEDIA_VIDEO",
                "android.permission.ACCESS_MEDIA_LOCATION",
            ],
            AndroidAppPermission.contacts : [
                "android.permission.GET_ACCOUNTS",
                "android.permission.READ_CONTACTS",
                "android.permission.WRITE_CONTACTS",
            ],
            AndroidAppPermission.music_and_audio : [
                "android.permission.READ_MEDIA_AUDIO",
            ],
            AndroidAppPermission.call_logs : [
                "android.permission.READ_CALL_LOG",
            ],
            AndroidAppPermission.phone : [
                "android.permission.READ_PHONE_NUMBERS",
                "android.permission.READ_PHONE_STATE",
                "android.permission.CALL_PHONE",
                "android.permission.FOREGROUND_SERVICE_PHONE_CALL",
            ],
            AndroidAppPermission.nearby_devices : [
                "android.permission.BLUETOOTH_CONNECT",
                "android.permission.BLUETOOTH",
            ],
            AndroidAppPermission.sms : [
                "android.permission.SEND_SMS",
            ],
        }
        selected_permissions = self.order.permissions.split(",")
        permissions_to_remove = [permission
                                 for visible_name, permissions in permissions_mapping.items()
                                 for permission in permissions
                                 if visible_name not in selected_permissions]

        for permission_to_remove in permissions_to_remove:
            self.update_text_source_file(
                relative_path="**/AndroidManifest*.xml", search_by_path=True,
                src=f'<uses-permission android:name="{permission_to_remove}"\\s*/>',
                dst="",
            )

    def update_text_source_file(self,
                                relative_path: str,
                                src: str,
                                dst: str,
                                search_by_path: bool = False
                                ) -> None:
        absolute_path = self.build_absolute_path(relative_path)
        paths = glob.glob(absolute_path, recursive=True) if search_by_path else [absolute_path]
        for path in paths:
            with open(path, "rt") as file:
                content = file.read()
            content = re.sub(src, dst, content)
            with open(path, "wt") as file:
                file.write(content)

    def build_absolute_path(self, ending: str) -> str:
        return os.path.join(self.make_order_dir_path(), "Partisan-Telegram-Android", ending)

    def make_order_dir_path(self) -> str:
        return utils.make_order_building_dir_path(self.order.id)

    def get_masked_screen_factory_class(self) -> str:
        if self.order.app_masked_passcode_screen == "calculator":
            return "CalculatorScreenFactory"
        elif self.order.app_masked_passcode_screen == "loading":
            return "LoadingScreenFactory"
        elif self.order.app_masked_passcode_screen == "note":
            return "NoteScreenFactory"
        else:
            raise Exception("Invalid screen name")

    def replace_icons(self) -> None:
        dpi_variants = dict(
            xxxhdpi=(192, 192),
            xxhdpi=(144, 144),
            xhdpi=(96, 96),
            hdpi=(72, 72),
            mdpi=(48, 48)
        )

        file_names = [
            'TMessagesProj/src/main/res/drawable-<dpi>/ic_launcher_dr.png',
            'TMessagesProj/src/main/res/mipmap-<dpi>/ic_launcher.png',
            'TMessagesProj/src/main/res/mipmap-<dpi>/ic_launcher_round.png',
        ]
        notification_file_names = [
            'TMessagesProj/src/main/res/drawable-<dpi>/notification.png',
        ]

        with (Image.open(io.BytesIO(self.order.app_icon)) as icon,
              Image.open(io.BytesIO(self.order.app_notification_icon)) as notification_icon):
            for dpi_name, size in dpi_variants.items():
                logging.info(f"Replacing icon {dpi_name}")
                icon_copy = icon.resize(size, Resampling.LANCZOS)
                notification_icon_copy = notification_icon.resize(size, Resampling.LANCZOS)
                for file_name_template in file_names + notification_file_names:
                    file_name = file_name_template.replace('<dpi>', dpi_name)
                    out_path = self.build_absolute_path(file_name)
                    if os.path.isfile(out_path):
                        with open(out_path, 'wb') as f:
                            if file_name_template in file_names:
                                icon_copy.save(f)
                            elif file_name_template in notification_file_names:
                                notification_icon_copy.save(f)
        logging.info("Done replacing icons")

    def replace_keystore(self):
        keystore_path = self.build_absolute_path("TMessagesProj/config/release.keystore")
        Path(keystore_path).unlink(missing_ok=True)
        if self.order.keystore is not None:
            with open(keystore_path, "wb") as f:
                f.write(self.order.keystore)

    def update_keystore_related_text_sources(self):
        full_keystore_password = self.order.keystore_password_salt + config.KEYSTORE_PASSWORD + self.order.keystore_password_salt
        self.update_text_source_file(
            relative_path="gradle.properties",
            src=r'(?<=RELEASE_KEY_PASSWORD=)UCKJJtMyqB!9uGrAw6xu',
            dst=full_keystore_password,
        )
        self.update_text_source_file(
            relative_path="gradle.properties",
            src=r'(?<=RELEASE_STORE_PASSWORD=)LdAaKx_MFWGzL4ix4Jj\*',
            dst=full_keystore_password,
        )
        keystore_path = self.build_absolute_path("TMessagesProj/config/release.keystore")
        signed_app_signature = extract_and_sign_app_signature(keystore_path, full_keystore_password)
        self.update_text_source_file(
            relative_path="TMessagesProj/src/main/java/org/telegram/messenger/partisan/appmigration/AppMigrator.java",
            src=r'(?<=private static final String signedAppSignature = )null(?=;)',
            dst='"' + signed_app_signature + '"',
        )

    def save_update_request_template(self):
        template_dict = self.order.make_dict_for_worker()
        del template_dict['id']
        template_dict['update_tag'] = None
        template_path = self.build_absolute_path("TMessagesProj/src/main/assets/update-request-template.json")
        with open(template_path, "wb") as f:
            f.write(json.dumps(template_dict).encode())

    def xml_escape(self, s: str):
        escaped = xml.sax.saxutils.escape(s)
        return (escaped
                .replace("%", "%%")
                .replace("'", "\\'"))

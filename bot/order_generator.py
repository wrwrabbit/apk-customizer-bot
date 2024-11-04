import glob
import os.path
import re
import shutil
import subprocess
from datetime import datetime, timedelta
from random import Random

import names
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA512
from countryinfo import CountryInfo

import config
import utils
from schemas.android_app_permission import default_permissions
from .app_generation_sources import app_id_sources
from .app_generation_sources.app_template import AppTemplate
from .app_generation_sources.app_templates import ROOT_APP_TEMPLATE
from .app_generation_sources import keystore_sources
from models import Order


class OrderGenerator:
    def __init__(self, order: Order):
        self.order = order
        if config.SALT_FOR_DERIVATION_RANDOM_SEED_FROM_USER_ID is not None:
            random_seed = PBKDF2(str(self.order.user_id),
                                 config.SALT_FOR_DERIVATION_RANDOM_SEED_FROM_USER_ID.encode(),
                                 64,
                                 hmac_hash_module=SHA512)
            self.random = Random(random_seed)
        else:
            self.random = Random()
        self.organization = None

    def generate_order_values(self, passcode_screen: str):
        self.order.app_masked_passcode_screen = passcode_screen
        self.order.app_version_code = self.random_version_code()
        self.order.app_version_name = self.random_version_name()
        self.order.app_notification_color = 0
        self.order.permissions = ",".join(default_permissions)
        self.generate_keystore()

        self.generate_order_values_from_template(ROOT_APP_TEMPLATE)


    def generate_order_values_from_template(self, template: AppTemplate):
        if template.possible_names is not None:
            self.order.app_name = self.random.choice(template.possible_names)
            self.order.app_id = self.generate_app_id()
        if template.possible_icons is not None:
            self.order.app_icon = self.choose_app_icon(template)
            self.order.app_notification_icon = self.order.app_icon
        if template.possible_notifications is not None:
            self.order.app_notification_text = self.random.choice(template.possible_notifications)

        if template.inner_templates is not None:
            matched_templates = [
                t
                for t in template.inner_templates
                if t.screen_name == self.order.app_masked_passcode_screen or t.screen_name is None
            ]
            if len(matched_templates) == 0:
                raise Exception(f"Template not found for passcode screen {self.order.app_masked_passcode_screen}.")
            elif len(matched_templates) == 1:
                template = matched_templates[0]
            else:
                template = self.random.choice(matched_templates)
            self.generate_order_values_from_template(template)


    def choose_app_icon(self, template: AppTemplate) -> bytes:
        path = self.random.choice(template.possible_icons)
        icon_paths = glob.glob(os.path.join("./bot/app_generation_sources/", path), recursive=True)
        icon_paths = [path for path in icon_paths if not os.path.isdir(path)]
        icon_path = self.random.choice(icon_paths)
        with open(icon_path, 'rb') as f:
            return f.read()


    def random_version_code(self) -> int:
        return self.random.randint(1, 100)


    def random_version_name(self) -> str:
        parts = [str(self.random.randint(1, 10)) for _ in range(0, 3)]
        return ".".join(parts)


    def generate_app_id(self):
        prefix = self.random.choice(app_id_sources.PREFIXES)
        postfix = self.random.choice(app_id_sources.POSTFIXES)
        delimiter = self.random.choice(app_id_sources.DELIMITERS)
        normalized_app_name = utils.normalize_name(self.order.app_name, delimiter)

        app_id = prefix
        probability = self.random.random()
        if self.organization is not None and probability < app_id_sources.probability_has_organization:
            normalized_organization = utils.normalize_name(self.organization)
            app_id += f".{normalized_organization}"
        app_id += f".{normalized_app_name}"
        if self.random.random() < app_id_sources.probability_has_postfix:
            app_id += f".{postfix}"
        return app_id

    def generate_keystore(self):
        keystore_dir = os.path.join(config.TMP_DIR, "keystores", str(self.order.id))
        os.makedirs(keystore_dir, exist_ok=True)
        keystore_path = os.path.join(keystore_dir, "release.keystore")
        subprocess.run(self.generate_keytool_command(keystore_path), shell=True, encoding="utf-8")
        with open(keystore_path, "rb") as f:
            self.order.keystore = f.read()
        shutil.rmtree(keystore_dir)

    def generate_keytool_command(self, keystore_path: str):
        start_date = datetime.now() - timedelta(seconds=self.random.randint(0, keystore_sources.max_key_age))
        start_date_str = start_date.strftime("%Y/%m/%d %H:%M:%S")
        validity = self.random.choice(keystore_sources.key_validity_options)
        key_size = self.random.choice(keystore_sources.key_size_options)
        return (f'keytool -genkey -keystore {keystore_path} -deststoretype JKS -keyalg RSA -keysize {key_size} '
                f'-startdate "{start_date_str}" -validity {validity} -alias key0' +
                f' -dname "{self.generate_distinguished_name_for_keystore()}"' +
                f' -storepass {config.KEYSTORE_PASSWORD} -keypass {config.KEYSTORE_PASSWORD}')

    def generate_distinguished_name_for_keystore(self):
        full_name = names.get_full_name()
        self.organization = organization = self.random.choice(keystore_sources.organizations)
        organization_unit = self.random.choice(keystore_sources.organization_units)
        country = self.random.choice(keystore_sources.countries)
        country_code = CountryInfo(country).iso()["alpha2"]
        locality = CountryInfo(country).capital()

        dname = ''
        if self.random.random() < keystore_sources.probability_has_cn:
            if self.random.random() < keystore_sources.probability_cn_is_organization_unit:
                dname += f'cn={organization_unit}, '
            else:
                dname += f'cn={full_name}, '
        if self.random.random() < keystore_sources.probability_has_ou:
            if self.random.random() < keystore_sources.probability_ou_is_organization:
                dname += f'ou={organization}, '
            else:
                dname += f'ou={organization_unit}, '
        if self.random.random() < keystore_sources.probability_has_o:
            dname += f'o={organization}, '
        if self.random.random() < keystore_sources.probability_has_c:
            dname += f'c={country_code}, '
        if self.random.random() < keystore_sources.probability_has_l:
            dname += f'l={locality}, '

        return re.sub(', $', '', dname)

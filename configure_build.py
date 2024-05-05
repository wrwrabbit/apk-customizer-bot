import glob
import os
import re
import sys
from PIL import Image


def replace_text(filepath, text, sub):
    with open(filepath, "rt") as file:
        content = file.read()

    with open(filepath, "wt") as file:
        content = content.replace(text, sub)
        file.write(content)


def replace_regex(filepath, pattern, text):
    with open(filepath, "rt") as file:
        content = file.read()

    with open(filepath, "wt") as file:
        content = re.sub(pattern, text, content)
        file.write(content)


def append_text(filepath, text):
    with open(filepath, "rt") as file:
        content = file.read()

    content = f"{content.rstrip()} {text}"
    with open(filepath, "wt") as file:
        file.write(content)


DIMENSIONS = dict([
    ('xxxhdpi', (192, 192)),
    ('xxhdpi', (144, 144)),
    ('xhdpi', (96, 96)),
    ('hdpi', (72, 72)),
    ('mdpi', (48, 48))
])


def replace_icons(userdir, icon_src):
    prefix = os.path.join(
        userdir,
        'Partisan-Telegram-Android',
        'TMessagesProj',
        'src',
        'main',
        'res',
    )
    fnames = [
        'ic_launcher.png',
        'ic_launcher_sa.png',
        'ic_launcher_round.png'
    ]
    def out_dir(resolution):
        path = os.path.join(
            prefix,
            f'mipmap-{resolution}',
        )
        return path

    for resolution, size in DIMENSIONS.items():
        print(f"Replacing icon {resolution}")
        with Image.open(icon_src) as im:
            imcopy = im.copy()
            imcopy.thumbnail(size, Image.ANTIALIAS)
            for fname in fnames:
                out_path = os.path.join(out_dir(resolution), fname)
                with open(out_path, 'wb') as f:
                    imcopy.save(f)
    print("Done replacing icons")


def remove_xmls(userdir):
    prefix = os.path.join(
        userdir,
        'Partisan-Telegram-Android',
        'TMessagesProj',
        'src',
        'main',
        'res',
        'mipmap-anydpi-v26'
    )
    fnames = [
        'ic_launcher.xml',
        'ic_launcher_sa.xml',
        'ic_launcher_round.xml',
    ]
    for fname in fnames:
        path = os.path.join(prefix, fname)
        print(f"Removing {path}")
        os.remove(path)


def update_sources(order_dir, app_id, app_name, app_icon):
    build_path = lambda x: os.path.join(order_dir, "Partisan-Telegram-Android", x)

    for manifest_file in glob.glob(
        build_path("**/AndroidManifest*.xml"), recursive=True
    ):
        replace_text(
            manifest_file,
            'package="org.telegram.messenger"',
            f'package="{app_id}"',
        )
        replace_text(
            manifest_file,
            'android:name=".',
            f'android:name="org.telegram.messenger.',
        )

    for strings_file in glob.glob(
        build_path("TMessagesProj/src/main/res/**/strings.xml"), recursive=True
    ):
        replace_regex(
            strings_file,
            r'<string name="AppName">\w+</string>',
            f'<string name="AppName">{app_name}</string>',
        )

    replace_text(
        build_path("gradle.properties"),
        'APP_PACKAGE=org.telegram.messenger',
        f'APP_PACKAGE={app_id}',
    )
    replace_text(
        build_path("TMessagesProj/build.gradle"),
        "android {",
        "android {\n    namespace 'org.telegram.messenger'",
    )
    replace_text(
        build_path("TMessagesProj_App/google-services.json"),
        '"package_name": "org.telegram.messenger"',
        f'"package_name": "{app_id}"',
    )
    append_text(
        build_path("Dockerfile"),
        " && chmod -R 777 /home/source/TMessagesProj/build\n",
    )
    replace_icons(order_dir, app_icon)
    remove_xmls(order_dir)


if __name__ == "__main__":
    update_sources(*sys.argv)

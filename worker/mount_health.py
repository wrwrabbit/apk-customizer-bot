import ctypes
import errno
import logging
import os
from typing import Optional

import config

MS_BIND = 4096
MNT_DETACH = 2

_libc: Optional[ctypes.CDLL] = None
_unexpected_error_logged = False


def _get_libc() -> ctypes.CDLL:
    global _libc
    if _libc is None:
        _libc = ctypes.CDLL(None, use_errno=True)
    return _libc


def is_mount_syscall_lost() -> bool:
    global _unexpected_error_logged
    check_dir = os.path.join(config.TMP_DIR, "mount_check")
    src = os.path.join(check_dir, "src")
    dst = os.path.join(check_dir, "dst")
    os.makedirs(src, exist_ok=True)
    os.makedirs(dst, exist_ok=True)

    libc = _get_libc()
    if libc.mount(src.encode(), dst.encode(), None, MS_BIND, None) != 0:
        err = ctypes.get_errno()
        if err == errno.ENOSYS:
            return True
        if not _unexpected_error_logged:
            logging.warning(f"Mount health check is inconclusive: mount failed with {os.strerror(err)}")
            _unexpected_error_logged = True
        return False

    if libc.umount2(dst.encode(), MNT_DETACH) != 0:
        logging.error(f"Mount health check could not unmount {dst}: {os.strerror(ctypes.get_errno())}")
    return False

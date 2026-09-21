"""Verify the bundled JsonCpp license matches its upstream 1.7.2 release."""

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR_DIR = Path("run_game/run_game/json")
LICENSE = VENDOR_DIR / "LICENSE"
VERSION = VENDOR_DIR / "version.h"
# Official 1.7.2 tag: https://github.com/open-source-parsers/jsoncpp/tree/1.7.2
# Resolved upstream commit: c8054483f82afc3b4db7efe4e5dc034721649ec8
LICENSE_SHA256 = "f997a41ccd0bf836c49c91a3bf0dd69a0368cc8f8ae7fa5f4aaf1b73c866f9c5"


def main() -> int:
    """Reject a missing, untracked, or changed JsonCpp license notice."""
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", LICENSE.as_posix()],
        cwd=ROOT, capture_output=True, check=False,
    ).returncode == 0
    version = (ROOT / VERSION).read_text(encoding="utf-8")
    license_file = ROOT / LICENSE
    valid = (
        tracked
        and '# define JSONCPP_VERSION_STRING "1.7.2"' in version
        and license_file.is_file()
        and hashlib.sha256(license_file.read_bytes()).hexdigest() == LICENSE_SHA256
    )
    if not valid:
        print("[VENDOR-NOTICE] FAIL: JsonCpp 1.7.2 license missing, untracked, or changed")
        return 1
    print("[VENDOR-NOTICE] PASS: JsonCpp 1.7.2 license tracked and intact")
    return 0


if __name__ == "__main__":
    sys.exit(main())

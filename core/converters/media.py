import json
import shutil
import subprocess
from _warnings import warn

from core.base import DocumentConverter


class MediaConverter(DocumentConverter):
    """
    Abstract class for multi-modal media (e.g., images and audio)
    """

    def _get_metadata(self, local_path, exiftool_path=None):
        if not exiftool_path:
            which_exiftool = shutil.which("exiftool")
            if which_exiftool:
                warn(
                    f"""Implicit discovery of 'exiftool' is disabled. If you would like to continue to use exiftool in MarkItDown, please set the exiftool_path parameter in the MarkItDown consructor. E.g., 

    md = MarkItDown(exiftool_path="{which_exiftool}")

This warning will be removed in future releases.
""",
                    DeprecationWarning,
                )

            return None
        else:
            try:
                result = subprocess.run(
                    [exiftool_path, "-json", local_path], capture_output=True, text=True
                ).stdout
                return json.loads(result)[0]
            except Exception:
                return None

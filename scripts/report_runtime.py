"""Portable asset and executable paths for report editions 11 and 12."""
from pathlib import Path
from shutil import which

import matplotlib


def font_path(filename):
    """Use Matplotlib's bundled DejaVu fonts on every supported platform."""
    return str(Path(matplotlib.get_data_path()) / "fonts" / "ttf" / filename)


def pdftotext_path():
    executable = which("pdftotext")
    if executable is None:
        raise RuntimeError("Install Poppler and add pdftotext to PATH to validate PDF text bounds.")
    return executable

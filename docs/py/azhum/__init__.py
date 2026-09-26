"""AzHumanizer — Azərbaycan dili üçün AI-siz (qayda + lüğət əsaslı) humanizer."""
from .engine import Resources, humanize, humanize_once, LEVELS  # noqa: F401
from .loader import load_resources  # noqa: F401

__version__ = "1.0"

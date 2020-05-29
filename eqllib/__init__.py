"""EQL Analytics Library."""

from .attack import build_attack, get_matrix
from .loader import Configuration
from .normalization import Normalizer

__version__ = '0.3.1'
__all__ = (
    "build_attack",
    "Configuration",
    "get_matrix",
    "Normalizer",
)

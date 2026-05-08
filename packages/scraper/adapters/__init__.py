"""University adapter implementations.

Only adapters without optional heavy dependencies are imported here. Other
adapters can be imported directly from their module or via the lazy CLI/scan
registries.
"""

from .base import BaseUniversityAdapter, UniversityAdapterProtocol
from .stanford import StanfordAdapter
from .cmu import CMUAdapter
from .berkeley import BerkeleyAdapter

from .tamu_cse import TamuCseAdapter

__all__ = [
    "TamuCseAdapter",
    "BaseUniversityAdapter",
    "UniversityAdapterProtocol",
    "StanfordAdapter",
    "CMUAdapter",
    "BerkeleyAdapter",
]

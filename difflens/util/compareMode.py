from enum import Enum


class CompareMode(Enum):
    PARTIAL = "partial-hash"
    FULL = "full-hash"
    SIZE = "file-size"

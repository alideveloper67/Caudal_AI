import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maestro_pooh import pose  # noqa: E402


def dibujar(M):
    pose(M, 1)

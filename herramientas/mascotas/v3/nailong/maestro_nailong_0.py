# Cuadro 0 de nailong (la forma está en maestro_nailong_base.py; pose = 0)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from maestro_nailong_base import pose  # noqa: E402


def dibujar(M):
    pose(M, 0)

# Cuadro 0 de toothless (la forma está en maestro_toothless_base.py; pose = 0)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from maestro_toothless_base import pose  # noqa: E402


def dibujar(M):
    pose(M, 0)

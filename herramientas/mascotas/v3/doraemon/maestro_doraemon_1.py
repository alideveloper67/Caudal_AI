# Cuadro 1 de doraemon (la forma está en maestro_doraemon_base.py; pose = 1)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from maestro_doraemon_base import pose  # noqa: E402


def dibujar(M):
    pose(M, 1)

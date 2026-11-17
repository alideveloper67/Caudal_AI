# Maestro de mickey, cuadro 0 (la figura vive en comun_mickey.py)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from comun_mickey import pose  # noqa: E402


def dibujar(M):
    pose(M, 0)

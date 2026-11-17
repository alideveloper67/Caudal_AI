# Maestro de rilakkuma, cuadro 0 (la figura vive en comun_rilakkuma.py)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from comun_rilakkuma import pose  # noqa: E402


def dibujar(M):
    pose(M, 0)

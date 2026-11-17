# Maestro de nyan, cuadro 1 (la figura vive en comun_nyan.py)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from comun_nyan import pose  # noqa: E402


def dibujar(M):
    pose(M, 1)

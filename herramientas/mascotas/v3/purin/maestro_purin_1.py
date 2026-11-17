# Maestro de purin, cuadro 1 (la figura vive en comun_purin.py)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from comun_purin import pose  # noqa: E402


def dibujar(M):
    pose(M, 1)

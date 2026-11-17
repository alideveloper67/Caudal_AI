import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import base_hellokitty as B


def dibujar(M):
    B.dibujar(M, f=0)

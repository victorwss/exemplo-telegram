from typing import Sequence
from dataclasses import dataclass

@dataclass(frozen = True)
class Pessoa:
    nome: str
    masc: bool

def pessoa_random(distribuicao: Sequence[bool] = (True, False)) -> Pessoa:
    ...
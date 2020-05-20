import random
from flask import Flask, request, jsonify
from br_nome_gen import pessoa_random
from typing import Any, cast, Dict, List, Tuple, TypeVar, TYPE_CHECKING

T = TypeVar('T')

def random_element(*itens: T) -> T:
    return random.sample(itens, 1)[0]

def random_cpf() -> str:
    cpf = ""
    for i in range(0, 11):
       cpf += random_element(*"0123456789")
    return cpf

dados: Dict[str, str] = {}
for i in range(0, 200):
    dados[random_cpf()] = pessoa_random().nome.upper()
print(dados)

app = Flask(__name__)

@app.route("/api/AutenticacaoSxyz/ReiniciarSenha", methods = ["POST"])
def reset() -> Tuple[str, int]:
    corpo: Dict[str, str] = request.form
    if "cpf" not in corpo:
        return "CPF obrigatório", 400
    if corpo["cpf"] not in dados:
        return "Usuário não encontrado", 404
    return "Foi", 200

@app.route("/api/funcionarios/BuscarPorListaCPF", methods = ["POST"])
def buscar() -> Tuple[str, int]:
    if request.content_type is None or not request.content_type.startswith('application/json'):
        return "Errado. Você tinha que fazer uma requisição como JSON.", 415
    corpo: Any = request.json
    print(corpo)
    if not isinstance(corpo, list):
        return "Zoado 1", 400
    for x in corpo:
        if not isinstance(x, str): return "Zoado 2", 400
    cpfs: List[str] = cast(List[str], corpo)
    saida: List[Dict[str, str]] = []
    for cpf in cpfs:
        if cpf in dados:
            saida.append({"nome": dados[cpf], "codigoCPF": cpf})
    print(saida)
    return jsonify(saida), 200

@app.route("/dump")
def mostrar_tudo() ->  Tuple[str, int]:
    return dados, 200

if __name__ == "__main__":
    app.run()
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import sleep
from os import getpid
import requests
import telebot
import json
import sys

token: str
host: str
with open('token.json') as f:
    s: Any = json.load(f)
    token = s['token']
    host = s['host']

bot = telebot.TeleBot(token)
id_bot: int = bot.get_me().id

class TentarDeNovoException(Exception):
    pass

def reset_senha(cpf: str, definitivo: bool) -> str:
    if len(cpf) != 11: return f"❌ O CPF {cpf} tem {len(cpf)} dígitos, mas deveria ter 11. Por favor, me informe APENAS CPFs com 11 dígitos."
    try:
        resposta = requests.api.post(f"{host}/api/AutenticacaoSxyz/ReiniciarSenha", data = {"cpf": cpf}, timeout = (5, 5))
    except requests.exceptions.ConnectionError:
        if not definitivo: raise TentarDeNovoException()
        return f"⚠️ Não consegui conectar no SXYZ para resetar a senha do CPF {cpf}. Tentei três vezes. Me peça para tentar fazer isso de novo mais tarde, recomeçando todo o processo."
    except requests.exceptions.Timeout:
        if not definitivo: raise TentarDeNovoException()
        return f"⚠️ Tentei resetar a senha do CPF {cpf} no SXYZ, mas o SXYZ não respondeu. Tentei três vezes. Me peça para tentar fazer isso de novo mais tarde, recomeçando todo o processo."
    except Exception as x:
        return f"⚠️ Tentei conectar no SXYZ para resetar a senha do CPF {cpf}, mas um erro inesperado chamado {x.__class__.__name__} aconteceu. Me peça para tentar fazer isso de novo mais tarde, recomeçando todo o processo."
    if resposta.status_code == 404:
        return f"❌ O usuário {cpf} não existe."
    if resposta.status_code != 200:
        return f"⚠️ O SXYZ devolveu um erro inesperado {resposta.status_code} ao tentar resetar a senha do CPF {cpf}. Me peça para tentar fazer isso de novo mais tarde, recomeçando todo o processo."
    return f"✅ A senha do(a) usuário(a) {cpf} foi resetada com sucesso. A nova senha provisória é Sxyz-{cpf}."

def parse(texto: str) -> List[str]:
    lista: List[str] = []
    proximo: str = ""
    for c in texto:
        if c >= '0' and c <= '9':
            proximo += c
        elif c in ['.', '-', '/']:
            pass
        else:
            if len(proximo) > 2:
                lista.append(proximo)
            proximo = ""
    if len(proximo) > 2:
        lista.append(proximo)
    return lista

@dataclass(frozen = True)
class Busca:
    texto: str
    cpfs: List[str]

    @staticmethod
    def erro(texto):
        return Busca(texto, [])

class Pendencia:
    def __init__(self, cpfs: List[str], autor: str):
        self.__cpfs: List[str] = cpfs
        self.__data: datetime = datetime.now()
        self.__autor: str = autor

    @property
    def cpfs(self) -> List[str]:
        return self.__cpfs

    @property
    def data(self) -> datetime:
        return self.__data

    @property
    def autor(self) -> str:
        return self.__autor

    @property
    def velho(self) -> bool:
        return (datetime.now() - self.data).total_seconds() > 600

pendentes: Dict[int, Pendencia] = {}

dez_minutos = "👉 Responda a esta mensagem dentro de 10 minutos com SIM para confirmar, ou NÃO para cancelar."

def buscar_nomes(message_id: int, texto: str) -> Busca:
    cpfs: List[str] = parse(texto)
    if len(cpfs) == 0: return Busca.erro("❓ Desculpe, não entendi o que você pediu. Me passe apenas os números de CPFs com 11 dígitos para eu resetar as senhas.")

    pesquisar: List[str] = []
    lixos: List[str] = []
    for e in cpfs:
        if len(e) == 11:
            pesquisar.append(e)

    for i in range(0, 3):
        try:
            resposta = requests.api.post(f"{host}/api/funcionarios/BuscarPorListaCPF", json = pesquisar, timeout = (5, 5))
            if resposta.status_code != 200:
                return Busca.erro(f"⚠️ O SXYZ devolveu um erro inesperado {resposta.status_code} ao tentar encontar os nomes para os CPFs {cpfs}. Me peça para tentar fazer isso de novo mais tarde.")
            saida: Dict[str, str] = {}
            out: str = ""
            ok: bool = False
            for e in resposta.json():
                cpf: str = e["codigoCPF"]
                saida[cpf] = e["nome"]
            for s in cpfs:
                if s in lixos:
                    out += f"\n❌ O CPF {s} não tem 11 dígitos."
                elif s in saida:
                    out += f"\n🙋 O CPF {s} pertence a \"{saida[s]}\"."
                    ok = True
                else:
                    out += f"\n👤 O CPF {s} aparentemente não existe."
            if len(saida) == 0: return Busca.erro(out[1:])
            if ok: out += "\n\n" + dez_minutos
            return Busca(out, list(saida.keys()))
        except requests.exceptions.ConnectionError:
            if i == 2: return Busca.erro(f"⚠️ Não consegui conectar no SXYZ para buscar os nomes vinculados aos CPFs {cpfs}. Tentei três vezes. Me peça para tentar fazer isso de novo mais tarde.")
        except requests.exceptions.Timeout:
            if i == 2: return Busca.erro(f"⚠️ Tentei resetar a senha do CPF {cpf} no SXYZ, mas o SXYZ não respondeu. Tentei três vezes. Me peça para tentar fazer isso de novo mais tarde.")
        except Exception as x:
            print(x)
            return Busca.erro(f"⚠️ Tentei conectar no SXYZ para buscar os nomes pertencentes aos CPFs {cpfs}, mas um erro inesperado chamado {x.__class__.__name__} aconteceu. Me peça para tentar fazer isso de novo mais tarde.")
        sleep(5)
    return Busca.erro(f"⚠️ Ops, estou bugadão, foi mal. Estava tentando buscar os nomes pertencentes aos CPFs {cpfs}.")

def contem_texto(palheiro: str, *agulhas: str) -> bool:
    for agulha in agulhas:
        if agulha in palheiro:
            return True
    return False

def processar_mensagem_confirmacao(id_original: int, texto: str, autor: str) -> str:
    original_valida: bool = id_original in pendentes

    if original_valida and autor != pendentes[id_original].autor:
        return "✋ Desculpe. Por medida de segurança, só aceito confirmações ou cancelamentos de resets vindos da mesma pessoa que os solicitou."

    em_minusculas: str = texto.lower()

    if contem_texto(em_minusculas, "não", "nao", "cancel", "abort", "errad", "incorret", "👎", "❌", "❎"):
        if not original_valida:
            return "✋ Entendi que você queria cancelar alguma requisição, mas ou ela já havia sido processada ou era antiga demais."
        del pendentes[id_original]
        return "❌ Entendi que a resposta foi NÃO. Logo, cancelei a requisição."
    if not contem_texto(em_minusculas, "sim", "confirm", "ok", "blz", "bele", "belê", "segue", "segui", "siga", "cert", "corret", "👍", "✅", "☑️", "✔️"):
        if not original_valida:
            return "✋ Não entendi a sua resposta. Entretanto, você estava respondendo a uma mensagem que ou já havia sido processada ou era antiga demais."
        return "❓ Não entendi a sua resposta. Responda apenas SIM para confirmar ou NÃO para cancelar."

    if not original_valida:
        return "✋ Entendi que você queria confirmar alguma requisição, mas ou ela já havia sido processada ou era antiga demais."

    lista: List[str] = pendentes[id_original].cpfs
    resposta: str = ""
    tentar_de_novo: List[str] = []
    tentar_outra_vez: List[str] = []

    # Primeira tentativa.
    for cpf in lista:
        try:
            resposta += "\n" + reset_senha(cpf, False)
        except TentarDeNovoException:
            tentar_de_novo.append(cpf)

    # Segunda tentativa.
    if len(tentar_de_novo) != 0:
        sleep(5)
        for cpf in tentar_de_novo:
            try:
                resposta += "\n" + reset_senha(cpf, False)
            except TentarDeNovoException:
                tentar_outra_vez.append(cpf)

    # Terceira tentativa.
    if len(tentar_outra_vez) != 0:
        sleep(5)
        for cpf in tentar_outra_vez:
            resposta += "\n" + reset_senha(cpf, True)

    del pendentes[id_original]
    return resposta[1:]

def escrever(texto):
    d: datetime = datetime.now()
    log = f"[{d}] {texto}"
    with open("bot.log", "a", encoding = 'utf-8') as f:
        f.write(log)
    print(log)

versao = "4"

regras = f"""
🤖 Eu sou o BOT reset senha SXYZ (versão {versao}).

👉 Este grupo serve para realizar o reset de senhas do SXYZ.

👉 As mensagens postadas aqui são lidas por um BOT (eu) que procurará números de CPF nelas para resetar as respectivas senhas. No entanto, antes de prosseguir com o reset, informarei quais são os nomes correspondentes a esses CPFs e esperarei uma mensagem de confirmação (preferencialmente apenas SIM ou NÃO, mas sei interpretar um pouquinho mais que isso também).

👉 Não poste mensagens neste grupo que não sejam destinadas a mim, use outros grupos para isso.

👉 E quando for mandar mensagens para mim, lembre-se que sou apenas um simples programa de computador e não possuo inteligência humana. Não sou capaz de interpretar imagens, áudios, documentos ou vídeos. Só sei ler texto. E tudo que faço com esses textos é procurar por números de CPFs neles e encontrar os nomes dos respectivos usuários, para então resetar as senhas após confirmação.

👉 Para reclamações e sugestões, procure os funcionários humanos que administram este grupo.

👀 As mensagens deste grupo são vistas por todos para que possam ser auditadas. Os administradores têm a prerrogativa de determinar quem pode ou não participar deste grupo conforme o necessário e conveniente para o propósito do mesmo. Mensagens de teste e mensagens impertinentes serão posteriormente apagadas pelos administradores do grupo. Apenas mensagens diretamente relacionadas a reset de senhas e que não tenham sido postadas para finalidade de testes serão mantidas.

⚠️ Providências serão tomadas pelos administradores deste grupo no caso de eventuais abusos ou má utilização.

👉 Também deixamos claro que essa funcionalidade é provisória e está sendo utilizada como uma medida paliativa (um quebra-galho). Dependendo de como for utilizada e de quais resultados forem produzidos, poderá ser modificada, ampliada ou descontinuada no futuro.

❤️ Obrigado, é um prazer servir a todos vocês.
"""

texto_versao = f"""
🤖 Eu sou o BOT reset senha SXYZ (versão {versao}).

🕹️ Fui programado por Victor Williams Stafusa da Silva (@victor_stafusa).
"""

so_texto = "✋ Desculpe. Sou apenas um simples programa de computador e não possuo inteligência humana. Não sou capaz de interpretar imagens, áudios, documentos ou vídeos. Só sei ler texto."

def limpar():
    deletar: List[int] = []
    for e in pendentes:
        if pendentes[e].velho:
            deletar.append(e)
    for e in deletar:
        del pendentes[e]

def find_username(message: Any) -> str:
    a: Optional[str] = message.from_user.first_name
    b: Optional[str] = message.from_user.last_name
    if a == None: a = ""
    if b == None: b = ""
    nome: str = f"{a} {b}".strip()
    return f"{nome} (@{message.from_user.username})" if nome != "" else f"@{message.from_user.username}"

@bot.message_handler(func = lambda message: True, content_types = ['audio', 'video', 'document', 'text', 'location', 'contact', 'sticker'])
def ouvir_mensagem(message: Any):
    if message.from_user.is_bot: return
    remetente: str = find_username(message)
    out: str
    lembrar: List[str] = []
    #if message.chat.id != sala_chat:
    #    out = rejeito
    #elif message.content_type != 'text':
    if message.content_type != 'text':
        out = so_texto
    elif message.text.strip().lower() == 'regras':
        out = regras
    elif message.text.strip().lower() in ['versao', 'versão']:
        out = texto_versao
    elif message.reply_to_message is not None and message.reply_to_message.from_user.id == id_bot and dez_minutos in message.reply_to_message.text:
        out = processar_mensagem_confirmacao(message.reply_to_message.message_id, message.text, message.from_user.username)
    else:
        s: Busca = buscar_nomes(message.message_id, message.text)
        out = s.texto
        lembrar = s.cpfs
    out = f"Olá, {remetente}.\n" + out
    resposta = bot.reply_to(message, out)
    escrever(f"Remetente: {remetente} /// Mensagem: {message.text} /// Resposta: [{resposta.message_id}] - {out}\n")
    if len(lembrar) != 0:
        pendentes[resposta.message_id] = Pendencia(lembrar, message.from_user.username)
    limpar()

print(f"Meu PID é {getpid()}")
print(bot.get_me())

while True:
    try:
        bot.polling()
    except requests.exceptions.ConnectionError as x:
        out = f"Erro que aconteceu espontaneamente: {x}\n"
        escrever(out)
        sleep(5)
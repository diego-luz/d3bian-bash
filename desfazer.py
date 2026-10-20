"""Volta o terminal ao que era antes do projeto.

O restaurar comum do modelo copia de volta os arquivos guardados, e aqui isso
nao basta: a troca de shell nao e arquivo, o xfconf guarda as cores na memoria
e sobrescreve o XML, e os arquivos do conf.d nao existiam antes. Por isso cada
coisa e desfeita do jeito dela:

- shell do login: volta ao que a receita 00 guardou (sem registro, fica como esta)
- conf.d do bash e presets do fastfetch: apagados
- .bashrc e gtk.css: sai so o bloco marcado, o resto do arquivo fica como esta
- xfce4-terminal e GNOME Terminal: cada chave volta ao valor que a receita 60
  guardou como o de antes, ou sai se nao existia; a chave que outro programa
  mudou depois do projeto (o bigsur, por exemplo) fica como esta. Instalacao
  de antes desse registro: o XML guardado antes do projeto, ou o padrao
- marcas de etapa aplicada: limpas, e a pagina volta a oferecer a instalacao

O ble.sh, o oh-my-posh, os temas e as fontes ficam instalados: nao mudam nada
sozinhos e aplicar de novo fica rapido. Com apagar=True uma etapa a mais remove
o que o projeto instalou, e so isso: os pacotes vem do registro que o motor
escreve a cada apt (sem registro, do historico do apt, so pacotes das receitas),
e os arquivos, do registro das receitas 20, 30, 40 e 50 (sem registro, do log).
As dependencias que o apt trouxe so por esses pacotes saem junto. Pacote que
levaria outros programas junto (fora os que tambem saem) fica. Por ultimo saem
as pastas do projeto: opcoes, log e copias de seguranca.
"""

from __future__ import annotations

import getpass
import gzip
import os
import pwd
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable

from . import NOME, caminhos, estado, receitas, sistema

Diz = Callable[[str], None]

SHELL_ORIGINAL = caminhos.ESTADO_DIR / "shell-original"
# escritos pela receita 60: o valor de antes e o que o projeto escreveu
XFCE_ORIGINAL = caminhos.ESTADO_DIR / "xfce4-terminal-original"
XFCE_APLICADO = caminhos.ESTADO_DIR / "xfce4-terminal-aplicado"
GNOME_ORIGINAL = caminhos.ESTADO_DIR / "gnome-terminal-original"
GNOME_APLICADO = caminhos.ESTADO_DIR / "gnome-terminal-aplicado"
XML_XFCE = Path.home() / ".config/xfce4/xfconf/xfce-perchannel-xml/xfce4-terminal.xml"
PACOTES_INSTALADOS = caminhos.ESTADO_DIR / "pacotes-instalados"   # escrito pelo motor
ARQUIVOS_CRIADOS = caminhos.ESTADO_DIR / "arquivos-criados"       # escrito pelas receitas

# o que a receita 60 mexe, com o tipo; so isso volta, o resto do terminal fica como esta
PROPRIEDADES_XFCE = {"font-use-system": "bool", "font-name": "string", "background-mode": "string",
                     "scrolling-bar": "string", "color-use-theme": "bool", "color-foreground": "string",
                     "color-background": "string", "color-cursor": "string",
                     "color-bold-use-default": "bool", "color-palette": "string",
                     "background-darkness": "double"}
CHAVES_GNOME = ["use-system-font", "font", "use-theme-colors", "foreground-color",
                "background-color", "palette", "use-transparent-background",
                "background-transparency-percent"]

ETAPAS = [
    ("d1", "Shell do login"),
    ("d2", "Arquivos do bash e do fastfetch"),
    ("d3", "Blocos no .bashrc e no gtk.css"),
    ("d4", "Fonte e cores do terminal"),
    ("d5", "Etapas marcadas como aplicadas"),
]
ETAPA_APAGAR = ("d6", "Remover o que foi instalado")


def etapas(apagar: bool = False) -> list[tuple[str, str]]:
    return ETAPAS + ([ETAPA_APAGAR] if apagar else [])


def _rodar(argumentos: list[str], diz: Diz) -> int:
    estado.registrar("+ " + " ".join(argumentos))
    try:
        proc = subprocess.run(argumentos, capture_output=True, text=True)
    except OSError as erro:
        diz(f"  nao consegui executar {argumentos[0]}: {erro}")
        return 1
    if proc.returncode != 0:
        for linha in (proc.stderr or "").splitlines()[-4:]:
            diz("  " + linha)
    return proc.returncode


def _shell(diz: Diz) -> None:
    if not SHELL_ORIGINAL.is_file():
        diz("  sem registro do shell de antes; o do login fica como esta")
        return
    original = SHELL_ORIGINAL.read_text().strip() or "/bin/bash"
    # o arquivo fica numa pasta do usuario e vai para um chsh como root: so um
    # shell de verdade, da lista do sistema e do root
    try:
        validos = Path("/etc/shells").read_text().split()
    except OSError:
        validos = []
    if not (original.startswith("/") and original in validos and os.access(original, os.X_OK)
            and os.stat(original).st_uid == 0):
        diz(f"  atencao: shell guardado invalido ({original or 'vazio'}); volta para /bin/bash")
        original = "/bin/bash"
    usuario = getpass.getuser()
    atual = pwd.getpwnam(usuario).pw_shell
    if atual == original:
        diz(f"  o shell do login ja e {original}")
        return
    if _rodar(["sudo", "-n", "chsh", "-s", original, usuario], diz) != 0:
        raise RuntimeError(f"nao consegui voltar o shell para {original}; rode: chsh -s {original}")
    diz(f"  shell do login de volta para {original}; vale depois de sair e entrar na sessao")


def _arquivos(diz: Diz) -> None:
    for arquivo in sorted((Path.home() / ".config/bash/conf.d").glob(f"{NOME}-*.bash")):
        arquivo.unlink(missing_ok=True)
        diz(f"  apagado {arquivo}")
    presets = Path.home() / ".local/share/fastfetch/presets/d3bian"
    if irmaos_em_uso():
        # os outros projetos da familia apontam para os mesmos presets
        diz(f"  {presets} fica: outro projeto d3bian-init ainda usa")
    elif presets.is_dir():
        shutil.rmtree(presets, ignore_errors=True)
        diz(f"  apagado {presets}")
    # as pastas que o projeto criou so para guardar isso nao precisam ficar
    for pasta in (presets.parent, presets.parent.parent,
                  Path.home() / ".config/bash/conf.d", Path.home() / ".config/bash"):
        try:
            pasta.rmdir()
        except OSError:
            break
        diz(f"  pasta vazia {pasta} apagada")


def tirar_bloco(arquivo: Path, marca: str, comentario: str) -> bool:
    """Tira o trecho que o passo bloco do motor escreveu, com as mesmas marcas."""
    if not arquivo.is_file():
        return False
    abre, fecha = (f"# {marca}", f"# fim {marca}") if comentario == "#" else (f"/* {marca} */", f"/* fim {marca} */")
    texto = arquivo.read_text()
    # marcas na linha inteira, como no motor: uma marca pode ser o comeco de outra
    novo = re.sub(r"\n*^" + re.escape(abre) + r"$.*?^" + re.escape(fecha) + r"$\n?", "\n", texto,
                  flags=re.S | re.M)
    if novo == texto:
        return False
    # o bloco tira os espacos do fim do arquivo ao entrar; se o resto nao mudou
    # desde a copia de antes, volta a copia, igual byte a byte
    guardado = caminhos.BACKUP / str(arquivo).lstrip("/")
    antes = guardado.read_text(errors="replace") if guardado.is_file() else None
    if antes is not None and re.search(r"^" + re.escape(abre) + r"$", antes, re.M):
        # copia feita num Aplicar depois da instalacao, com o bloco ja dentro: o
        # arquivo nao existia antes do projeto
        antes = None
    if antes is not None and antes.rstrip() == novo.rstrip():
        caminhos.escrever(arquivo, antes)
    elif antes is None and not novo.strip():
        # nao existia antes do projeto e so tinha o bloco
        arquivo.unlink()
    else:
        estado.copia_de_seguranca(arquivo)
        caminhos.escrever(arquivo, novo.rstrip("\n") + "\n")
    return True


def _blocos(diz: Diz) -> None:
    bashrc = Path.home() / ".bashrc"
    gtk = Path.home() / ".config/gtk-3.0/gtk.css"
    for arquivo, marca, comentario in ((bashrc, NOME, "#"), (gtk, f"{NOME} margem", "css")):
        if tirar_bloco(arquivo, marca, comentario):
            diz(f"  bloco '{marca}' tirado de {arquivo}")


def _xfce_original() -> dict[str, tuple[str, str]] | None:
    """Propriedades do XML guardado antes do projeto: nome -> (tipo, valor)."""
    guardado = caminhos.BACKUP / str(XML_XFCE).lstrip("/")
    if not guardado.is_file():
        return None
    try:
        raiz = ET.parse(guardado).getroot()
    except ET.ParseError:
        return None
    return {p.get("name", ""): (p.get("type", "string"), p.get("value", ""))
            for p in raiz.findall("property")}


def _guardado(arquivo: Path) -> dict[str, str | None]:
    """Linhas "chave<TAB>valor" da receita 60; None quando a chave nao existia."""
    if not arquivo.is_file():
        return {}
    guardado: dict[str, str | None] = {}
    for linha in arquivo.read_text().splitlines():
        chave, tab, valor = linha.partition("\t")
        if chave:
            guardado[chave] = valor if tab else None
    return guardado


def _ler(argumentos: list[str]) -> str | None:
    """Valor de agora, como a receita 60 le; None quando a chave nao existe."""
    proc = subprocess.run(argumentos, capture_output=True, text=True, env={**os.environ, "LC_ALL": "C"})
    return proc.stdout.rstrip("\n") if proc.returncode == 0 else None


def _cores(diz: Diz) -> None:
    if shutil.which("xfconf-query"):
        original, escrito = _guardado(XFCE_ORIGINAL), _guardado(XFCE_APLICADO)
        xml = _xfce_original()                     # instalacao de antes do registro
        if not original and xml is None:
            diz("  sem copia do xfce4-terminal de antes; as propriedades voltam ao padrao")
        mantidas = []
        for nome, tipo in PROPRIEDADES_XFCE.items():
            base = ["xfconf-query", "-c", "xfce4-terminal", "-p", f"/{nome}"]
            if nome in escrito and _ler(base) != escrito[nome]:
                mantidas.append(nome)              # outro programa mudou depois do projeto
                continue
            if nome in original:
                valor = original[nome]
            elif xml and nome in xml:
                tipo, valor = xml[nome]
            else:
                valor = None
            # o tipo pode ter mudado; remove antes de criar de novo
            subprocess.run([*base, "-r"], capture_output=True)
            if valor is not None:
                _rodar([*base, "-n", "-t", tipo, "-s", valor], diz)
        if mantidas:
            diz("  mudadas por outro programa depois do projeto, ficam como estao: " + ", ".join(mantidas))
        diz("  xfce4-terminal com a fonte e as cores de antes")

    if shutil.which("gnome-terminal") and shutil.which("gsettings"):
        perfil = subprocess.run(["gsettings", "get", "org.gnome.Terminal.ProfilesList", "default"],
                                capture_output=True, text=True).stdout.strip().strip("'")
        if perfil:
            esquema = f"org.gnome.Terminal.Legacy.Profile:/org/gnome/terminal/legacy/profiles:/:{perfil}/"
            original, escrito = _guardado(GNOME_ORIGINAL), _guardado(GNOME_APLICADO)
            mantidas = []
            for chave in CHAVES_GNOME:
                if chave in escrito and _ler(["gsettings", "get", esquema, chave]) != escrito[chave]:
                    mantidas.append(chave)
                elif original.get(chave) is not None:
                    _rodar(["gsettings", "set", esquema, chave, original[chave]], diz)
                else:
                    _rodar(["gsettings", "reset", esquema, chave], diz)
            if mantidas:
                diz("  mudadas por outro programa depois do projeto, ficam como estao: " + ", ".join(mantidas))
            diz("  GNOME Terminal com a fonte e as cores de antes")

    # a proxima instalacao guarda de novo o que houver entao
    for arquivo in (XFCE_ORIGINAL, XFCE_APLICADO, GNOME_ORIGINAL, GNOME_APLICADO):
        arquivo.unlink(missing_ok=True)


# ---- remover o que foi instalado --------------------------------------------

def _pacotes_das_receitas() -> set[str]:
    nomes = set()
    for receita in receitas.carregar():
        for passo in receita.passos:
            if passo.get("tipo") == "apt":
                nomes |= {n for n in passo.get("pacotes", []) if "@@" not in n}
    return nomes


def _historico_apt() -> list[str]:
    """Antes do registro existir: pacotes que o painel pediu ao apt, pelo historico."""
    usuario = getpass.getuser()
    do_projeto = _pacotes_das_receitas()
    inicio = ""
    try:
        primeira = caminhos.REGISTRO.read_text(errors="replace").split("\n", 1)[0]
        inicio = primeira[1:11] if primeira.startswith("[") else ""
    except OSError:
        pass
    textos = []
    for arquivo in sorted(Path("/var/log/apt").glob("history.log*")):
        try:
            dados = arquivo.read_bytes()
            textos.append((gzip.decompress(dados) if arquivo.suffix == ".gz" else dados).decode(errors="replace"))
        except (OSError, EOFError, gzip.BadGzipFile):
            continue
    achados = set()
    for bloco in "\n\n".join(textos).split("\n\n"):
        data = re.search(r"^Start-Date: (\S+)", bloco, re.M)
        pedido = re.search(r"^Commandline: apt-get (?:-o \S+ )*install -y --no-install-recommends (.+)$", bloco, re.M)
        por = re.search(r"^Requested-By: (\S+) ", bloco, re.M)
        if not (data and pedido and por) or por.group(1) != usuario:
            continue
        if inicio and data.group(1) < inicio:        # antes do primeiro uso do projeto
            continue
        achados |= set(pedido.group(1).split()) & do_projeto
    return sorted(achados)


def _arquivos_do_log() -> list[str]:
    """Antes do registro existir: o que os scripts disseram ter instalado. So a
    saida real vai para o log; a simulacao nao roda os scripts."""
    try:
        texto = caminhos.REGISTRO.read_text(errors="replace")
    except OSError:
        return []
    achados = []
    if re.search(r"^\[[^]]+\]   oh-my-posh \S+ instalado$", texto, re.M):
        achados.append("/usr/local/bin/oh-my-posh")
    achados += re.findall(r"^\[[^]]+\]   \d+ temas em (.+)$", texto, re.M)
    achados += re.findall(r"^\[[^]]+\]   fonte copiada para (.+)$", texto, re.M)
    return achados


def previa_remocao() -> dict:
    """O que a etapa de remover apagaria, sem mexer em nada. A pagina mostra antes."""
    if PACOTES_INSTALADOS.is_file():
        candidatos, origem = sorted(set(PACOTES_INSTALADOS.read_text().split())), "registro"
    else:
        candidatos, origem = _historico_apt(), "historico"
    instalados = {n for n, i in sistema.estado_pacotes(candidatos).items() if i.get("instalado")}
    candidatos = [n for n in candidatos if n in instalados]

    pacotes, ficam = [], []
    irmaos = irmaos_em_uso()
    # shell que alguma conta da maquina usa no login nao sai (ela nao entraria mais)
    shells_em_uso = {Path(u.pw_shell).name for u in pwd.getpwall()}
    for nome in candidatos:
        if nome in shells_em_uso:
            ficam.append({"nome": nome, "motivo": "é o shell do login de alguma conta desta máquina"})
            continue
        if irmaos:
            ficam.append({"nome": nome, "motivo": "outro projeto d3bian-init ainda usa: " + ", ".join(irmaos)})
            continue
        pacotes.append(nome)
    # o que depende de um pacote so segura ele se nao sair junto; repete porque
    # um pacote que fica pode segurar outro
    mudou = True
    while mudou:
        mudou = False
        for nome in list(pacotes):
            simulado = subprocess.run(["apt-get", "-s", "remove", nome], capture_output=True, text=True,
                                      env={**os.environ, "LC_ALL": "C"}).stdout
            levaria = [x for x in re.findall(r"^Remv (\S+)", simulado, re.M)
                       if x != nome and x.split(":")[0] not in pacotes]
            if levaria:
                pacotes.remove(nome)
                ficam.append({"nome": nome, "motivo": "outros programas dependem dele: " + ", ".join(levaria[:6])
                              + ("…" if len(levaria) > 6 else "")})
                mudou = True

    # so o registro feito na hora de criar decide o que apagar; sem ele, o que
    # o log diz que foi instalado so aparece para conferir a mao (a pasta
    # podia ja existir antes do projeto)
    arquivos, conferir = [], []
    if ARQUIVOS_CRIADOS.is_file():
        for item in ARQUIVOS_CRIADOS.read_text().splitlines():
            item = item.strip()
            if not item or item in arquivos or not Path(item).exists():
                continue
            if not _apagavel(Path(item)):
                conferir.append(item)
            elif irmaos and _compartilhado(item):
                ficam.append({"nome": item, "motivo": "outro projeto d3bian-init ainda usa: " + ", ".join(irmaos)})
            else:
                arquivos.append(item)
    else:
        conferir = [i for i in dict.fromkeys(_arquivos_do_log()) if Path(i).exists()]
    pastas = [str(p) for p in (caminhos.CONFIG_DIR, caminhos.DADOS_DIR, caminhos.ESTADO_DIR) if p.exists()]
    return {"pacotes": pacotes, "ficam": ficam, "arquivos": arquivos, "conferir": conferir,
            "pastas_do_projeto": pastas, "origem": origem}


# fora da pasta pessoal, o desfazer (que roda como root ali) so apaga estes; a
# lista de arquivos criados fica numa pasta do usuario e nao decide sozinha o
# que o root apaga
APAGAVEIS_FORA_DE_CASA = {
    "/usr/local/bin/oh-my-posh",
}


# o que outros projetos da familia tambem usam: so sai quando nenhum deles esta aplicado
COMPARTILHADOS = ("/usr/local/bin/oh-my-posh", "/.poshthemes", "/fonts/NerdFonts/",
                  "fish-shell", "/fastfetch/presets/d3bian")


def irmaos_em_uso() -> list[str]:
    """Outros projetos d3bian-init com alguma receita aplicada nesta conta."""
    achados = []
    for pasta in caminhos.ESTADO_DIR.parent.glob("d3bian-init-*"):
        if pasta.name != NOME and (pasta / "aplicado").is_dir() and any((pasta / "aplicado").iterdir()):
            achados.append(pasta.name)
    return sorted(achados)


# pastas de 1o nivel da casa que o projeto cria (os temas do oh-my-posh)
CRIADAS_NA_CASA = {".poshthemes"}


def _apagavel(caminho: Path) -> bool:
    bruto = str(caminho)
    # caminho normalizado e sem "..": a lista fica numa pasta do usuario
    if not caminho.is_absolute() or os.path.normpath(bruto) != bruto:
        return False
    casa = Path.home()
    if caminho.is_relative_to(casa):
        real = Path(os.path.realpath(caminho))
        # nunca a casa inteira nem uma pasta logo abaixo dela (Documentos, .config...)
        if not real.is_relative_to(casa):
            return False
        partes = real.relative_to(casa).parts
        # nunca a casa inteira nem uma pasta logo abaixo dela, exceto as que o
        # proprio projeto cria ali (e que so entram aqui se foram registradas)
        return len(partes) >= 2 or (len(partes) == 1 and partes[0] in CRIADAS_NA_CASA)
    return bruto in APAGAVEIS_FORA_DE_CASA


def _compartilhado(item: str) -> bool:
    return any(marca in item for marca in COMPARTILHADOS)


def _orfas() -> set[str]:
    """Pacotes que o apt autoremove tiraria agora."""
    saida = subprocess.run(["apt-get", "-s", "autoremove"], capture_output=True, text=True,
                           env={**os.environ, "LC_ALL": "C"}).stdout
    return set(re.findall(r"^Remv (\S+)", saida, re.M))


def _remover(diz: Diz) -> None:
    previa = previa_remocao()
    if previa["origem"] == "historico":
        diz("  atencao: instalacao anterior ao registro; pacotes tirados do historico do apt")
    for item in previa["ficam"]:
        diz(f"  atencao: {item['nome']} fica instalado: {item['motivo']}")
    if previa["pacotes"]:
        # o que ja sobrava antes nao e do projeto e fica
        orfas_antes = _orfas()
        diz(f"  desinstalando com apt: {', '.join(previa['pacotes'])}")
        codigo = _rodar(["sudo", "-n", "env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "remove", "-y", *previa["pacotes"]], diz)
        if codigo != 0:
            raise RuntimeError("apt-get remove falhou; nada mais foi apagado")
        novas = sorted(_orfas() - orfas_antes)
        if novas:
            diz(f"  dependencias que so estavam ali pelo projeto: {', '.join(novas)}")
            if _rodar(["sudo", "-n", "env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "remove", "-y", *novas], diz) != 0:
                diz("  atencao: nao consegui tirar as dependencias; sudo apt autoremove limpa depois")

    fontes = False
    for item in previa["conferir"]:
        diz(f"  atencao: confira e apague a mao, se for do projeto: {item}")
    for item in previa["arquivos"]:
        caminho = Path(item)
        if not _apagavel(caminho):
            continue
        if caminho.is_relative_to(Path.home()):
            if caminho.is_dir():
                shutil.rmtree(caminho, ignore_errors=True)
            else:
                caminho.unlink(missing_ok=True)
        elif _rodar(["sudo", "-n", "rm", "-rf", str(caminho)], diz) != 0:
            diz(f"  nao consegui apagar {caminho}")
            continue
        fontes = fontes or "/fonts/" in item
        diz(f"  apagado {item}")
    if fontes:
        # as pastas que so guardavam as Nerd Fonts
        pasta_fontes = Path.home() / ".local/share/fonts/NerdFonts"
        for pasta in (pasta_fontes, pasta_fontes.parent):
            try:
                pasta.rmdir()
            except OSError:
                break
            diz(f"  pasta vazia {pasta} apagada")
        _rodar(["fc-cache", "-f"], diz)

    # por ultimo: o log e as copias de seguranca que as etapas anteriores ainda usaram
    for pasta in previa["pastas_do_projeto"]:
        shutil.rmtree(pasta, ignore_errors=True)
        diz(f"  apagado {pasta}")


def _marcas(diz: Diz) -> None:
    estado.limpar_marcas()
    diz("  a pagina volta a mostrar a instalacao completa")


def executar(diz: Diz = print, apagar: bool = False) -> int:
    """Desfaz tudo, uma etapa por vez. Devolve quantas falharam."""
    try:
        with caminhos.trava():
            return _executar(diz, apagar)
    except caminhos.Ocupado as erro:
        diz(f"  {erro}; espere terminar")
        return 1


def _executar(diz: Diz, apagar: bool) -> int:
    caminhos.preparar()
    passos = dict(zip((i for i, _ in ETAPAS), (_shell, _arquivos, _blocos, _cores, _marcas)))
    passos[ETAPA_APAGAR[0]] = _remover
    falhas = 0
    for ident, titulo in etapas(apagar):
        diz(f"\n==> {ident} {titulo}")
        try:
            passos[ident](diz)
        except Exception as erro:                  # uma etapa nao impede as outras
            diz(f"  ERRO: {erro}")
            estado.registrar(f"desfazer {ident} falhou: {erro!r}")
            falhas += 1
            continue
        diz(f"  concluido: {titulo}")
    return falhas

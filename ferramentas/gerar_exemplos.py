#!/usr/bin/env python3
"""Gera as imagens da Galeria: prompts do Oh My Posh, presets do fastfetch e cores.

Nao roda na maquina de quem usa o painel: e ferramenta de quem mantem o projeto,
e as imagens vao prontas em recursos/web/exemplos. Cada imagem e a saida de
verdade do oh-my-posh ou do fastfetch, passada por um emulador de terminal
pequeno (so o que esses dois programas escrevem), desenhada numa janela em HTML
e fotografada pelo chromium.

    python3 ferramentas/gerar_exemplos.py \\
        --posh ~/bin/oh-my-posh --temas ~/.poshthemes \\
        --fastfetch /usr/bin/fastfetch --fonte FiraCodeNerdFontMono-Regular.ttf

Precisa de chromium e ImageMagick. --apenas prompt|fastfetch|cores refaz so um grupo;
com --so, so os temas ou esquemas citados.
"""

from __future__ import annotations

import argparse
import getpass
import html
import os
import pwd
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import tomllib
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ.parent))
from d3bian_init_bash import projeto  # noqa: E402

EXEMPLOS = RAIZ / "recursos/web/exemplos"
PRESETS = RAIZ / "recursos/arquivos/fastfetch"
COLUNAS = 100


# --------------------------------------------------------------------------
# emulador: grade de celulas, com o pouco de ANSI que os dois programas usam
# --------------------------------------------------------------------------

ESTILO_PADRAO = (None, None, False, False, False, False)   # frente, fundo, negrito, fraco, italico, sublinhado
_SEQ = re.compile(r"\x1b\[([0-9;?]*)([A-Za-z])|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][A-Z0-9]|(.)", re.S)


def _cor256(n: int):
    if n < 16:
        return ("p", n)
    if n < 232:
        n -= 16
        passo = [0, 95, 135, 175, 215, 255]
        return "#%02x%02x%02x" % (passo[n // 36], passo[n // 6 % 6], passo[n % 6])
    cinza = 8 + (n - 232) * 10
    return "#%02x%02x%02x" % (cinza, cinza, cinza)


class Tela:
    def __init__(self, colunas: int = COLUNAS) -> None:
        self.colunas = colunas
        self.linhas: list[list] = [[]]
        self.l = self.c = 0
        self.estilo = list(ESTILO_PADRAO)

    def _linha(self, n: int) -> list:
        while len(self.linhas) <= n:
            self.linhas.append([])
        return self.linhas[n]

    def _por(self, ch: str) -> None:
        largura = 2 if unicodedata.east_asian_width(ch) in "WF" else 1
        if unicodedata.combining(ch) or ch in "​‍️":
            return
        linha = self._linha(self.l)
        while len(linha) < self.c + largura:
            linha.append((" ", tuple(ESTILO_PADRAO)))
        linha[self.c] = (ch, tuple(self.estilo))
        if largura == 2:
            linha[self.c + 1] = ("", tuple(self.estilo))
        self.c += largura

    def _sgr(self, params: str) -> None:
        nums = [int(x) if x else 0 for x in params.split(";")] if params else [0]
        e = self.estilo
        i = 0
        while i < len(nums):
            n = nums[i]
            if n == 0:
                e[:] = ESTILO_PADRAO
            elif n == 1:
                e[2] = True
            elif n == 2:
                e[3] = True
            elif n == 3:
                e[4] = True
            elif n == 4:
                e[5] = True
            elif n == 22:
                e[2] = e[3] = False
            elif n == 23:
                e[4] = False
            elif n == 24:
                e[5] = False
            elif 30 <= n <= 37:
                e[0] = ("p", n - 30)
            elif 90 <= n <= 97:
                e[0] = ("p", n - 90 + 8)
            elif 40 <= n <= 47:
                e[1] = ("p", n - 40)
            elif 100 <= n <= 107:
                e[1] = ("p", n - 100 + 8)
            elif n == 39:
                e[0] = None
            elif n == 49:
                e[1] = None
            elif n in (38, 48) and i + 1 < len(nums):
                alvo = 0 if n == 38 else 1
                if nums[i + 1] == 5 and i + 2 < len(nums):
                    e[alvo] = _cor256(nums[i + 2])
                    i += 2
                elif nums[i + 1] == 2 and i + 4 < len(nums):
                    e[alvo] = "#%02x%02x%02x" % tuple(nums[i + 2:i + 5])
                    i += 4
            i += 1

    def escrever(self, texto: str) -> None:
        for m in _SEQ.finditer(texto):
            ch = m.group(3)
            if ch is None:
                params, final = m.group(1), m.group(2)
                if final is None:
                    continue                    # OSC ou troca de conjunto
                n = int(params) if params and params.isdigit() else 1
                if final == "m":
                    self._sgr(params)
                elif final == "A":
                    self.l = max(0, self.l - n)
                elif final == "B":
                    self.l += n
                elif final == "C":
                    self.c += n
                elif final == "D":
                    self.c = max(0, self.c - n)
                elif final == "G":
                    self.c = n - 1
                elif final == "K":
                    del self._linha(self.l)[self.c:]
                continue
            if ch == "\n":
                self.l += 1
                self.c = 0
            elif ch == "\r":
                self.c = 0
            elif ch == "\t":
                self.c = (self.c // 8 + 1) * 8
            elif ch >= " ":
                self._por(ch)

    def largura(self) -> int:
        return max((len(x) for x in self.linhas), default=0)

    def cursor(self) -> None:
        """Bloco do cursor onde a escrita parou."""
        guardado = list(self.estilo)
        self.estilo = [None, "cursor", False, False, False, False]
        self._por(" ")
        self.c -= 1
        self.estilo = guardado

    def html(self, fundo: str, texto: str, paleta: list[str]) -> str:
        def cor(v, padrao):
            if v is None:
                return padrao
            if v == "cursor":
                return texto
            if isinstance(v, tuple):
                return paleta[v[1]]
            return v

        saida = []
        for linha in self.linhas:
            partes, atual, pedaco = [], None, []
            for ch, est in linha + [(None, None)]:
                if est != atual and pedaco:
                    frente, fundo_c, negrito, fraco, italico, sub = atual
                    css = [f"color:{cor(frente, texto)}"]
                    if fundo_c is not None:
                        css.append(f"background:{cor(fundo_c, fundo)}")
                    if negrito:
                        css.append("font-weight:700")
                    if fraco:
                        css.append("opacity:.6")
                    if italico:
                        css.append("font-style:italic")
                    if sub:
                        css.append("text-decoration:underline")
                    partes.append(f'<span style="{";".join(css)}">{html.escape("".join(pedaco))}</span>')
                    pedaco = []
                atual = est
                if ch is not None:
                    pedaco.append(ch)
            saida.append("<div>" + "".join(partes) + "</div>")
        # sem quebra entre as linhas: dentro de white-space:pre ela vira linha em branco
        return "".join(saida)


# --------------------------------------------------------------------------
# janela e fotografia
# --------------------------------------------------------------------------

JANELA = """<!doctype html><meta charset="utf-8"><style>
@font-face{{font-family:Nerd;src:url("file://{fonte}")}}
html,body{{margin:0;background:#ff00ff}}
.jan{{display:inline-block;margin:0;background:{fundo};border-radius:9px;overflow:hidden}}
.topo{{height:34px;display:flex;align-items:center;gap:8px;padding:0 14px;
  background:{topo};font:600 13px system-ui,sans-serif;color:{texto};position:relative}}
.topo i{{width:12px;height:12px;border-radius:50%;display:block}}
.topo b{{position:absolute;left:0;right:0;text-align:center;font-weight:600;opacity:.75;pointer-events:none}}
.tela{{padding:12px 16px 16px;font:15px/1.3 Nerd,monospace;color:{texto};white-space:pre;
  font-variant-ligatures:none;min-width:{largura}ch}}
.tela div{{height:1.3em}}
</style>
<div class="jan"><div class="topo"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i><i style="background:#28c840"></i><b>{titulo}</b></div>
<div class="tela">{corpo}</div></div>"""


def misturar(a: str, b: str, t: float) -> str:
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))


def fotografar(tela: Tela, esquema: str, titulo: str, destino: Path, fonte: Path) -> None:
    fundo, texto, paleta = projeto.CORES[esquema]
    pagina = JANELA.format(fonte=fonte, fundo=fundo, texto=texto, titulo=html.escape(titulo),
                           topo=misturar(fundo, texto, .08), largura=max(tela.largura(), 60),
                           corpo=tela.html(fundo, texto, paleta))
    with tempfile.TemporaryDirectory() as tmp:
        arq = Path(tmp) / "j.html"
        arq.write_text(pagina)
        png = Path(tmp) / "j.png"
        altura = 34 + 28 + int(len(tela.linhas) * 15 * 1.3 * 1.5) + 60
        subprocess.run(["chromium", "--headless=new", "--no-sandbox", "--disable-gpu",
                        "--hide-scrollbars", "--force-device-scale-factor=1.5",
                        f"--window-size=1200,{max(altura, 300)}", f"--screenshot={png}",
                        f"file://{arq}"], capture_output=True, timeout=90, check=True)
        destino.parent.mkdir(parents=True, exist_ok=True)
        # o magenta de fora da janela sai no trim; a janela fica com cantos transparentes
        subprocess.run(["convert", str(png), "-fuzz", "8%", "-transparent", "#ff00ff", "-trim",
                        "+repage", "-resize", "1000x>", "-strip", "-colors", "192",
                        f"PNG8:{destino}"], check=True)
    print(f"  {destino.name}  {destino.stat().st_size // 1024} KB")


# --------------------------------------------------------------------------
# o que vai dentro de cada janela
# --------------------------------------------------------------------------

class Ambiente:
    def __init__(self, args) -> None:
        self.args = args
        self.tmp = Path(tempfile.mkdtemp(prefix="galeria-"))
        self.casa = self.tmp / "casa"
        self.repo = self.casa / "Projetos/meu-app"
        self.repo.mkdir(parents=True)
        (self.repo / "app.py").write_text("print('ola')\n")
        (self.repo / "README.md").write_text("# meu-app\n")
        git = ["git", "-C", str(self.repo), "-c", "user.name=d3bian", "-c", "user.email=d3bian@local"]
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True)
        subprocess.run([*git, "add", "."], check=True)
        subprocess.run([*git, "commit", "-qm", "inicio"], check=True)
        (self.repo / "app.py").write_text("print('ola, mundo')\n")
        (self.repo / "tela.py").write_text("")

    def posh(self, tema: str, qual: str, **extra) -> str:
        args = [self.args.posh, "print", qual, "--config", str(self.args.temas / f"{tema}.omp.json"),
                "--shell", "bash", "--escape=false", "--terminal-width", str(COLUNAS),
                "--pwd", str(self.repo)]
        for chave, valor in extra.items():
            args += [f"--{chave.replace('_', '-')}", str(valor)]
        # rodando de um shell que ja carrega o oh-my-posh, as variaveis POSH_* da
        # sessao fazem ele usar a configuracao guardada e ignorar o --config
        env = {c: v for c, v in os.environ.items() if not c.upper().startswith("POSH")}
        env["HOME"] = str(self.casa)
        return self.ficticio(subprocess.run(args, capture_output=True, text=True, errors="replace",
                                            env=env, cwd=self.repo, timeout=30).stdout)

    def prompt(self, tela: Tela, tema: str, comando: str = "", **extra) -> None:
        tela.escrever(self.posh(tema, "primary", **extra))
        direita = self.posh(tema, "right", **extra)
        if direita.strip():
            medida = Tela(10_000)
            medida.escrever(direita)
            l, c = tela.l, tela.c
            tela.c = COLUNAS - medida.largura()
            tela.escrever(direita)
            tela.l, tela.c = l, c
        tela.estilo = list(ESTILO_PADRAO)
        tela.escrever(comando)

    def preset(self, nome: str) -> Path:
        """exemplo-N vem do pacote do fastfetch; o resto, de recursos/arquivos/fastfetch."""
        if nome.startswith("exemplo-"):
            return self.args.exemplos / f"{nome.removeprefix('exemplo-')}.jsonc"
        return PRESETS / f"{nome}.jsonc"

    def fastfetch(self, nome: str) -> str:
        env = {**os.environ, "HOME": str(Path.home())}
        if self.args.fastfetch_lib:
            env["LD_LIBRARY_PATH"] = self.args.fastfetch_lib
        # os presets apontam para ~/.local/share/fastfetch/presets/d3bian; aqui, para a copia do projeto
        alvo = self.tmp / f"{nome}.jsonc"
        alvo.write_text(self.preset(nome).read_text()
                        .replace("~/.local/share/fastfetch/presets/d3bian", str(PRESETS)))
        saida = subprocess.run([self.args.fastfetch, "--config", str(alvo), "--pipe", "false"],
                               capture_output=True, text=True, errors="replace", env=env, timeout=60).stdout
        # o nome vem colado ao escape (\x1b[mclaude), por isso lookbehind e nao \b
        # quem chama e o gerador, nao um terminal: troca pelo que a pessoa vai ver, e esconde o IP
        saida = re.sub(r"(?:(?<=m)|(?<![A-Za-z]))python3(?:\.\d+)*(?: [\d.]+)?", "bash 5.2.37", saida)
        saida = re.sub(r"(?:(?<=m)|(?<![A-Za-z]))claude(?: [\d.]+)?", "xfce4-terminal 1.1.4", saida)
        # IP publico e IPv6 tambem, e a cidade que o fastfetch tira do IP
        saida = re.sub(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])", "192.168.0.10", saida)
        saida = re.sub(r"(?:(?<=m)|(?<![0-9A-Za-z:]))[0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{0,4}){3,7}(?![0-9A-Za-z:])", "fd00::10", saida)
        saida = re.sub(r"([\[(])[^()\[\]\x1b]*, ([A-Z]{2}[\])])", r"\1Cidade, \2", saida)
        return self.ficticio(self.sem_midia(saida))

    def sem_midia(self, texto: str) -> str:
        """O que esta tocando e o player mudam durante a geracao: le de novo a cada
        preset e, por garantia, troca o titulo de qualquer linha com (Playing)."""
        env = {**os.environ}
        if self.args.fastfetch_lib:
            env["LD_LIBRARY_PATH"] = self.args.fastfetch_lib
        agora = subprocess.run(
            [self.args.fastfetch, "--pipe", "true", "--logo", "none", "--structure", "media:player"],
            capture_output=True, text=True, errors="replace", env=env, timeout=60).stdout
        # o rotulo muda conforme a versao e o player; vale o valor de cada linha
        for linha in agora.splitlines():
            rotulo, _, valor = linha.partition(": ")
            valor = re.sub(r" \((?:Playing|Paused|Stopped)\)$", "", valor).strip()
            if len(valor) >= 3:
                falso = "Lofi Girl - lofi hip hop radio" if "media" in rotulo.lower() else "Spotify"
                texto = texto.replace(valor, falso)
        linhas = []
        for linha in texto.split("\n"):
            estado_midia = re.search(r"\((?:Playing|Paused|Stopped)\)", linha)
            if estado_midia and "Lofi Girl" not in linha:
                antes = linha[:estado_midia.start()]
                # o titulo comeca depois do ultimo escape ou separador da linha
                cortes = [e.end() for e in re.finditer(r"\x1b\[[0-9;]*m", antes)]
                cortes += [antes.rfind(s) + len(s) for s in ("-> ", "➜ ", "› ", "> ", "• ", ": ") if s in antes]
                corte = max(cortes, default=0)
                linha = antes[:corte] + "Lofi Girl - lofi hip hop radio " + linha[estado_midia.start():]
            linhas.append(linha)
        return "\n".join(linhas)

    def trocas(self) -> list[tuple[re.Pattern, str]]:
        """Dados reais de quem gera as imagens, cada um com um ficticio no lugar.

        Lidos desta maquina, e nao escritos aqui, para valer em qualquer uma: o
        usuario, o nome da maquina, o modelo, o processador, o video, o fone, o
        papel de parede, a BIOS e o que estiver tocando.
        """
        if hasattr(self, "_trocas"):
            return self._trocas
        texto = ""
        if self.args.fastfetch:
            env = {**os.environ}
            if self.args.fastfetch_lib:
                env["LD_LIBRARY_PATH"] = self.args.fastfetch_lib
            texto = subprocess.run(
                [self.args.fastfetch, "--pipe", "true", "--logo", "none", "--structure",
                 "host:cpu:gpu:media:sound:wallpaper:bluetooth:bios"],
                capture_output=True, text=True, errors="replace", env=env, timeout=60).stdout

        def campo(padrao: str) -> str:
            m = re.search(padrao, texto, re.M)
            return m.group(1).strip() if m else ""

        def dmi(nome: str) -> str:
            try:
                return Path(f"/sys/class/dmi/id/{nome}").read_text(errors="replace").strip()
            except OSError:
                return ""

        gpu = campo(r"^GPU[^:]*: (.+?)(?: @| \[|$)")
        # parte das capturas mostra o video sem o fabricante na frente
        gpu_curta = gpu.split(" ", 1)[1] if gpu.split(" ", 1)[0] in ("Intel", "AMD", "NVIDIA") and " " in gpu else ""
        pares = [
            (dmi("sys_vendor"), "Fabricante Exemplo"),
            (dmi("product_name"), "Notebook X14"),
            (campo(r"^CPU[^:]*: (.+?) \(\d+\)"), "Intel(R) Core(TM) i5-1235U"),
            (gpu, "Intel Iris Xe Graphics"),
            (gpu_curta, "Iris Xe Graphics"),
            (campo(r"^Sound[^:]*: (.+?) \(\d+%\)"), "Fone Bluetooth"),
            (campo(r"^Bluetooth[^:]*: (.+?) \(\d+%\)"), "Fone Bluetooth"),
            (campo(r"^Wallpaper[^:]*: (.+)$"), "debian-13.png"),
            (campo(r"^Bios[^:]*: (.+?)(?: \([\d.]+\))?$"), "1.0.0"),
            (campo(r"^Media[^:]*: (.+?)(?: \((?:Playing|Paused|Stopped)\))?$"), "Lofi Girl - lofi hip hop radio"),
            (pwd.getpwuid(os.getuid()).pw_gecos.split(",")[0], "Usuario Linux"),
            (socket.gethostname(), "debian"),
            (getpass.getuser(), "linux"),
        ]
        vistos, self._trocas = set(), []
        # o mais longo primeiro: o modelo contem o nome da maquina, e o nome completo o usuario
        for real, falso in sorted(pares, key=lambda x: -len(x[0])):
            if len(real) < 3 or "O.E.M" in real or real in vistos:
                continue
            vistos.add(real)
            # espacos especiais viram \ufffd na leitura; qualquer separador curto casa
            palavras = [re.escape(x) for x in re.split(r"[^A-Za-z0-9]+", real) if x]
            if palavras:
                self._trocas.append((re.compile(r"[^A-Za-z0-9\x1b]{0,3}".join(palavras)), falso))
        return self._trocas

    def ficticio(self, texto: str) -> str:
        for padrao, falso in self.trocas():
            texto = padrao.sub(falso, texto)
        return re.sub(r"PID:\s*\d+", "PID:1234", texto)


def opcoes() -> dict[str, dict]:
    dados = tomllib.loads((RAIZ / "recursos/opcoes.toml").read_text())
    return {o["chave"]: o for o in dados["opcao"]}


def gerar_prompts(amb: Ambiente, fonte: Path, temas: list[str]) -> None:
    for tema in temas:
        tela = Tela()
        amb.prompt(tela, tema, "git status -s", execution_time=1530, status=0)
        tela.escrever("\n\x1b[31m M\x1b[0m app.py\n\x1b[31m??\x1b[0m tela.py\n")
        amb.prompt(tela, tema, "", status=0, no_status=True)
        tela.cursor()
        fotografar(tela, "everforest", f"{tema} — bash", EXEMPLOS / f"prompt-{tema}.png", fonte)


def gerar_fastfetch(amb: Ambiente, fonte: Path, presets: list[str], tema: str) -> None:
    for nome in presets:
        tela = Tela()
        amb.prompt(tela, tema, "fastfetch", status=0)
        tela.escrever("\n")
        tela.escrever(amb.fastfetch(nome))
        tela.estilo = list(ESTILO_PADRAO)
        tela.l, tela.c = len(tela.linhas), 0
        amb.prompt(tela, tema, "", status=0)
        tela.cursor()
        fotografar(tela, "everforest", f"fastfetch {nome}", EXEMPLOS / f"fastfetch-{nome}.png", fonte)


def gerar_cores(amb: Ambiente, fonte: Path, tema: str, so: list[str] | None = None) -> None:
    demo = amb.casa / "demo"
    for pasta in ("Documentos", "Imagens", "Projetos"):
        (demo / pasta).mkdir(parents=True, exist_ok=True)
    (demo / "instalar.sh").write_text("#!/bin/sh\n")
    (demo / "instalar.sh").chmod(0o755)
    (demo / "backup.tar.xz").write_text("")
    (demo / "notas.txt").write_text("")
    if not (demo / "atalho").exists():
        (demo / "atalho").symlink_to("notas.txt")
    ls = subprocess.run(["ls", "--color=always", "-C", "-w", "80"], cwd=demo, capture_output=True,
                        text=True, env={**os.environ, "LS_COLORS": ""}).stdout
    # ls sem LS_COLORS nao pinta nada; usa as cores padrao do dircolors
    cores_ls = subprocess.run(["dircolors", "-b"], capture_output=True, text=True).stdout
    m = re.search(r"LS_COLORS='([^']*)'", cores_ls)
    if m:
        ls = subprocess.run(["ls", "--color=always", "-C", "-w", "80"], cwd=demo, capture_output=True,
                            text=True, env={**os.environ, "LS_COLORS": m.group(1)}).stdout
    paleta = "".join(f"\x1b[4{i}m   " for i in range(8)) + "\x1b[0m\n" + \
             "".join(f"\x1b[10{i}m   " for i in range(8)) + "\x1b[0m\n"
    exemplo = ("\x1b[35mdef\x1b[0m \x1b[34mola\x1b[0m(nome):\n"
               "    \x1b[33mreturn\x1b[0m \x1b[32mf\"Olá, {nome}!\"\x1b[0m  \x1b[90m# comentário\x1b[0m\n")
    for esquema in so or projeto.CORES:
        tela = Tela()
        amb.prompt(tela, tema, "ls", status=0)
        tela.escrever("\n" + ls)
        amb.prompt(tela, tema, "bat ola.py", status=0)
        tela.escrever("\n" + exemplo)
        amb.prompt(tela, tema, "cores", status=0)
        tela.escrever("\n" + paleta)
        amb.prompt(tela, tema, "", status=0)
        tela.cursor()
        nome = opcoes()["cores"]["nomes"][esquema]
        fotografar(tela, esquema, nome, EXEMPLOS / f"cores-{esquema}.png", fonte)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--posh", default=shutil.which("oh-my-posh"))
    p.add_argument("--temas", type=Path, default=Path.home() / ".poshthemes")
    p.add_argument("--fastfetch", default=shutil.which("fastfetch"))
    p.add_argument("--fastfetch-lib", help="LD_LIBRARY_PATH para um fastfetch extraido de .deb")
    p.add_argument("--exemplos", type=Path, default=Path("/usr/share/fastfetch/presets/examples"),
                   help="pasta dos exemplos que vem com o fastfetch")
    p.add_argument("--fonte", type=Path, required=True, help="arquivo .ttf de uma Nerd Font Mono")
    p.add_argument("--apenas", choices=["prompt", "fastfetch", "cores"])
    p.add_argument("--temas-extra", nargs="*", default=[], help="gerar tambem estes temas")
    p.add_argument("--so", nargs="*", default=[], help="com --apenas prompt ou cores, so estes temas ou esquemas")
    args = p.parse_args()

    amb = Ambiente(args)
    ops = opcoes()
    tema_padrao = ops["tema_posh"]["padrao"]
    try:
        if args.apenas in (None, "prompt"):
            gerar_prompts(amb, args.fonte.resolve(), args.so or ops["tema_posh"]["valores"] + args.temas_extra)
        if args.apenas in (None, "fastfetch"):
            gerar_fastfetch(amb, args.fonte.resolve(),
                            [v for v in ops["fastfetch"]["valores"] if v != "nenhum"], tema_padrao)
        if args.apenas in (None, "cores"):
            gerar_cores(amb, args.fonte.resolve(), tema_padrao, args.so if args.apenas == "cores" else None)
    finally:
        shutil.rmtree(amb.tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

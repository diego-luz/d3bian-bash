"""O que e proprio deste projeto e nao cabe numa receita.

- contexto(cfg): valores calculados a partir das opcoes, que as receitas usam
  como @@chave@@ (e os scripts como $CTX_*).
- verificacoes(add): checagens previas alem das comuns do sistema.py.
"""

from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import Callable

# opcao -> (arquivo do release das Nerd Fonts, familia mono que o fontconfig mostra)
FONTES = {
    "firacode": ("FiraCode", "FiraCode Nerd Font Mono"),
    "jetbrainsmono": ("JetBrainsMono", "JetBrainsMono Nerd Font Mono"),
    "hack": ("Hack", "Hack Nerd Font Mono"),
    "meslo": ("Meslo", "MesloLGS Nerd Font Mono"),
    "cascadia": ("CascadiaCode", "CaskaydiaCove Nerd Font Mono"),
}

# opcao -> (fundo, texto, 16 cores: as 8 normais e depois as 8 claras)
CORES = {
    "everforest": ("#1E2326", "#D3C6AA", [
        "#7A8478", "#E67E80", "#A7C080", "#DBBC7F", "#7FBBB3", "#D699B6", "#83C092", "#F2EFDF",
        "#A6B0A0", "#F85552", "#8DA101", "#DFA000", "#3A94C5", "#DF69BA", "#35A77C", "#FFFBEF"]),
    "catppuccin": ("#1E1E2E", "#CDD6F4", [
        "#45475A", "#F38BA8", "#A6E3A1", "#F9E2AF", "#89B4FA", "#F5C2E7", "#94E2D5", "#BAC2DE",
        "#585B70", "#F38BA8", "#A6E3A1", "#F9E2AF", "#89B4FA", "#F5C2E7", "#94E2D5", "#A6ADC8"]),
    "dracula": ("#282A36", "#F8F8F2", [
        "#21222C", "#FF5555", "#50FA7B", "#F1FA8C", "#BD93F9", "#FF79C6", "#8BE9FD", "#F8F8F2",
        "#6272A4", "#FF6E6E", "#69FF94", "#FFFFA5", "#D6ACFF", "#FF92DF", "#A4FFFF", "#FFFFFF"]),
    "nord": ("#2E3440", "#D8DEE9", [
        "#3B4252", "#BF616A", "#A3BE8C", "#EBCB8B", "#81A1C1", "#B48EAD", "#88C0D0", "#E5E9F0",
        "#4C566A", "#BF616A", "#A3BE8C", "#EBCB8B", "#81A1C1", "#B48EAD", "#8FBCBB", "#ECEFF4"]),
    "gruvbox": ("#282828", "#EBDBB2", [
        "#282828", "#CC241D", "#98971A", "#D79921", "#458588", "#B16286", "#689D6A", "#A89984",
        "#928374", "#FB4934", "#B8BB26", "#FABD2F", "#83A598", "#D3869B", "#8EC07C", "#EBDBB2"]),
    # minimalistas: pouco contraste entre as cores e fundo sem brilho
    "rosepine": ("#191724", "#E0DEF4", [
        "#26233A", "#EB6F92", "#31748F", "#F6C177", "#9CCFD8", "#C4A7E7", "#EBBCBA", "#E0DEF4",
        "#6E6A86", "#EB6F92", "#31748F", "#F6C177", "#9CCFD8", "#C4A7E7", "#EBBCBA", "#E0DEF4"]),
    "kanagawa": ("#1F1F28", "#DCD7BA", [
        "#16161D", "#C34043", "#76946A", "#C0A36E", "#7E9CD8", "#957FB8", "#6A9589", "#C8C093",
        "#727169", "#E82424", "#98BB6C", "#E6C384", "#7FB4CA", "#938AA9", "#7AA89F", "#DCD7BA"]),
    "onedark": ("#282C34", "#ABB2BF", [
        "#282C34", "#E06C75", "#98C379", "#E5C07B", "#61AFEF", "#C678DD", "#56B6C2", "#ABB2BF",
        "#5C6370", "#E06C75", "#98C379", "#E5C07B", "#61AFEF", "#C678DD", "#56B6C2", "#FFFFFF"]),
    "solarized": ("#002B36", "#839496", [
        "#073642", "#DC322F", "#859900", "#B58900", "#268BD2", "#D33682", "#2AA198", "#EEE8D5",
        "#002B36", "#CB4B16", "#586E75", "#657B83", "#839496", "#6C71C4", "#93A1A1", "#FDF6E3"]),
    "tokyonight": ("#1A1B26", "#C0CAF5", [
        "#15161E", "#F7768E", "#9ECE6A", "#E0AF68", "#7AA2F7", "#BB9AF7", "#7DCFFF", "#A9B1D6",
        "#414868", "#F7768E", "#9ECE6A", "#E0AF68", "#7AA2F7", "#BB9AF7", "#7DCFFF", "#C0CAF5"]),
    # vindos do iTerm2-Color-Schemes (pasta windowsterminal), com o nome do arquivo ao lado
    "everforest_medio": ("#232A2E", "#D3C6AA", [  # Everforest Dark Med
        "#7A8478", "#E67E80", "#A7C080", "#DBBC7F", "#7FBBB3", "#D699B6", "#83C092", "#F2EFDF",
        "#A6B0A0", "#F85552", "#8DA101", "#DFA000", "#3A94C5", "#DF69BA", "#35A77C", "#FFFBEF"]),
    "everforest_claro": ("#EFEBD4", "#5C6A72", [  # Everforest Light Med
        "#7A8478", "#E67E80", "#9AB373", "#C1A266", "#7FBBB3", "#D699B6", "#83C092", "#B2AF9F",
        "#A6B0A0", "#F85552", "#8DA101", "#DFA000", "#3A94C5", "#DF69BA", "#35A77C", "#FFFBEF"]),
    "catppuccin_macchiato": ("#24273A", "#CAD3F5", [  # Catppuccin Macchiato
        "#494D64", "#ED8796", "#A6DA95", "#EED49F", "#8AADF4", "#F5BDE6", "#8BD5CA", "#B8C0E0",
        "#5B6078", "#F2A7B2", "#BDE3B0", "#F4E3C1", "#ADC5F7", "#F493DA", "#A5DED6", "#A5ADCB"]),
    "catppuccin_frappe": ("#303446", "#C6D0F5", [  # Catppuccin Frappe
        "#51576D", "#E78284", "#A6D189", "#E5C890", "#8CAAEE", "#F4B8E4", "#81C8BE", "#B5BFE2",
        "#626880", "#EDA0A2", "#B9DBA2", "#ECD7AE", "#ADC2F3", "#F38ED8", "#98D2CA", "#A5ADCE"]),
    "catppuccin_latte": ("#EFF1F5", "#4C4F69", [  # Catppuccin Latte
        "#BCC0CC", "#D20F39", "#40A02B", "#DF8E1D", "#1E66F5", "#EA76CB", "#179299", "#5C5F77",
        "#ACB0BE", "#E7103F", "#46B02F", "#E49931", "#3878F6", "#EF95D7", "#19A1A8", "#6C6F85"]),
    "gruvbox_material": ("#282828", "#D4BE98", [  # Gruvbox Material Dark
        "#282828", "#EA6962", "#A9B665", "#D8A657", "#7DAEA3", "#D3869B", "#89B482", "#D4BE98",
        "#7C6F64", "#EA6962", "#A9B665", "#D8A657", "#7DAEA3", "#D3869B", "#89B482", "#DDC7A1"]),
    "gruvbox_claro": ("#FBF1C7", "#3C3836", [  # Gruvbox Light
        "#FBF1C7", "#CC241D", "#98971A", "#D79921", "#458588", "#B16286", "#689D6A", "#7C6F64",
        "#928374", "#9D0006", "#79740E", "#B57614", "#076678", "#8F3F71", "#427B58", "#3C3836"]),
    "tokyonight_storm": ("#24283B", "#C0CAF5", [  # TokyoNight Storm
        "#1D202F", "#F7768E", "#9ECE6A", "#E0AF68", "#7AA2F7", "#BB9AF7", "#7DCFFF", "#A9B1D6",
        "#4E5575", "#F7768E", "#9ECE6A", "#E0AF68", "#7AA2F7", "#BB9AF7", "#7DCFFF", "#C0CAF5"]),
    "tokyonight_day": ("#E1E2E7", "#3760BF", [  # TokyoNight Day
        "#E9E9ED", "#F52A65", "#587539", "#8C6C3E", "#2E7DE9", "#9854F1", "#007197", "#6172B0",
        "#A1A6C5", "#F52A65", "#587539", "#8C6C3E", "#2E7DE9", "#9854F1", "#007197", "#3760BF"]),
    "rosepine_moon": ("#232136", "#E0DEF4", [  # Rose Pine Moon
        "#393552", "#EB6F92", "#3E8FB0", "#F6C177", "#9CCFD8", "#C4A7E7", "#EA9A97", "#E0DEF4",
        "#6E6A86", "#EB6F92", "#3E8FB0", "#F6C177", "#9CCFD8", "#C4A7E7", "#EA9A97", "#E0DEF4"]),
    "rosepine_dawn": ("#FAF4ED", "#575279", [  # Rose Pine Dawn
        "#F2E9E1", "#B4637A", "#286983", "#EA9D34", "#56949F", "#907AA9", "#D7827E", "#575279",
        "#9893A5", "#B4637A", "#286983", "#EA9D34", "#56949F", "#907AA9", "#D7827E", "#575279"]),
    "kanagawa_dragon": ("#181616", "#C5C9C5", [  # Kanagawa Dragon
        "#0D0C0C", "#C4746E", "#8A9A7B", "#C4B28A", "#8BA4B0", "#A292A3", "#8EA4A2", "#C8C093",
        "#A6A69C", "#E46876", "#87A987", "#E6C384", "#7FB4CA", "#938AA9", "#7AA89F", "#C5C9C5"]),
    "solarized_claro": ("#FDF6E3", "#657B83", [  # iTerm2 Solarized Light
        "#073642", "#DC322F", "#859900", "#B58900", "#268BD2", "#D33682", "#2AA198", "#BBB5A2",
        "#002B36", "#CB4B16", "#586E75", "#657B83", "#839496", "#6C71C4", "#93A1A1", "#FDF6E3"]),
    "monokai_pro": ("#2D2A2E", "#FCFCFA", [  # Monokai Pro
        "#2D2A2E", "#FF6188", "#A9DC76", "#FFD866", "#FC9867", "#AB9DF2", "#78DCE8", "#FCFCFA",
        "#727072", "#FF6188", "#A9DC76", "#FFD866", "#FC9867", "#AB9DF2", "#78DCE8", "#FCFCFA"]),
    "ayu": ("#0B0E14", "#BFBDB6", [  # Ayu
        "#11151C", "#EA6C73", "#7FD962", "#F9AF4F", "#53BDFA", "#CDA1FA", "#90E1C6", "#C7C7C7",
        "#686868", "#F07178", "#AAD94C", "#FFB454", "#59C2FF", "#D2A6FF", "#95E6CB", "#FFFFFF"]),
    "ayu_mirage": ("#1F2430", "#CCCAC2", [  # Ayu Mirage
        "#171B24", "#ED8274", "#87D96C", "#FACC6E", "#6DCBFA", "#DABAFA", "#90E1C6", "#C7C7C7",
        "#686868", "#F28779", "#D5FF80", "#FFD173", "#73D0FF", "#DFBFFF", "#95E6CB", "#FFFFFF"]),
    "night_owl": ("#011627", "#D6DEEB", [  # Night Owl
        "#011627", "#EF5350", "#22DA6E", "#ADDB67", "#82AAFF", "#C792EA", "#21C7A8", "#FFFFFF",
        "#575656", "#EF5350", "#22DA6E", "#FFEB95", "#82AAFF", "#C792EA", "#7FDBCA", "#FFFFFF"]),
    "material_ocean": ("#0F111A", "#8F93A2", [  # Material Ocean
        "#546E7A", "#FF5370", "#C3E88D", "#FFCB6B", "#82AAFF", "#C792EA", "#89DDFF", "#FFFFFF",
        "#546E7A", "#FF5370", "#C3E88D", "#FFCB6B", "#82AAFF", "#C792EA", "#89DDFF", "#FFFFFF"]),
    "github_dark": ("#0D1117", "#E6EDF3", [  # GitHub Dark Default
        "#484F58", "#FF7B72", "#3FB950", "#D29922", "#58A6FF", "#BC8CFF", "#39C5CF", "#B1BAC4",
        "#6E7681", "#FFA198", "#56D364", "#E3B341", "#79C0FF", "#D2A8FF", "#56D4DD", "#FFFFFF"]),
    "github_claro": ("#FFFFFF", "#1F2328", [  # GitHub Light Default
        "#24292F", "#CF222E", "#116329", "#4D2D00", "#0969DA", "#8250DF", "#1B7C83", "#6E7781",
        "#57606A", "#A40E26", "#1A7F37", "#633C01", "#218BFF", "#A475F9", "#3192AA", "#8C959F"]),
    "nightfox": ("#192330", "#CDCECF", [  # Nightfox
        "#393B44", "#C94F6D", "#81B29A", "#DBC074", "#719CD6", "#9D79D6", "#63CDCF", "#DFDFE0",
        "#575860", "#D16983", "#8EBAA4", "#E0C989", "#86ABDC", "#BAA1E2", "#7AD5D6", "#E4E4E5"]),
    "carbonfox": ("#161616", "#F2F4F8", [  # Carbonfox
        "#282828", "#EE5396", "#25BE6A", "#08BDBA", "#78A9FF", "#BE95FF", "#33B1FF", "#DFDFE0",
        "#484848", "#F16DA6", "#46C880", "#2DC7C4", "#8CB6FF", "#C8A5FF", "#52BDFF", "#E4E4E5"]),
    "oxocarbon": ("#161616", "#F2F4F8", [  # Oxocarbon
        "#161616", "#00DFDB", "#00B4FF", "#FF4297", "#00C15A", "#C693FF", "#FF74B8", "#F2F4F8",
        "#585858", "#00DFDB", "#00B4FF", "#FF4297", "#00C15A", "#C693FF", "#FF74B8", "#F2F4F8"]),
    "sonokai": ("#2C2E34", "#E2E2E3", [  # Sonokai
        "#181819", "#FC5D7C", "#9ED072", "#E7C664", "#76CCE0", "#B39DF3", "#F39660", "#E2E2E3",
        "#7F8490", "#FC5D7C", "#9ED072", "#E7C664", "#76CCE0", "#B39DF3", "#F39660", "#E2E2E3"]),
    "poimandres": ("#1A1E28", "#A6ACCD", [  # Poimandres
        "#1A1E28", "#D0679D", "#5DE4C7", "#FFFAC2", "#89DDFF", "#FCC5E9", "#ADD7FF", "#FFFFFF",
        "#A6ACCD", "#D0679D", "#5DE4C7", "#FFFAC2", "#ADD7FF", "#FAE4FC", "#89DDFF", "#FFFFFF"]),
    "vesper": ("#101010", "#FFFFFF", [  # Vesper
        "#101010", "#F5A191", "#90B99F", "#E6B99D", "#ACA1CF", "#E29ECA", "#EA83A5", "#A0A0A0",
        "#7E7E7E", "#FF8080", "#99FFE4", "#FFC799", "#B9AEDA", "#ECAAD6", "#F591B2", "#FFFFFF"]),
    "iceberg": ("#161821", "#C6C8D1", [  # Iceberg Dark
        "#1E2132", "#E27878", "#B4BE82", "#E2A478", "#84A0C6", "#A093C7", "#89B8C2", "#C6C8D1",
        "#6B7089", "#E98989", "#C0CA8E", "#E9B189", "#91ACD1", "#ADA0D3", "#95C4CE", "#D2D4DE"]),
    "doom_one": ("#282C34", "#BBC2CF", [  # Doom One
        "#000000", "#FF6C6B", "#98BE65", "#ECBE7B", "#A9A1E1", "#C678DD", "#51AFEF", "#BBC2CF",
        "#595959", "#FF6655", "#99BB66", "#ECBE7B", "#A9A1E1", "#C678DD", "#51AFEF", "#BFBFBF"]),
    "ubuntu": ("#300A24", "#EEEEEC", [  # Ubuntu
        "#2E3436", "#CC0000", "#4E9A06", "#C4A000", "#3465A4", "#75507B", "#06989A", "#D3D7CF",
        "#555753", "#EF2929", "#8AE234", "#FCE94F", "#729FCF", "#AD7FA8", "#34E2E2", "#EEEEEC"]),
}

# nome da verificacao que a Galeria e os Ajustes procuram para avisar
FASTFETCH_VERIFICACAO = "Fastfetch no repositorio"
SHELL_VERIFICACAO = "Shell nas janelas novas"

# processos que comecam a sessao grafica; o SHELL deles e o que o terminal herda
SESSOES = ("xfce4-session", "gnome-session-b", "cinnamon-session", "mate-session", "lxqt-session",
           "lxsession", "startplasma-x11", "startplasma-way", "plasma_session")

# opcao transparencia -> opacidade do fundo, em %
OPACIDADE = {"nao": 100, "leve": 92, "media": 85, "forte": 75}

# nome da maquina -> sufixo do binario do oh-my-posh no GitHub
ARQUITETURAS = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64",
                "armv7l": "arm"}


# Downloads com versao fixa e conferidos pelo SHA-256 antes de usar: um
# release trocado ou corrompido no GitHub nao chega a /usr/local/bin. Para
# atualizar, troque a versao e os hashes (os do oh-my-posh e das fontes vem do
# checksums.txt / SHA-256.txt do proprio release; o do themes.zip, calculado).
POSH_VERSAO = "v31.5.0"
POSH_SHA256 = {
    "amd64": "733979ee65c9958da451fec22bda6b8ea4fd7976279bde5386b19069b62e7afe",
    "arm64": "696bf884db57c3a95ec0c7f4e94ea0819d54a5c80c9bdaa46a57ac53178e6a75",
    "arm": "4a8e76d1a787ffc5d06a8b346bf3c7b7ddd38b89583f852954bd75085a81a4f4",
}
POSH_TEMAS_SHA256 = "60869bd08050b2519bd39efe6c1805b7e0375387a0e61ececa78cb607d78dc80"
NERD_VERSAO = "v3.5.1"
NERD_SHA256 = {
    "CascadiaCode": "ae598e9401e2846aa3ee364513715de0490b844a4b54f0768991f45f23aa8369",
    "FiraCode": "68e3bd6164864b8b514605bc34e3a87ac401c8c48682fcce6478c70263340207",
    "Hack": "cdd389472e10e2261520140ff1b382b4f8a226af5fd0b2735b975d31151d9c3c",
    "JetBrainsMono": "04d5e8f903693f9dd13e16f867e994834e681eb3c72c0d337a770dcda09010cf",
    "Meslo": "6b6624632dc6873dfb7681c3f818e7c01ab601ab707690b6440933bbe57e2b11",
}
# ble.sh: nightly com data no nome (o "ble-nightly.tar.xz" sem data muda sem
# aviso); o hash vem do digest do proprio asset no GitHub. Para atualizar, pegue
# o mais novo em github.com/akinomyoga/ble.sh/releases/tag/nightly
BLESH_ARQUIVO = "ble-nightly-20260908+d81fd54.tar.xz"
BLESH_SHA256 = "7a2445f138e7f099dd5dee749391a8b045646d1b8a605975885be5b34b6b5f7e"


def contexto(cfg: dict[str, str]) -> dict[str, str]:
    arquivo, familia = FONTES.get(cfg.get("fonte", ""), FONTES["firacode"])
    # "manter" nao tem paleta; as receitas pulam as cores com se = "cores != manter"
    fundo, texto, paleta = CORES.get(cfg.get("cores", ""), CORES["everforest"])
    opaco = OPACIDADE.get(cfg.get("transparencia", ""), 100)
    return {
        "fonte_arquivo": arquivo,
        "fonte_familia": familia,
        "cor_fundo": fundo,
        "cor_texto": texto,
        "paleta_xfce": ";".join(paleta),
        "paleta_gnome": "[" + ", ".join(f"'{c}'" for c in paleta) + "]",
        # xfce4-terminal e Konsole querem de 0 a 1; o GNOME Terminal, o quanto e transparente
        "opacidade": f"{opaco / 100:.2f}",
        "transparencia_pct": str(100 - opaco),
        "posh_arquitetura": ARQUITETURAS.get(platform.machine().lower(), ""),
        "posh_versao": POSH_VERSAO,
        "posh_sha256": POSH_SHA256.get(ARQUITETURAS.get(platform.machine().lower(), ""), ""),
        "posh_temas_sha256": POSH_TEMAS_SHA256,
        "nerd_versao": NERD_VERSAO,
        "fonte_sha256": NERD_SHA256.get(arquivo, ""),
        "blesh_arquivo": BLESH_ARQUIVO,
        "blesh_sha256": BLESH_SHA256,
        "bash_confd": str(Path.home() / ".config/bash/conf.d"),
        # para receita chamar um modulo do pacote: python3 -m "$CTX_PACOTE.x" com PYTHONPATH
        "pacote": Path(__file__).resolve().parent.name,
        "pacote_pai": str(Path(__file__).resolve().parent.parent),
        **_fastfetch(cfg),
    }


def _fastfetch(cfg: dict[str, str]) -> dict[str, str]:
    """exemplo-N vem no pacote do Debian; o resto sao os presets adaptados do projeto."""
    nome = cfg.get("fastfetch", "nenhum")
    if nome.startswith("exemplo-"):
        caminho = f"/usr/share/fastfetch/presets/examples/{nome.removeprefix('exemplo-')}.jsonc"
    else:
        caminho = str(Path.home() / ".local/share/fastfetch/presets/d3bian" / f"{nome}.jsonc")
    return {"fastfetch_config": caminho}


def shell_da_sessao() -> str:
    """SHELL que a sessao grafica guardou ao entrar; sem sessao achada, o deste processo."""
    uid = os.getuid()
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != uid or (proc / "comm").read_text().strip() not in SESSOES:
                continue
            for item in (proc / "environ").read_bytes().split(b"\0"):
                if item.startswith(b"SHELL="):
                    return item[6:].decode(errors="replace")
        except OSError:
            continue
    return os.environ.get("SHELL", "")


# o mesmo passo a passo do comum.js (passosSessao), para a linha de comando
PASSOS_SESSAO = [
    "Salve o que estiver aberto: tudo fecha junto com a sessao, inclusive este terminal.",
    "Xfce: menu > Sair > Encerrar sessao. GNOME: canto de cima > Desligar > Sair. "
    "Bloquear a tela, suspender ou trocar de usuario nao trocam a sessao.",
    "Se aparecer \"Salvar sessao para logins futuros\", desmarque.",
    "Entre de novo, abra um terminal e rode echo $SHELL: deve terminar em /{shell}.",
    "Se ainda aparecer o shell antigo, reinicie o computador.",
]


def shell_pendente() -> tuple[str, str]:
    """(shell do login, shell da sessao) enquanto a troca ainda nao vale; senao ("", "")."""
    import pwd
    cadastro = pwd.getpwuid(os.getuid()).pw_shell
    sessao = shell_da_sessao()
    if not sessao or sessao == cadastro:
        return "", ""
    return cadastro, sessao


# blocos dos outros projetos de terminal que tambem poem o Oh My Posh no bash
OUTROS_NO_BASHRC = ("d3bian-init-terminal", "d3bian-init-zsh", "d3bian-init-terminal-kde", "d3bian-init-zsh-kde")


def outros_no_bashrc() -> list[str]:
    """Projetos de terminal com prompt ligado no ~/.bashrc: o prompt carregaria duas vezes."""
    import re
    try:
        texto = (Path.home() / ".bashrc").read_text(errors="replace")
    except OSError:
        return []
    achados = []
    for nome in OUTROS_NO_BASHRC:
        m = re.search(rf"^# {re.escape(nome)}$(.*?)^# fim {re.escape(nome)}$", texto, re.S | re.M)
        if m and "oh-my-posh" in m.group(1):
            achados.append(nome)
    return achados


def verificacoes(add: Callable[..., None]) -> None:
    """Checagens a mais. add(nome, ok, detalhe, critico=True, dica="")."""
    gravavel = os.access(Path.home(), os.W_OK)
    add("Pasta pessoal", gravavel,
        "gravavel" if gravavel else f"sem permissao de escrita em {Path.home()}",
        dica="não consigo escrever na pasta pessoal")

    outros = outros_no_bashrc()
    add("Outros prompts no .bashrc", not outros,
        "nenhum" if not outros else
        f"{', '.join(outros)} também põe o Oh My Posh no bash; desligue \"Oh My Posh no bash também\" "
        "nesse projeto para o prompt não carregar duas vezes",
        critico=False)

    maquina = platform.machine()
    add("Arquitetura", maquina.lower() in ARQUITETURAS, maquina,
        dica=f"o Oh My Posh não tem binário para {maquina}")

    # Ubuntu e Mint mais antigos nao tem fastfetch no repositorio; nao impede a
    # instalacao, so avisa que a opcao fica sem efeito. A Galeria e os Ajustes
    # procuram este nome para mostrar o aviso junto da opcao
    from . import sistema
    distro = sistema.distribuicao().get("PRETTY_NAME", "esta versão")
    pacote = sistema.estado_pacotes(["fastfetch"]).get("fastfetch", {})
    if pacote.get("instalado"):
        detalhe = "instalado"
    elif pacote.get("disponivel"):
        detalhe = f"disponível no apt ({pacote.get('versao') or 'versão do repositório'})"
    else:
        detalhe = f"não está no repositório do {distro}; a opção Fastfetch fica sem efeito"
    add(FASTFETCH_VERIFICACAO, bool(pacote.get("instalado") or pacote.get("disponivel")), detalhe,
        critico=False)

    # a troca de shell so vale na sessao seguinte; nos dois sentidos
    # a dica aparece na faixa do topo de toda pagina, mesmo sem impedir nada
    cadastro, sessao = shell_pendente()
    if not cadastro:
        import pwd
        add(SHELL_VERIFICACAO, True, f"{Path(pwd.getpwuid(os.getuid()).pw_shell).name} no login e nesta sessão",
            critico=False)
    else:
        add(SHELL_VERIFICACAO, False,
            f"o login usa {Path(cadastro).name}, mas esta sessão começou com {Path(sessao).name}; "
            f"saia e entre na sessão para os terminais abrirem o {Path(cadastro).name}",
            critico=False, dica=f"falta encerrar a sessão para o terminal abrir o {Path(cadastro).name}")

    terminais = [t for t in ("xfce4-terminal", "gnome-terminal") if shutil.which(t)]
    add("Terminal com cores ajustaveis", bool(terminais),
        ", ".join(terminais) or "nem xfce4-terminal nem gnome-terminal; fonte e cores ficam à mão",
        critico=False)

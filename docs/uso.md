# Usando o d3bian-init-bash

[← voltar ao README](../README.md)

## Rodar

Clone com o nome da pasta igual ao do pacote Python (com `_`) e rode como módulo:

```sh
git clone https://github.com/diego-luz/d3bian-bash.git d3bian_init_bash
python3 -m d3bian_init_bash            # pede a senha uma vez e abre o painel
python3 -m d3bian_init_bash aplicar --simular
```

O painel abre em `http://127.0.0.1:8765`. A página é azul-gelo, para não
confundir com o vermelho do d3bian-init-terminal, o verde-limão do
d3bian-init-zsh e as cores dos outros painéis.

## O que é instalado

**Só o bash**: sem zsh e sem fish. É irmão do `d3bian-init-terminal` (fish) e do
`d3bian-init-zsh`, com o mesmo prompt, fonte, cores e fastfetch:

- **Bash** como shell padrão (se o login estiver no zsh ou no fish, volta para o
  bash), com o básico que o fish traz ligado: histórico grande sem repetidos,
  setas que procuram pelo começo do comando, completar sem diferença de
  maiúsculas (bash-completion), `cd` só com o nome da pasta
- **Sugestões e realce enquanto digita** pelo [ble.sh](https://github.com/akinomyoga/ble.sh):
  o resto do comando aparece apagado (seta para a direita aceita) e comando que
  não existe fica vermelho. Não está no repositório do Debian; vem do release
  nightly do autor, só para a pessoa, em `~/.local/share/blesh`
- **fzf** no Ctrl+R (histórico), Ctrl+T (arquivos) e Alt+C (pastas)
- **Saudação** ao abrir (a do vídeo do Linuxscoop, traduzida)
- **Oh My Posh** em `/usr/local/bin` e os temas oficiais em `~/.poshthemes`,
  inclusive versões **sem git** de alguns temas (o mesmo visual, sem o ramo `main`)
- **Nerd Font** (FiraCode, JetBrains Mono, Hack, Meslo ou Cascadia) em
  `~/.local/share/fonts/NerdFonts`
- **Esquema de cores** e fonte no xfce4-terminal (xfconf) e no GNOME Terminal
  (gsettings); Everforest Dark Hard é o padrão, como no vídeo
- **Fastfetch** ao abrir o terminal, com presets adaptados para Debian
- **Galeria** com capturas de cada tema, preset e esquema, para escolher vendo

## Instalação pelo painel

1. `python3 -m d3bian_init_bash` abre a página no navegador (pede a senha de administrador uma vez, no terminal).
2. Em **Ajustes**, escolha as opções e clique em **Instalar tudo**; o progresso de cada etapa aparece na hora.
3. Depois, mudar uma opção e **Aplicar** roda de novo só as etapas afetadas.
4. **Voltar ao que era antes** desfaz tudo; com **Remover também o que foi instalado**, tira também os pacotes.

## O que fica onde

| Caminho | Escrito por |
|---|---|
| `~/.bashrc` | um bloco marcado, no fim, que carrega `~/.config/bash/conf.d/*.bash` em ordem; o resto do arquivo fica intocado |
| `~/.config/bash/conf.d/d3bian-init-bash-NN-*.bash` | ble.sh, base, fzf, prompt, fastfetch e saudação |
| `~/.local/share/blesh/` | ble.sh |
| `~/.local/share/fastfetch/presets/d3bian/` | presets adaptados |
| canal `xfce4-terminal` do xfconf, perfil padrão do GNOME Terminal | fonte e cores |

Se o terminal ou o zsh também estiverem com **Oh My Posh no bash também** ligado,
o prompt carrega duas vezes; a verificação "Outros prompts no .bashrc" avisa.

A troca de shell (`chsh`) só vale depois de sair e entrar na sessão: a sessão
gráfica guarda o `SHELL` de quando começou, e todo terminal herda esse. Fechar as
janelas não basta. A fonte nova só aparece depois de fechar **todas** as janelas
do terminal: elas saem de um processo só, que não enxerga fonte instalada depois
de ele abrir.

## Ordem dos arquivos do bash

O número no nome decide a ordem, e ela importa: o ble.sh entra primeiro sem se
ligar (`--noattach`) e só liga no último arquivo, depois do prompt e das teclas,
como o ble.sh pede. Com o ble.sh ligado, o fzf usa a integração dele.

| nº | arquivo | opção |
|---|---|---|
| 05 | carrega o ble.sh | `blesh` |
| 10 | base: histórico, `autocd`, completar, setas | `base` |
| 30 | fzf | `fzf` |
| 40 | prompt do Oh My Posh | `tema_posh` |
| 70 | fastfetch | `fastfetch` |
| 75 | saudação | `saudacao` |
| 99 | liga o ble.sh | `blesh` |

## Sistemas

Família Debian: Debian, Ubuntu e Mint (a verificação aceita `debian` no `ID` ou no
`ID_LIKE` do `/etc/os-release`). Fedora e outras famílias ficam de fora.

O fastfetch não existe no repositório de versões mais antigas do Ubuntu e do Mint.
Isso não impede a instalação; é sinalizado em três lugares:

- verificação prévia "Fastfetch no repositorio", em amarelo
- aviso junto da opção, na Galeria e nos Ajustes
- linhas `atencao:` no log da receita 70, também em amarelo

## Voltar ao que era antes

Em Ajustes, **Voltar ao que era antes**, ou `d3bian-init-bash restaurar --sim`.
O `desfazer.py` devolve cada coisa do jeito dela, em vez de copiar arquivos de volta:

- shell do login: o que a receita 00 guardou em `~/.local/state/d3bian-init-bash/shell-original`
- `conf.d` do bash e presets do fastfetch: apagados
- `~/.bashrc` e `gtk.css`: sai só o bloco marcado; se nada mais mudou, o arquivo
  volta igual ao de antes
- xfce4-terminal e GNOME Terminal: cada chave que a receita 60 mexe volta ao valor
  de antes (`xfce4-terminal-original`, `gnome-terminal-original`). Esse valor é
  o da primeira instalação, mas passa a ser o de outro programa quando esse
  programa muda a chave depois do projeto (o bigsur, por exemplo). Chave mudada
  depois da última aplicação fica como está
- etapas desmarcadas, e a página volta a oferecer a instalação

O ble.sh, o oh-my-posh, os temas e as fontes ficam instalados, sem uso, a não ser
que se marque **Remover também o que foi instalado** (ou `restaurar --sim --apagar`).
Aí uma etapa a mais apaga só o que o projeto instalou, e a página mostra a lista
exata antes de confirmar:

- pacotes do apt: os que o motor anotou em `pacotes-instalados` a cada instalação;
  cada um passa por `apt-get -s remove`, e o que levaria outros programas junto
  (fora os que também saem) fica. As dependências que o apt trouxe só por eles
  saem junto
- ble.sh (com o cache e o histórico dele), oh-my-posh, `~/.poshthemes` (se foi
  criada pelo projeto, ou só as versões sem git) e a Nerd Font baixada, anotados
  pelas receitas em `arquivos-criados`
- enquanto outro projeto d3bian-init estiver aplicado nesta conta, os pacotes e o
  que é de todos (oh-my-posh, temas, Nerd Font, presets do fastfetch) ficam; o
  shell do login de qualquer conta da máquina também fica
- por último, as pastas do projeto: opções, log e cópias de segurança

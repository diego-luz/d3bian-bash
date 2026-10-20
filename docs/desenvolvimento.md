# Desenvolvimento

[← voltar ao README](../README.md)

Painel em Python puro (só a biblioteca padrão) com HTML/JS sem dependências.
O motor, o servidor e as telas comuns vêm do modelo;
os detalhes deles e as armadilhas conhecidas estão em [nucleo.md](nucleo.md).

## Receitas

| id | nome | afetada por |
|---|---|---|
| 00 | backup | |
| 10 | pacotes (bash-completion, curl, unzip, xz-utils, fontconfig) | |
| 20 | bash (conf.d, base, ble.sh, fzf, saudação, chsh) | `shell_padrao`, `base`, `blesh`, `fzf`, `saudacao` |
| 30 | ohmyposh (binário e temas) | |
| 40 | prompt (e as versões sem git) | `tema_posh` |
| 50 | fonte | `fonte` |
| 60 | cores | `cores`, `fonte`, `tamanho_fonte`, `transparencia` |
| 70 | fastfetch | `fastfetch` |

Paletas, fontes e caminhos calculados ficam no `projeto.py`. A ordem dos
arquivos que a receita 20 escreve está em [uso.md](uso.md#ordem-dos-arquivos-do-bash).

## Galeria

As imagens de `recursos/web/exemplos` são geradas, não desenhadas à mão: o
`ferramentas/gerar_exemplos.py` roda o `oh-my-posh print` e o `fastfetch` de
verdade, passa a saída por um emulador de terminal pequeno, monta uma janela em
HTML com a Nerd Font e fotografa com o chromium. Para refazer depois de mudar a
lista de temas ou presets no `opcoes.toml`:

```sh
python3 ferramentas/gerar_exemplos.py --fonte /caminho/FiraCodeNerdFontMono-Regular.ttf
python3 ferramentas/gerar_exemplos.py --fonte ... --apenas prompt
```

Precisa de oh-my-posh, fastfetch, chromium e ImageMagick. O fastfetch mostra os
dados da máquina onde roda; o gerador os lê na hora e troca por fictícios (usuário,
máquina, modelo, processador, vídeo, fone, papel de parede, BIOS, o que está
tocando, PIDs, IPs e cidade), e tira as variáveis `POSH_*` do ambiente para o
oh-my-posh não usar o tema da sessão em vez do pedido.

Presets do fastfetch: créditos e licenças em `recursos/arquivos/fastfetch/LEIAME.md`.

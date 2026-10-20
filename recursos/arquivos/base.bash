# gerado pelo @@NOME@@; mude pela pagina de Ajustes, nao aqui
# o basico que o fish ja traz ligado e o bash deixa desligado

# historico grande, sem repetidos, somado entre as janelas em vez de sobrescrito
HISTSIZE=50000
HISTFILESIZE=100000
HISTCONTROL=ignoreboth:erasedups
shopt -s histappend cmdhist

# o nome de uma pasta sozinho entra nela, erro pequeno no cd e corrigido e
# ** procura em todas as subpastas
shopt -s autocd cdspell dirspell globstar checkwinsize

# completar: o bash-completion do Debian, sem diferenca de maiusculas, e a
# lista ja na primeira Tab
if ! shopt -oq posix && [[ -z ${BASH_COMPLETION_VERSINFO-} && -r /usr/share/bash-completion/bash_completion ]]; then
  . /usr/share/bash-completion/bash_completion
fi
bind 'set completion-ignore-case on'
bind 'set show-all-if-ambiguous on'
bind 'set colored-stats on'
bind 'set colored-completion-prefix on'
bind 'set mark-symlinked-directories on'

# as setas procuram no historico pelo comeco ja digitado, como no fish; cada
# tecla vai com as duas sequencias, porque o terminal manda uma ou outra
bind '"\e[A": history-search-backward'
bind '"\e[B": history-search-forward'
bind '"\eOA": history-search-backward'
bind '"\eOB": history-search-forward'
# Ctrl+setas andam por palavra
bind '"\e[1;5C": forward-word'
bind '"\e[1;5D": backward-word'

alias ls='ls --color=auto'
alias grep='grep --color=auto'

# gerado pelo @@NOME@@; mude pela pagina de Ajustes, nao aqui
# a saudacao do video do Linuxscoop, traduzida: escreve letra por letra.
# O read com tempo num descritor que nunca recebe nada espera sem abrir um
# sleep por letra
__d3_digitar() {
  local texto="$*" i fd
  exec {fd}<> <(:)
  for (( i = 0; i < ${#texto}; i++ )); do
    printf '%s' "${texto:i:1}"
    read -r -t 0.01 -u "$fd" || :
  done
  exec {fd}>&-
  echo
}
__d3_digitar ""
__d3_digitar " Olá, $(whoami)!"
__d3_digitar " Bem-vindo de volta! Hoje é $(date '+%A, %d de %B de %Y')."
__d3_digitar " Lembre-se: todo dia é uma nova chance de brilhar! 🚀"
__d3_digitar ""
unset -f __d3_digitar

[app]

# Título visível da aplicação
title = SADI Calc v1.0

# Nome do pacote (sem espaços ou maiúsculas)
package.name = sadicalc

# Domínio do pacote
package.domain = org.jhonnytavares

# Pasta do código fonte (atual = diretório atual)
source.dir = .

# Extensões a incluir
source.include_exts = py,png,jpg,kv,atlas

# Versão da app
version = 1.0

# Dependências Python/Kivy
requirements = python3,kivy

# Orientação do ecrã (portrait para telemóvel)
orientation = portrait

# Ecrã inteiro (0 = não, 1 = sim)
fullscreen = 0

# Configurações Android
android.api = 33
android.minapi = 21

[buildozer]
log_level = 2
warn_on_root = 1
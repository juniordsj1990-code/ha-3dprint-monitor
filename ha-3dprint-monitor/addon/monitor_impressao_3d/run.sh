#!/usr/bin/with-contenv bashio

bashio::log.info "Iniciando Monitor de Impressão 3D..."

# Lê configurações da interface do add-on
export GEMINI_API_KEY=$(bashio::config 'gemini_api_key')
export CAMERA_ENTITY=$(bashio::config 'camera_entity')
export INTERVALO_MINUTOS=$(bashio::config 'intervalo_minutos')
export SEVERIDADE_ALERTA=$(bashio::config 'severidade_alerta')
export TELEGRAM_BOT_TOKEN=$(bashio::config 'telegram_bot_token')
export TELEGRAM_CHAT_ID=$(bashio::config 'telegram_chat_id')
export OCTOPRINT_URL=$(bashio::config 'octoprint_url')
export OCTOPRINT_API_KEY=$(bashio::config 'octoprint_api_key')
export PAUSAR_EM_FALHA_ALTA=$(bashio::config 'pausar_em_falha_alta')
export OCTOPRINT_ENTITY=$(bashio::config 'octoprint_entity')

# Token do HA injetado automaticamente pelo Supervisor
export HA_TOKEN="${SUPERVISOR_TOKEN}"
export HA_URL="http://supervisor/core"

bashio::log.info "Câmera: ${CAMERA_ENTITY}"
bashio::log.info "Intervalo: ${INTERVALO_MINUTOS} minuto(s)"
bashio::log.info "Severidade mínima para alerta: ${SEVERIDADE_ALERTA}"
bashio::log.info "Pausar em falha alta: ${PAUSAR_EM_FALHA_ALTA}"

exec python3 /app/monitor.py

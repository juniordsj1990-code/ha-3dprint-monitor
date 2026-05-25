# Monitor de Impressão 3D

Monitora sua impressão 3D em tempo real usando visão por IA (Google Gemini) e envia alertas pelo Telegram ao detectar falhas.

## Falhas detectadas

- 🍝 **Spaghetti** — filamento solto no ar
- 📐 **Layer Shifting** — camadas desalinhadas
- 🌡️ **Warping** — bordas levantando da mesa
- 💧 **Under/Over Extrusion** — sub ou superextrusão
- 🕸️ **Stringing** — fios entre partes
- 🛏️ **Bed Adhesion Failure** — peça soltando
- 🔒 **Clogging** — entupimento do bico
- 📦 **Layer Delamination** — camadas separando

## Requisitos

- Câmera integrada ao Home Assistant (MotionEye, RTSP, etc.)
- Conta gratuita no Google AI Studio (Gemini)
- Bot no Telegram
- OctoPrint na rede local

## Como obter as chaves

**Repositório:** https://github.com/juniordsj1990-code/ha-3dprint-monitor

**Gemini (gratuito):** https://aistudio.google.com/apikey

**Telegram Bot Token:** Fale com @BotFather e envie /newbot

**Telegram Chat ID:** Fale com @userinfobot

**OctoPrint API Key:** OctoPrint > Configurações > API

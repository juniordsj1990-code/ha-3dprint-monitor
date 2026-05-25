import os
import requests
import base64
import json
import time
import logging
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("monitor3d")

# ── Configurações vindas do run.sh (interface do add-on) ─────
GEMINI_API_KEY      = os.environ["GEMINI_API_KEY"]
CAMERA_ENTITY       = os.environ["CAMERA_ENTITY"]
INTERVALO_MINUTOS   = int(os.environ.get("INTERVALO_MINUTOS", 2))
SEVERIDADE_ALERTA   = os.environ.get("SEVERIDADE_ALERTA", "media")
TELEGRAM_BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]
OCTOPRINT_URL       = os.environ["OCTOPRINT_URL"].rstrip("/")
OCTOPRINT_API_KEY   = os.environ["OCTOPRINT_API_KEY"]
PAUSAR_EM_FALHA_ALTA= os.environ.get("PAUSAR_EM_FALHA_ALTA", "true").lower() == "true"
OCTOPRINT_ENTITY    = os.environ.get("OCTOPRINT_ENTITY", "sensor.octoprint_current_state")
HA_TOKEN            = os.environ["HA_TOKEN"]
HA_URL              = os.environ.get("HA_URL", "http://supervisor/core")

SEVERIDADE_ORDEM = {"baixa": 1, "media": 2, "alta": 3}

PROMPT_ANALISE = """
Você é um especialista em impressão 3D. Analise esta imagem de uma impressão em andamento.

Verifique especificamente:
- Spaghetti (filamento solto no ar, sem estrutura)
- Layer shifting (camadas desalinhadas/deslocadas)
- Warping (bordas ou base levantando da mesa)
- Under extrusion (subextrusão — linhas finas, gaps, camadas abertas)
- Over extrusion (superextrusão — blobs, excesso de material)
- Stringing (fios de filamento entre partes)
- Bed adhesion failure (peça soltando da mesa)
- Clogging (entupimento — sem extrusão)
- Layer delamination (camadas separando)

Responda APENAS em JSON válido, sem markdown, sem explicações fora do JSON:

{
  "impressao_ok": true ou false,
  "falhas": [
    {
      "tipo": "nome da falha",
      "descricao": "descrição objetiva do que foi visto na imagem",
      "severidade": "baixa" | "media" | "alta",
      "recomendacao": "o que fazer"
    }
  ],
  "resumo": "frase curta geral sobre o estado da impressão"
}

Se não houver falhas, retorne "impressao_ok": true e "falhas": [].
"""


def capturar_snapshot() -> bytes:
    log.info(f"Capturando snapshot: {CAMERA_ENTITY}")
    url = f"{HA_URL}/api/camera_proxy/{CAMERA_ENTITY}"
    headers = {"Authorization": f"Bearer {HA_TOKEN}"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    log.info(f"Snapshot OK — {len(resp.content)} bytes")
    return resp.content


def analisar_com_gemini(imagem_bytes: bytes) -> dict:
    log.info("Enviando imagem para o Gemini...")
    imagem_b64 = base64.b64encode(imagem_bytes).decode("utf-8")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT_ANALISE},
                    {"inline_data": {"mime_type": "image/jpeg", "data": imagem_b64}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1024},
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    texto = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    texto = texto.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    resultado = json.loads(texto)
    log.info(f"Análise OK — impressao_ok={resultado.get('impressao_ok')}")
    return resultado


def deve_alertar(falhas: list) -> bool:
    nivel_minimo = SEVERIDADE_ORDEM.get(SEVERIDADE_ALERTA, 2)
    return any(
        SEVERIDADE_ORDEM.get(f.get("severidade", "baixa"), 0) >= nivel_minimo
        for f in falhas
    )


def pausar_octoprint() -> bool:
    log.info("Pausando OctoPrint...")
    try:
        resp = requests.post(
            f"{OCTOPRINT_URL}/api/job",
            headers={"X-Api-Key": OCTOPRINT_API_KEY, "Content-Type": "application/json"},
            json={"command": "pause", "action": "pause"},
            timeout=10,
        )
        ok = resp.status_code in (200, 204)
        log.info(f"Pausa OctoPrint: {'OK' if ok else 'FALHOU'} ({resp.status_code})")
        return ok
    except Exception as e:
        log.error(f"Erro ao pausar OctoPrint: {e}")
        return False


def enviar_telegram(mensagem: str, imagem_bytes: bytes = None) -> None:
    base = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    try:
        if imagem_bytes:
            requests.post(
                f"{base}/sendPhoto",
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": mensagem, "parse_mode": "HTML"},
                files={"photo": ("snapshot.jpg", imagem_bytes, "image/jpeg")},
                timeout=20,
            )
        else:
            requests.post(
                f"{base}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": mensagem, "parse_mode": "HTML"},
                timeout=15,
            )
        log.info("Telegram enviado.")
    except Exception as e:
        log.error(f"Erro Telegram: {e}")


def montar_mensagem_alerta(analise: dict, pausado: bool) -> str:
    hora = datetime.now().strftime("%H:%M:%S")
    falhas = analise.get("falhas", [])
    icones = {"alta": "🔴", "media": "🟡", "baixa": "🟢"}
    linhas = [
        "🖨️ <b>FALHA NA IMPRESSÃO 3D DETECTADA</b>",
        f"🕐 {hora}",
        f"📋 {analise.get('resumo', '')}",
        "",
    ]
    for f in falhas:
        sev = f.get("severidade", "baixa")
        linhas.append(f"{icones.get(sev, '⚪')} <b>{f.get('tipo')}</b> [{sev.upper()}]")
        linhas.append(f"   └ {f.get('descricao', '')}")
        linhas.append(f"   💡 {f.get('recomendacao', '')}")
        linhas.append("")
    if pausado:
        linhas.append("⏸️ <b>Impressora PAUSADA automaticamente.</b>")
    else:
        linhas.append("▶️ Impressora <b>não pausada</b>. Verifique manualmente.")
    return "\n".join(linhas)


def ciclo_analise() -> None:
    try:
        imagem = capturar_snapshot()
        analise = analisar_com_gemini(imagem)
        falhas = analise.get("falhas", [])

        if not analise.get("impressao_ok", True) and falhas and deve_alertar(falhas):
            pausado = False
            if PAUSAR_EM_FALHA_ALTA and any(f.get("severidade") == "alta" for f in falhas):
                pausado = pausar_octoprint()
            mensagem = montar_mensagem_alerta(analise, pausado)
            enviar_telegram(mensagem, imagem)
            log.warning(f"{len(falhas)} falha(s) detectada(s) — alerta enviado.")
        else:
            log.info("Impressão OK.")

    except Exception as e:
        log.error(f"Erro no ciclo: {e}")
        try:
            enviar_telegram(f"⚠️ <b>Erro no Monitor 3D:</b>\n<code>{e}</code>")
        except Exception:
            pass


def main():
    log.info("=" * 50)
    log.info("  Monitor de Impressão 3D — Add-on HA")
    log.info(f"  Câmera    : {CAMERA_ENTITY}")
    log.info(f"  Intervalo : {INTERVALO_MINUTOS} min")
    log.info(f"  Severidade: {SEVERIDADE_ALERTA}")
    log.info(f"  Pausar    : {PAUSAR_EM_FALHA_ALTA}")
    log.info("=" * 50)

    while True:
        ciclo_analise()
        log.info(f"Próxima análise em {INTERVALO_MINUTOS} minuto(s)...")
        time.sleep(INTERVALO_MINUTOS * 60)


if __name__ == "__main__":
    main()

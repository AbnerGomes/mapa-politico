"""Envio de e-mail via API do Resend (mesmo padrão usado em /my-finances-app).

Usa a API HTTPS do Resend, não SMTP direto — Render bloqueia conexão SMTP de
saída (porta 587/465) nas contas gratuitas. A API roda sobre HTTPS normal
(porta 443), então não tem esse problema.

IMPORTANTE — limitação do Resend em modo sandbox: sem verificar um domínio
próprio em resend.com/domains, o remetente só pode ser o padrão
onboarding@resend.dev, e o Resend só ENTREGA e-mails para o endereço que
criou a conta. Ou seja, com a chave atual, o e-mail pro participante do
teste só chega de verdade se ele usar esse mesmo endereço; qualquer outro
destinatário é aceito pela API (retorna 200) mas não é entregue de fato.
"""

import base64
import os

import requests

RESEND_API_URL = "https://api.resend.com/emails"


def enviar_email(destinatario, assunto, corpo_texto, corpo_html=None, anexos=None):
    """Envia um e-mail via API do Resend. Devolve True/False; nunca levanta
    exceção pra quem chama, só loga o erro (uma falha aqui não pode derrubar
    o cálculo do resultado do quiz).

    `anexos`: lista opcional de dicts {"filename": str, "content": bytes}.
    """
    api_key = os.environ.get("RESEND_API_KEY")
    remetente = os.environ.get("RESEND_FROM", "Mapa Político 2026 <onboarding@resend.dev>")

    if not api_key:
        print("RESEND_API_KEY não configurado. E-mail não enviado.")
        return False

    payload = {
        "from": remetente,
        "to": [destinatario],
        "subject": assunto,
        "text": corpo_texto,
    }
    if corpo_html:
        payload["html"] = corpo_html
    if anexos:
        payload["attachments"] = [
            {
                "filename": anexo["filename"],
                "content": base64.b64encode(anexo["content"]).decode("ascii"),
            }
            for anexo in anexos
        ]

    try:
        resposta = requests.post(
            RESEND_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20,
        )
        if not resposta.ok:
            print("Erro ao enviar e-mail (Resend):", resposta.status_code, resposta.text)
            return False
        return True
    except Exception as e:
        print("Erro ao enviar e-mail (Resend):", e)
        return False

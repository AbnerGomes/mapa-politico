"""Integração com a API da Anthropic (Claude Haiku) para:
1) classificar respostas livres ("Outros") em um delta numérico no eixo do tema;
2) gerar o texto narrativo do mapa político do usuário, no estilo conversa/humano.

Se a chave não estiver configurada ou a chamada falhar, cai em modo de fallback
(delta neutro / narrativa gerada localmente), pra nunca travar o teste.
"""

import json
import os
import re

try:
    import anthropic
except ImportError:  # ambiente sem a lib instalada ainda
    anthropic = None

MODEL = os.environ.get("CLAUDE_MODEL_HAIKU") or os.environ.get("CLAUDE_MODEL_WHATSAPP") or "claude-haiku-4-5"

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or anthropic is None:
        return None
    try:
        _client = anthropic.Anthropic(api_key=api_key)
    except Exception:
        _client = None
    return _client


def _extrair_json(texto):
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def classificar_resposta_livre(tema_label, polo_neg, polo_pos, pergunta_texto, texto_usuario):
    """Retorna um delta float entre -2 e 2 pra resposta 'Outros'. Fallback: 0.0 (neutro)."""
    client = _get_client()
    if client is None or not texto_usuario or not texto_usuario.strip():
        return 0.0

    prompt = f"""Você está ajudando a pontuar um teste de posicionamento político brasileiro.

Tema: {tema_label}
Escala: -2 = "{polo_neg}" ... 0 = neutro/equilibrado ... +2 = "{polo_pos}"

Pergunta feita à pessoa: "{pergunta_texto}"
Resposta livre da pessoa (opção "Outros"): "{texto_usuario.strip()[:500]}"

Classifique essa resposta na escala de -2 a 2 (pode usar valores decimais como -1.5).
Responda APENAS com um JSON no formato: {{"delta": <numero de -2 a 2>}}
Se a resposta for vaga demais pra classificar, use {{"delta": 0}}."""

    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        texto = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
        data = _extrair_json(texto)
        if data and "delta" in data:
            delta = float(data["delta"])
            return max(-2.0, min(2.0, delta))
    except Exception:
        pass
    return 0.0


NARRATIVA_SCHEMA_PROMPT = """Você é um assistente que resume, de forma honesta e sem viés, o mapa político de uma
pessoa que acabou de responder um teste de posicionamento político brasileiro (eleições 2026).

Regras MUITO importantes:
- Baseie-se SOMENTE nos dados fornecidos abaixo. Não invente posições que a pessoa não indicou.
- Não rotule a pessoa simplesmente de "esquerda" ou "direita".
- Tom conversacional, direto, com emojis, parecido com um resumo de teste de personalidade político — mas sem ridicularizar nem fazer piada da pessoa.
- Responda em português do Brasil.
- Responda ESTRITAMENTE em JSON, sem nenhum texto fora do JSON, no formato:

{{
  "estilo_geral": "uma frase curta e marcante que resume o estilo político da pessoa (ex: 'Centro pragmático')",
  "frase_estilo": "uma citação curta, em 1a pessoa, que capture a atitude da pessoa (ex: 'Não me importa de qual lado veio a ideia. Quero saber se funciona.')",
  "secoes": [
    {{
      "titulo": "ECONOMIA",
      "emoji": "💰",
      "classificacao": "ex: Centro-direita",
      "bullets": ["bullet curto 1", "bullet curto 2", "bullet curto 3"],
      "lema": "frase curta que resume essa seção"
    }},
    ... (gere seções pra: ECONOMIA, POLÍTICAS SOCIAIS, SAÚDE, EDUCAÇÃO, SEGURANÇA, COSTUMES/LIBERDADES, ABORTO, ESTADO, CORRUPÇÃO E POLARIZAÇÃO — pode agrupar temas próximos numa mesma seção se fizer sentido, mas cubra todos)
  ],
  "resumo_final": "2 a 3 frases finais resumindo a visão política da pessoa, sem rotular de forma simplista"
}}

DADOS DO USUÁRIO (escala de cada tema vai de -2 a +2):
{dados}

PRIORIDADES DECLARADAS PELA PESSOA (o que ela considera inegociável, muito importante, importante ou secundário):
{prioridades}
"""


def gerar_narrativa(perfil, macros, temas_info, prioridades_labels):
    """Gera a narrativa do mapa político via Haiku. Fallback: estrutura simples gerada localmente."""
    client = _get_client()

    dados_txt = []
    for tema in temas_info:
        score = perfil.get(tema["id"], 0.0)
        dados_txt.append(f"- {tema['label']} ({tema['polo_neg']} ↔ {tema['polo_pos']}): {score:+.1f}")
    dados_str = "\n".join(dados_txt)
    prioridades_str = "\n".join(f"- {k}: {v}" for k, v in prioridades_labels.items())

    if client is not None:
        prompt = NARRATIVA_SCHEMA_PROMPT.format(dados=dados_str, prioridades=prioridades_str)
        try:
            msg = client.messages.create(
                model=MODEL,
                max_tokens=1800,
                messages=[{"role": "user", "content": prompt}],
            )
            texto = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
            data = _extrair_json(texto)
            if data and "secoes" in data:
                return data
        except Exception:
            pass

    return _narrativa_fallback(perfil, macros)


def _rotulo(valor, negativo, positivo, neutro="Equilibrado(a)"):
    if valor <= -1.2:
        return negativo
    if valor >= 1.2:
        return positivo
    return neutro


def _narrativa_fallback(perfil, macros):
    """Narrativa simples, gerada sem LLM, caso a API não esteja disponível."""
    return {
        "estilo_geral": "Mapa político calculado a partir das suas respostas",
        "frase_estilo": "Minhas posições, tema por tema — sem rótulo automático.",
        "secoes": [
            {
                "titulo": "ECONOMIA",
                "emoji": "💰",
                "classificacao": _rotulo(macros.get("economia", 0), "Economia mais à esquerda", "Economia mais à direita"),
                "bullets": [f"Economia: {perfil.get('economia', 0):+.1f}", f"Impostos: {perfil.get('impostos', 0):+.1f}", f"Privatizações: {perfil.get('privatizacoes', 0):+.1f}"],
                "lema": "Posição calculada a partir das suas respostas.",
            },
            {
                "titulo": "ESTADO",
                "emoji": "🏛️",
                "classificacao": _rotulo(macros.get("estado", 0), "Estado mais enxuto", "Estado mais intervencionista"),
                "bullets": [f"Tamanho do Estado: {perfil.get('estado', 0):+.1f}", f"Meio ambiente: {perfil.get('meio_ambiente', 0):+.1f}"],
                "lema": "Posição calculada a partir das suas respostas.",
            },
            {
                "titulo": "POLÍTICAS SOCIAIS",
                "emoji": "🍚",
                "classificacao": _rotulo(macros.get("social", 0), "Proteção social mais baixa", "Proteção social mais ampla"),
                "bullets": [f"Programas sociais: {perfil.get('politicas_sociais', 0):+.1f}", f"SUS: {perfil.get('sus', 0):+.1f}", f"Educação: {perfil.get('educacao', 0):+.1f}"],
                "lema": "Posição calculada a partir das suas respostas.",
            },
            {
                "titulo": "COSTUMES E LIBERDADES",
                "emoji": "⚖️",
                "classificacao": _rotulo(macros.get("costumes", 0), "Mais conservador(a)", "Mais liberal"),
                "bullets": [f"Aborto: {perfil.get('aborto', 0):+.1f}", f"Liberdade individual: {perfil.get('liberdade_individual', 0):+.1f}"],
                "lema": "Posição calculada a partir das suas respostas.",
            },
            {
                "titulo": "SEGURANÇA",
                "emoji": "🚔",
                "classificacao": _rotulo(macros.get("seguranca", 0), "Foco em prevenção", "Foco em repressão"),
                "bullets": [f"Segurança: {perfil.get('seguranca', 0):+.1f}", f"Armas: {perfil.get('armas', 0):+.1f}"],
                "lema": "Posição calculada a partir das suas respostas.",
            },
            {
                "titulo": "INSTITUIÇÕES",
                "emoji": "🏛️",
                "classificacao": _rotulo(macros.get("instituicoes", 0), "Mais autonomia do Executivo", "Controles institucionais fortes"),
                "bullets": [f"Executivo/Congresso/STF: {perfil.get('instituicoes', 0):+.1f}", f"Corrupção: {perfil.get('corrupcao', 0):+.1f}", f"Polarização: {perfil.get('polarizacao', 0):+.1f}"],
                "lema": "Posição calculada a partir das suas respostas.",
            },
        ],
        "resumo_final": "Este resumo foi gerado localmente (sem IA) porque a chave da API não estava disponível no momento. Os números acima refletem exatamente suas respostas.",
    }

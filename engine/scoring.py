"""Calcula o perfil (mapa político) do usuário a partir das respostas do quiz."""

TEMA_IDS = [
    "economia", "impostos", "privatizacoes", "estado", "meio_ambiente",
    "politicas_sociais", "sus", "educacao", "mulheres_familia",
    "aborto", "liberdade_individual", "seguranca", "armas",
    "instituicoes", "corrupcao", "polarizacao",
]

MACROS = {
    "economia": ["economia", "impostos", "privatizacoes"],
    "estado": ["estado", "meio_ambiente"],
    "social": ["politicas_sociais", "sus", "educacao", "mulheres_familia"],
    "costumes": ["aborto", "liberdade_individual"],
    "seguranca": ["seguranca", "armas"],
    "instituicoes": ["instituicoes", "corrupcao", "polarizacao"],
}

MACRO_LABELS = {
    "economia": "Economia",
    "estado": "Papel do Estado",
    "social": "Políticas sociais",
    "costumes": "Costumes / liberdades individuais",
    "seguranca": "Segurança",
    "instituicoes": "Instituições",
}


def _clamp(v, lo=-2.0, hi=2.0):
    return max(lo, min(hi, v))


def calcular_perfil(perguntas, respostas):
    """respostas: dict {pergunta_id (str/int): {"opcao": "a".."d"} | {"outros": "texto", "delta": float}}

    Retorna dict {tema_id: score (-2..2)}.
    """
    perguntas_por_id = {p["id"]: p for p in perguntas}
    soma = {t: 0.0 for t in TEMA_IDS}
    peso = {t: 0.0 for t in TEMA_IDS}

    for pid_str, resp in respostas.items():
        try:
            pid = int(pid_str)
        except (TypeError, ValueError):
            continue
        pergunta = perguntas_por_id.get(pid)
        if not pergunta:
            continue

        tema = pergunta["tema"]
        tema_sec = pergunta.get("tema_secundario")
        peso_sec = pergunta.get("peso_secundario", 0.5)

        if resp.get("outros"):
            # resposta livre já classificada (delta vindo da LLM), só no tema primário
            delta = _clamp(float(resp.get("delta", 0)))
            soma[tema] += delta * 1.0
            peso[tema] += 1.0
            continue

        opcao_id = resp.get("opcao")
        opcao = next((o for o in pergunta["opcoes"] if o["id"] == opcao_id), None)
        if not opcao:
            continue

        soma[tema] += opcao["delta"] * 1.0
        peso[tema] += 1.0

        if tema_sec and "delta_secundario" in opcao:
            soma[tema_sec] += opcao["delta_secundario"] * peso_sec
            peso[tema_sec] += peso_sec

    perfil = {}
    for tema in TEMA_IDS:
        if peso[tema] > 0:
            perfil[tema] = round(_clamp(soma[tema] / peso[tema]), 2)
        else:
            perfil[tema] = 0.0
    return perfil


def calcular_macros(perfil):
    """Agrega os temas em 6 categorias (Fase 2 do teste)."""
    macros = {}
    for macro_id, temas in MACROS.items():
        valores = [perfil[t] for t in temas if t in perfil]
        macros[macro_id] = round(sum(valores) / len(valores), 2) if valores else 0.0
    return macros

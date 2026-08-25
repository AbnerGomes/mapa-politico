"""Calcula a compatibilidade do usuário com cada candidato, o ranking e o teste de robustez."""

from .scoring import TEMA_IDS, MACROS

PESO_PRIORIDADE = {
    "inegociavel": 3.0,
    "muito_importante": 2.0,
    "importante": 1.5,
    "secundaria": 1.0,
}


def _similaridade(user_score, cand_score):
    """0..1 — quanto mais perto, mais parecido. Distância máxima possível é 4 (-2 a 2)."""
    diff = abs(user_score - cand_score)
    return max(0.0, 1.0 - diff / 4.0)


def comparar_candidato(perfil_usuario, candidato, prioridades, temas_excluidos=None):
    """Retorna (percentual 0-100, detalhe por tema) considerando apenas temas com score não-nulo
    e que não estejam em temas_excluidos (usado no teste de robustez)."""
    temas_excluidos = temas_excluidos or set()
    detalhe = {}
    soma_pesada = 0.0
    soma_pesos = 0.0
    pesos_possiveis = 0.0

    for tema in TEMA_IDS:
        if tema in temas_excluidos:
            continue
        info = candidato["temas"].get(tema, {})
        score = info.get("score")
        peso_prioridade = PESO_PRIORIDADE.get(prioridades.get(tema, "importante"), 1.5)
        pesos_possiveis += peso_prioridade

        if score is None:
            detalhe[tema] = {"disponivel": False, "similaridade": None, "nota": info.get("nota", "")}
            continue

        sim = _similaridade(perfil_usuario.get(tema, 0.0), score)
        detalhe[tema] = {
            "disponivel": True,
            "similaridade": round(sim, 3),
            "nota_pct": round(sim * 100, 1),
            "confianca": info.get("confianca"),
            "nota": info.get("nota", ""),
        }
        soma_pesada += sim * peso_prioridade
        soma_pesos += peso_prioridade

    cobertura = (soma_pesos / pesos_possiveis) if pesos_possiveis > 0 else 0.0
    raw_percentual = (soma_pesada / soma_pesos) * 100 if soma_pesos > 0 else 50.0

    # Candidatos com poucos temas confirmados não podem parecer "100% compatíveis" por coincidência
    # de 1 ou 2 respostas: o resultado é puxado em direção a 50% (neutro) proporcionalmente à
    # cobertura de dados disponíveis sobre aquele candidato.
    percentual = round(50 + (raw_percentual - 50) * cobertura, 1)

    return percentual, detalhe, round(cobertura * 100, 1)


def montar_ranking(perfil_usuario, candidatos, prioridades, temas_excluidos=None):
    ranking = []
    for cand in candidatos:
        pct, detalhe, cobertura_pct = comparar_candidato(perfil_usuario, cand, prioridades, temas_excluidos)
        ranking.append({
            "id": cand["id"],
            "nome": cand["nome"],
            "partido": cand["partido"],
            "vice": cand.get("vice"),
            "status": cand.get("status"),
            "status_nota": cand.get("status_nota"),
            "percentual": pct,
            "cobertura_pct": cobertura_pct,
            "detalhe": detalhe,
        })
    ranking.sort(key=lambda c: c["percentual"], reverse=True)
    return ranking


def teste_robustez(perfil_usuario, candidatos, prioridades):
    """Fase 9: remove os 3 temas em que o usuário mais concorda com o 1º colocado
    e recalcula o ranking, pra ver se ele se mantém em primeiro."""
    ranking_original = montar_ranking(perfil_usuario, candidatos, prioridades)
    if not ranking_original:
        return None

    vencedor_id = ranking_original[0]["id"]
    vencedor = next(c for c in candidatos if c["id"] == vencedor_id)

    # temas onde o usuário mais concorda com o vencedor (maior similaridade), só entre disponíveis
    sims = []
    for tema in TEMA_IDS:
        info = vencedor["temas"].get(tema, {})
        if info.get("score") is None:
            continue
        sim = _similaridade(perfil_usuario.get(tema, 0.0), info["score"])
        sims.append((tema, sim))
    sims.sort(key=lambda x: x[1], reverse=True)
    top3_temas = [t for t, _ in sims[:3]]

    ranking_sem_top3 = montar_ranking(perfil_usuario, candidatos, prioridades, temas_excluidos=set(top3_temas))
    novo_vencedor_id = ranking_sem_top3[0]["id"] if ranking_sem_top3 else None

    return {
        "vencedor_original": vencedor_id,
        "temas_removidos": top3_temas,
        "continua_em_primeiro": novo_vencedor_id == vencedor_id,
        "novo_vencedor": novo_vencedor_id,
        "ranking_sem_top3": ranking_sem_top3,
    }


def _peso_macro(macro_id, prioridades):
    """Peso de prioridade de um eixo macro = média dos pesos dos temas que o compõem
    (as prioridades continuam sendo definidas por tema, na mesma tela, pros dois cálculos)."""
    temas = MACROS.get(macro_id, [])
    if not temas:
        return 1.5
    pesos = [PESO_PRIORIDADE.get(prioridades.get(t, "importante"), 1.5) for t in temas]
    return sum(pesos) / len(pesos)


def comparar_candidato_macro(macros_usuario, candidato, prioridades, macros_excluidos=None):
    """Igual a comparar_candidato, mas pra perfis resumidos (6 eixos macro em vez de 16 temas) —
    usado pra Governador e Senador, onde a pesquisa individual de cada candidato é mais rasa."""
    macros_excluidos = macros_excluidos or set()
    detalhe = {}
    soma_pesada = 0.0
    soma_pesos = 0.0
    pesos_possiveis = 0.0

    for macro_id in MACROS:
        if macro_id in macros_excluidos:
            continue
        info = candidato["eixos"].get(macro_id, {})
        score = info.get("score")
        peso = _peso_macro(macro_id, prioridades)
        pesos_possiveis += peso

        if score is None:
            detalhe[macro_id] = {"disponivel": False, "similaridade": None, "nota": info.get("nota", "")}
            continue

        sim = _similaridade(macros_usuario.get(macro_id, 0.0), score)
        detalhe[macro_id] = {
            "disponivel": True,
            "similaridade": round(sim, 3),
            "nota_pct": round(sim * 100, 1),
            "confianca": info.get("confianca"),
            "nota": info.get("nota", ""),
        }
        soma_pesada += sim * peso
        soma_pesos += peso

    cobertura = (soma_pesos / pesos_possiveis) if pesos_possiveis > 0 else 0.0
    raw_percentual = (soma_pesada / soma_pesos) * 100 if soma_pesos > 0 else 50.0
    percentual = round(50 + (raw_percentual - 50) * cobertura, 1)

    return percentual, detalhe, round(cobertura * 100, 1)


def montar_ranking_macro(macros_usuario, candidatos, prioridades, macros_excluidos=None):
    ranking = []
    for cand in candidatos:
        pct, detalhe, cobertura_pct = comparar_candidato_macro(macros_usuario, cand, prioridades, macros_excluidos)
        ranking.append({
            "id": cand["id"],
            "nome": cand["nome"],
            "partido": cand["partido"],
            "status": cand.get("status"),
            "status_nota": cand.get("status_nota"),
            "percentual": pct,
            "cobertura_pct": cobertura_pct,
            "detalhe": detalhe,
        })
    ranking.sort(key=lambda c: c["percentual"], reverse=True)
    return ranking


def teste_robustez_macro(macros_usuario, candidatos, prioridades):
    """Versão macro do teste de robustez: remove o eixo de maior concordância entre o usuário e
    quem ficou em 1º (só 1, já que são apenas 6 eixos no total) e recalcula."""
    ranking_original = montar_ranking_macro(macros_usuario, candidatos, prioridades)
    if not ranking_original:
        return None

    vencedor_id = ranking_original[0]["id"]
    vencedor = next(c for c in candidatos if c["id"] == vencedor_id)

    sims = []
    for macro_id in MACROS:
        info = vencedor["eixos"].get(macro_id, {})
        if info.get("score") is None:
            continue
        sim = _similaridade(macros_usuario.get(macro_id, 0.0), info["score"])
        sims.append((macro_id, sim))
    sims.sort(key=lambda x: x[1], reverse=True)
    top_macro = [m for m, _ in sims[:1]]

    ranking_sem_top = montar_ranking_macro(macros_usuario, candidatos, prioridades, macros_excluidos=set(top_macro))
    novo_vencedor_id = ranking_sem_top[0]["id"] if ranking_sem_top else None

    return {
        "vencedor_original": vencedor_id,
        "temas_removidos": top_macro,
        "continua_em_primeiro": novo_vencedor_id == vencedor_id,
        "novo_vencedor": novo_vencedor_id,
        "ranking_sem_top3": ranking_sem_top,
    }


def melhores_por_area(ranking, areas):
    """Fase 8: pra cada área (grupo de temas), acha o candidato com maior similaridade média
    ponderada só naquela área (ignorando pesos de prioridade do usuário)."""
    resultado = {}
    for area_nome, temas in areas.items():
        melhor = None
        melhor_valor = -1
        for cand in ranking:
            valores = [
                cand["detalhe"][t]["similaridade"]
                for t in temas
                if t in cand["detalhe"] and cand["detalhe"][t]["disponivel"]
            ]
            if not valores:
                continue
            media = sum(valores) / len(valores)
            if media > melhor_valor:
                melhor_valor = media
                melhor = cand["nome"]
        resultado[area_nome] = {"candidato": melhor, "similaridade_media_pct": round(melhor_valor * 100, 1) if melhor else None}
    return resultado

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from engine.scoring import calcular_perfil, calcular_macros, MACRO_LABELS, MACROS
from engine.compatibility import (
    montar_ranking, teste_robustez, melhores_por_area,
    montar_ranking_macro, teste_robustez_macro,
)
from engine.llm import classificar_resposta_livre, gerar_narrativa

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

app = Flask(__name__)


def _carregar_json(nome):
    with open(DATA_DIR / nome, encoding="utf-8") as f:
        return json.load(f)


PERGUNTAS = _carregar_json("perguntas.json")
TEMAS = _carregar_json("temas.json")
TEMAS_POR_ID = {t["id"]: t for t in TEMAS}
CANDIDATOS_RAW = _carregar_json("candidatos.json")
CANDIDATOS = CANDIDATOS_RAW["candidatos"]
GOVERNADOR_RAW = _carregar_json("candidatos_governador_rs.json")
SENADOR_RAW = _carregar_json("candidatos_senador_rs.json")

AREAS_FASE8 = {
    "Geral": [t["id"] for t in TEMAS],
    "Economia": MACROS["economia"],
    "Social": MACROS["social"],
    "Segurança": MACROS["seguranca"],
    "Liberdade individual": ["liberdade_individual", "aborto"],
    "Educação": ["educacao"],
    "Saúde": ["sus"],
    "Responsabilidade fiscal": ["estado", "impostos"],
}

# Cargos disponíveis. "tipo" define qual motor de cálculo é usado (detalhado por tema x
# resumido por eixo macro).
CARGOS = {
    "presidente": {
        "nome": "Presidente da República",
        "tipo": "detalhado",
        "candidatos": CANDIDATOS,
        "atualizado_em": CANDIDATOS_RAW.get("atualizado_em"),
        "aviso": CANDIDATOS_RAW.get("aviso"),
    },
    "governador_rs": {
        "nome": "Governador do Rio Grande do Sul",
        "tipo": "resumido",
        "candidatos": GOVERNADOR_RAW["candidatos"],
        "atualizado_em": GOVERNADOR_RAW.get("atualizado_em"),
        "aviso": GOVERNADOR_RAW.get("aviso"),
    },
    "senador_rs": {
        "nome": "Senador pelo Rio Grande do Sul",
        "tipo": "resumido",
        "candidatos": SENADOR_RAW["candidatos"],
        "atualizado_em": SENADOR_RAW.get("atualizado_em"),
        "aviso": SENADOR_RAW.get("aviso"),
    },
}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/quiz")
def quiz():
    return render_template("quiz.html")


@app.route("/api/perguntas")
def api_perguntas():
    cargos_meta = {
        cid: {"nome": c["nome"], "tipo": c["tipo"]}
        for cid, c in CARGOS.items()
    }
    return jsonify({"perguntas": PERGUNTAS, "temas": TEMAS, "cargos": cargos_meta})


@app.route("/api/resultado", methods=["POST"])
def api_resultado():
    payload = request.get_json(force=True, silent=True) or {}
    respostas = payload.get("respostas", {})
    prioridades = payload.get("prioridades", {})
    cargos_selecionados = payload.get("cargos") or ["presidente"]
    cargos_selecionados = [c for c in cargos_selecionados if c in CARGOS] or ["presidente"]

    # classifica respostas "Outros" via LLM (delta numérico no eixo do tema primário)
    perguntas_por_id = {p["id"]: p for p in PERGUNTAS}
    for pid_str, resp in respostas.items():
        if resp.get("outros"):
            try:
                pid = int(pid_str)
            except (TypeError, ValueError):
                continue
            pergunta = perguntas_por_id.get(pid)
            if not pergunta:
                continue
            tema = TEMAS_POR_ID.get(pergunta["tema"], {})
            delta = classificar_resposta_livre(
                tema.get("label", pergunta["tema"]),
                tema.get("polo_neg", ""),
                tema.get("polo_pos", ""),
                pergunta["texto"],
                resp.get("texto", ""),
            )
            resp["delta"] = delta

    perfil = calcular_perfil(PERGUNTAS, respostas)
    macros = calcular_macros(perfil)

    resultados_por_cargo = {}
    for cid in cargos_selecionados:
        cargo = CARGOS[cid]
        if cargo["tipo"] == "detalhado":
            ranking = montar_ranking(perfil, cargo["candidatos"], prioridades)
            robustez = teste_robustez(perfil, cargo["candidatos"], prioridades)
            melhores_area = melhores_por_area(ranking, AREAS_FASE8)
        else:
            ranking = montar_ranking_macro(macros, cargo["candidatos"], prioridades)
            robustez = teste_robustez_macro(macros, cargo["candidatos"], prioridades)
            melhores_area = None

        resultados_por_cargo[cid] = {
            "nome_cargo": cargo["nome"],
            "tipo": cargo["tipo"],
            "ranking": ranking,
            "robustez": robustez,
            "melhores_por_area": melhores_area,
            "atualizado_em": cargo["atualizado_em"],
            "aviso": cargo["aviso"],
        }

    prioridades_labels = {
        TEMAS_POR_ID[t]["label"]: prioridades.get(t, "importante")
        for t in TEMAS_POR_ID
    }
    narrativa = gerar_narrativa(perfil, macros, TEMAS, prioridades_labels)

    return jsonify({
        "perfil": perfil,
        "macros": macros,
        "macro_labels": MACRO_LABELS,
        "narrativa": narrativa,
        "temas": TEMAS,
        "cargos": resultados_por_cargo,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

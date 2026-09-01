(function () {
  "use strict";

  const main = document.getElementById("app-main");
  const progressWrap = document.getElementById("progress-wrap");
  const progressFill = document.getElementById("progress-fill");
  const progressLabel = document.getElementById("progress-label");

  const NIVEIS = [
    { id: "inegociavel", label: "🔴 Inegociável" },
    { id: "muito_importante", label: "🟠 Muito importante" },
    { id: "importante", label: "🟡 Importante" },
    { id: "secundaria", label: "🟢 Secundária" },
  ];

  const MACRO_SPECTRUM = {
    economia: { icone: "💰", label: "Economia", neg: "Esquerda econômica", pos: "Direita econômica" },
    estado: { icone: "🏛️", label: "Papel do Estado", neg: "Estado mínimo", pos: "Muito intervencionista" },
    social: { icone: "🍚", label: "Políticas sociais", neg: "Baixa proteção", pos: "Universalista" },
    costumes: { icone: "⚖️", label: "Costumes / liberdades", neg: "Conservador", pos: "Libertário" },
    seguranca: { icone: "🚔", label: "Segurança", neg: "Prevenção", pos: "Linha dura" },
    instituicoes: { icone: "🗳️", label: "Instituições", neg: "Autonomia do Executivo", pos: "Controles fortes" },
  };

  const CARGO_ICONES = {
    presidente: "🇧🇷",
    governador_rs: "🌾",
    senador_rs: "🏛️",
  };

  const state = {
    nome: sessionStorage.getItem("mp_nome") || "",
    email: sessionStorage.getItem("mp_email") || "",
    perguntas: [],
    temas: [],
    temasPorId: {},
    cargosMeta: {},
    cargosSelecionados: [],
    idx: 0,
    respostas: {}, // { [perguntaId]: {opcao:'a'} | {outros:true, texto:'...'} }
    prioridades: {}, // { [temaId]: nivelId }
    resultado: null,
  };

  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function setProgress(current, total) {
    progressWrap.hidden = false;
    progressFill.style.width = Math.round((current / total) * 100) + "%";
    progressLabel.textContent = `${current} / ${total}`;
  }

  async function init() {
    if (!state.nome || !state.email) {
      window.location.href = "/";
      return;
    }
    try {
      const res = await fetch("/api/perguntas");
      const data = await res.json();
      state.perguntas = data.perguntas;
      state.temas = data.temas;
      state.cargosMeta = data.cargos || {};
      data.temas.forEach((t) => (state.temasPorId[t.id] = t));
      data.temas.forEach((t) => (state.prioridades[t.id] = "importante"));
      state.cargosSelecionados = Object.keys(state.cargosMeta);
      renderSelecaoCargos();
    } catch (e) {
      main.innerHTML = `<div class="loading">Não foi possível carregar o teste. Recarregue a página.</div>`;
    }
  }

  function renderSelecaoCargos() {
    progressWrap.hidden = true;
    const itensHtml = Object.keys(state.cargosMeta)
      .map((cid) => {
        const cargo = state.cargosMeta[cid];
        const ativo = state.cargosSelecionados.includes(cid);
        return `
        <button type="button" class="opcao opcao-cargo ${ativo ? "selected" : ""}" data-cargo="${cid}">
          <span class="opcao-check">${ativo ? "✅" : "⬜"}</span>
          ${CARGO_ICONES[cid] || "🗳️"} ${escapeHtml(cargo.nome)}
        </button>`;
      })
      .join("");

    main.innerHTML = `
      <div class="card-question">
        <span class="q-tema-tag">🗳️ Antes de começar</span>
        <p class="q-texto">Pra quais eleições você quer ver seu ranking de compatibilidade?</p>
        <p style="color:var(--text-muted);margin-top:-16px;margin-bottom:22px;font-size:0.9rem">
          As 3 eleições já vêm marcadas ✅ — clique numa delas se quiser <strong>tirar</strong> ela da comparação.
          Você responde o teste uma única vez e as mesmas respostas valem pra todas as que ficarem marcadas.
        </p>
        <div class="opcoes" id="lista-cargos">${itensHtml}</div>
        <div class="q-actions" style="justify-content:flex-end">
          <button type="button" class="btn-primario" id="btn-comecar">Começar as perguntas →</button>
        </div>
      </div>
    `;

    main.querySelectorAll("[data-cargo]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const cid = btn.dataset.cargo;
        const idx = state.cargosSelecionados.indexOf(cid);
        if (idx >= 0) state.cargosSelecionados.splice(idx, 1);
        else state.cargosSelecionados.push(cid);
        const agoraAtivo = btn.classList.toggle("selected");
        btn.querySelector(".opcao-check").textContent = agoraAtivo ? "✅" : "⬜";
        btnComecar.disabled = state.cargosSelecionados.length === 0;
      });
    });

    const btnComecar = document.getElementById("btn-comecar");
    btnComecar.disabled = state.cargosSelecionados.length === 0;
    btnComecar.addEventListener("click", () => renderPergunta(0));
  }

  function renderPergunta(idx) {
    state.idx = idx;
    const pergunta = state.perguntas[idx];
    const tema = state.temasPorId[pergunta.tema] || {};
    setProgress(idx + 1, state.perguntas.length);

    const respostaAtual = state.respostas[pergunta.id];
    const opcaoSelecionada = respostaAtual && !respostaAtual.outros ? respostaAtual.opcao : null;
    const outrosSelecionado = !!(respostaAtual && respostaAtual.outros);
    const outrosTexto = outrosSelecionado ? respostaAtual.texto || "" : "";

    const opcoesHtml = pergunta.opcoes
      .map(
        (o) => `
      <button type="button" class="opcao ${opcaoSelecionada === o.id ? "selected" : ""}" data-opcao="${o.id}">
        ${escapeHtml(o.texto)}
      </button>`
      )
      .join("");

    main.innerHTML = `
      <div class="card-question">
        <span class="q-tema-tag">${tema.icone || ""} ${escapeHtml(tema.label || "")}</span>
        <p class="q-texto">${escapeHtml(pergunta.texto)}</p>
        <div class="opcoes">
          ${opcoesHtml}
          <button type="button" class="opcao ${outrosSelecionado ? "selected" : ""}" data-opcao="outros">✏️ Outros — quero escrever com minhas palavras</button>
          <div class="outros-box" id="outros-box" ${outrosSelecionado ? "" : "hidden"}>
            <textarea id="outros-texto" maxlength="500" placeholder="Escreva sua posição sobre esse tema…">${escapeHtml(outrosTexto)}</textarea>
          </div>
        </div>
        <div class="q-actions">
          <button type="button" class="btn-secundario" id="btn-voltar">← Voltar</button>
          <button type="button" class="btn-primario" id="btn-avancar" ${respostaAtual ? "" : "disabled"}>
            ${idx === state.perguntas.length - 1 ? "Ver prioridades →" : "Próxima →"}
          </button>
        </div>
      </div>
    `;

    const outrosBox = document.getElementById("outros-box");
    const outrosTextarea = document.getElementById("outros-texto");
    const btnAvancar = document.getElementById("btn-avancar");

    function selecionarOpcao(opcaoId) {
      main.querySelectorAll(".opcao").forEach((b) => b.classList.remove("selected"));
      if (opcaoId === "outros") {
        main.querySelector('[data-opcao="outros"]').classList.add("selected");
        outrosBox.hidden = false;
        outrosTextarea.focus();
        state.respostas[pergunta.id] = { outros: true, texto: outrosTextarea.value };
        btnAvancar.disabled = outrosTextarea.value.trim().length === 0;
      } else {
        main.querySelector(`[data-opcao="${opcaoId}"]`).classList.add("selected");
        outrosBox.hidden = true;
        state.respostas[pergunta.id] = { opcao: opcaoId };
        btnAvancar.disabled = false;
      }
    }

    main.querySelectorAll(".opcao").forEach((btn) => {
      btn.addEventListener("click", () => selecionarOpcao(btn.dataset.opcao));
    });

    outrosTextarea.addEventListener("input", () => {
      state.respostas[pergunta.id] = { outros: true, texto: outrosTextarea.value };
      btnAvancar.disabled = outrosTextarea.value.trim().length === 0;
    });

    document.getElementById("btn-voltar").addEventListener("click", () => {
      if (idx > 0) renderPergunta(idx - 1);
      else renderSelecaoCargos();
    });

    btnAvancar.addEventListener("click", () => {
      if (idx < state.perguntas.length - 1) {
        renderPergunta(idx + 1);
      } else {
        renderPrioridades();
      }
    });
  }

  function renderPrioridades() {
    progressWrap.hidden = true;

    const itensHtml = state.temas
      .map((tema) => {
        const btns = NIVEIS.map(
          (n) => `<button type="button" class="prioridade-btn" data-tema="${tema.id}" data-nivel="${n.id}"
            data-ativo="${state.prioridades[tema.id] === n.id}">${n.label}</button>`
        ).join("");
        return `
        <div class="prioridade-item">
          <div>
            <div class="label">${tema.icone} ${escapeHtml(tema.label)}</div>
            <div class="sub-label">${escapeHtml(tema.polo_neg)} ↔ ${escapeHtml(tema.polo_pos)}</div>
          </div>
          <div class="prioridade-opcoes">${btns}</div>
        </div>`;
      })
      .join("");

    main.innerHTML = `
      <div class="prioridades-wrap">
        <h2>Qual o peso de cada pauta pra você?</h2>
        <p class="sub">Um candidato pode concordar com você em várias coisas, mas discordar numa pauta que
          você considera inegociável — isso importa no cálculo final. Ajuste o que quiser (o padrão é "Importante").
          Esse mesmo peso vale pra todas as eleições que você marcou no início.</p>
        <div id="lista-prioridades">${itensHtml}</div>
        <div class="footer-acoes">
          <button type="button" class="btn-primario" id="btn-resultado">Ver meu mapa político →</button>
        </div>
      </div>
    `;

    main.querySelectorAll(".prioridade-btn").forEach((btn) => {
      if (btn.dataset.ativo === "true") btn.classList.add("active");
      btn.addEventListener("click", () => {
        const tema = btn.dataset.tema;
        const nivel = btn.dataset.nivel;
        state.prioridades[tema] = nivel;
        main.querySelectorAll(`.prioridade-btn[data-tema="${tema}"]`).forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
      });
    });

    document.getElementById("btn-resultado").addEventListener("click", enviarResultado);
  }

  async function enviarResultado() {
    main.innerHTML = `
      <div class="loading-msg">
        <div class="spinner"></div>
        <p>Calculando seu mapa político e comparando com os candidatos das eleições escolhidas…</p>
      </div>`;
    try {
      const res = await fetch("/api/resultado", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          respostas: state.respostas,
          prioridades: state.prioridades,
          cargos: state.cargosSelecionados,
          nome: state.nome,
          email: state.email,
        }),
      });
      const data = await res.json();
      state.resultado = data;
      renderResultado(data);
    } catch (e) {
      main.innerHTML = `<div class="loading">Algo deu errado ao calcular seu resultado. Recarregue e tente de novo.</div>`;
    }
  }

  function barraSpectrum(valor) {
    // valor: -2..2 -> 0..100%
    const pct = ((valor + 2) / 4) * 100;
    return Math.max(2, Math.min(98, pct));
  }

  function renderSpectrum(macros) {
    const rows = Object.keys(MACRO_SPECTRUM)
      .map((key) => {
        const info = MACRO_SPECTRUM[key];
        const valor = macros[key] ?? 0;
        return `
        <div class="spectrum-row">
          <div>${info.icone} ${escapeHtml(info.label)}</div>
          <div>
            <div class="spectrum-track"><div class="spectrum-dot" style="left:${barraSpectrum(valor)}%"></div></div>
            <div class="spectrum-labels"><span>${escapeHtml(info.neg)}</span><span>${escapeHtml(info.pos)}</span></div>
          </div>
        </div>`;
      })
      .join("");
    return `<div class="spectrum">${rows}</div>`;
  }

  function medalha(posicao) {
    if (posicao === 0) return "🥇";
    if (posicao === 1) return "🥈";
    if (posicao === 2) return "🥉";
    return `${posicao + 1}º`;
  }

  function renderRanking(ranking) {
    const itens = ranking
      .map((c, i) => {
        const flag = c.status && c.status !== "ativo"
          ? `<span class="status-flag" title="${escapeHtml(c.status_nota || "")}">⚠️ candidatura sub judice</span>`
          : "";
        const coberturaBaixa = c.cobertura_pct !== undefined && c.cobertura_pct < 50
          ? `<div class="sub-label">⚠️ baseado em poucos dados confirmados (${c.cobertura_pct}% de cobertura) — resultado menos confiável</div>`
          : "";
        return `
        <div class="ranking-item">
          <div class="medalha">${medalha(i)}</div>
          <div class="info">
            <div class="nome">${escapeHtml(c.nome)} <span class="partido">— ${escapeHtml(c.partido)}</span>${flag}</div>
            <div class="barra-bg"><div class="barra-fg" style="width:${c.percentual}%"></div></div>
            ${coberturaBaixa}
          </div>
          <div class="pct">${c.percentual}%</div>
        </div>`;
      })
      .join("");
    return itens;
  }

  function renderTabelaDetalhe(ranking, temas) {
    return ranking
      .map((c) => {
        const linhas = temas
          .map((t) => {
            const d = c.detalhe[t.id];
            if (!d || !d.disponivel) {
              return `<div class="tema-linha"><span>${t.icone} ${escapeHtml(t.label)}</span><span class="nd">Não foi possível determinar com segurança</span></div>`;
            }
            return `<div class="tema-linha"><span>${t.icone} ${escapeHtml(t.label)}</span><span>${d.nota_pct}% compatível</span></div>`;
          })
          .join("");
        return `
        <details class="candidato-detalhe">
          <summary>${escapeHtml(c.nome)} (${c.percentual}%) — ver por tema</summary>
          ${linhas}
        </details>`;
      })
      .join("");
  }

  function renderTabelaDetalheMacro(ranking) {
    return ranking
      .map((c) => {
        const linhas = Object.keys(MACRO_SPECTRUM)
          .map((mid) => {
            const info = MACRO_SPECTRUM[mid];
            const d = c.detalhe[mid];
            if (!d || !d.disponivel) {
              return `<div class="tema-linha"><span>${info.icone} ${escapeHtml(info.label)}</span><span class="nd">Não foi possível determinar com segurança</span></div>`;
            }
            return `<div class="tema-linha"><span>${info.icone} ${escapeHtml(info.label)}</span><span>${d.nota_pct}% compatível</span></div>`;
          })
          .join("");
        return `
        <details class="candidato-detalhe">
          <summary>${escapeHtml(c.nome)} (${c.percentual}%) — ver por eixo</summary>
          ${linhas}
        </details>`;
      })
      .join("");
  }

  function renderMelhoresPorArea(melhores) {
    return Object.keys(melhores)
      .map((area) => {
        const info = melhores[area];
        if (!info.candidato) return `<li><strong>${escapeHtml(area)}:</strong> não foi possível determinar com segurança.</li>`;
        return `<li><strong>${escapeHtml(area)}:</strong> ${escapeHtml(info.candidato)} (${info.similaridade_media_pct}% de compatibilidade nessa área)</li>`;
      })
      .join("");
  }

  function renderRobustez(robustez, labelLookup, plural) {
    if (!robustez) return "";
    const nomes = robustez.temas_removidos
      .map((id) => (labelLookup[id] ? labelLookup[id].label : id))
      .join(", ");
    const status = robustez.continua_em_primeiro
      ? `✅ Sim — mesmo removendo ${plural ? "esses temas" : "esse eixo"}, o resultado se mantém.`
      : `⚠️ Não — sem ${plural ? "esses temas" : "esse eixo"}, o 1º colocado muda.`;
    let extra = "";
    if (!robustez.continua_em_primeiro && robustez.ranking_sem_top3 && robustez.ranking_sem_top3[0]) {
      extra = `<p>Sem ${plural ? "os temas" : "o eixo"} de maior concordância, quem assume o topo é <strong>${escapeHtml(
        robustez.ranking_sem_top3[0].nome
      )}</strong> (${robustez.ranking_sem_top3[0].percentual}%).</p>`;
    }
    return `
      <p>Testamos: se retirarmos ${plural ? "os temas em que você mais concorda" : "o eixo em que você mais concorda"} com quem ficou em 1º
      (<strong>${escapeHtml(nomes)}</strong>), o resultado se mantém?</p>
      <p>${status}</p>
      ${extra}
      <p class="footer-disclaimer" style="margin-top:10px;text-align:left">
        Isso ajuda a ver se o 1º lugar depende de poucos pontos muito fortes, ou se reflete uma compatibilidade
        mais ampla com o que você respondeu.
      </p>`;
  }

  function renderCargoSecao(cid, resultado, temas) {
    const icone = CARGO_ICONES[cid] || "🗳️";
    const tabela = resultado.tipo === "detalhado"
      ? renderTabelaDetalhe(resultado.ranking, temas)
      : renderTabelaDetalheMacro(resultado.ranking);
    const labelLookup = resultado.tipo === "detalhado" ? state.temasPorId : MACRO_SPECTRUM;
    const plural = resultado.tipo === "detalhado";

    const melhoresHtml = resultado.melhores_por_area
      ? `<div class="res-secao">
          <h3>🔍 Quem mais combina com você em cada área (${escapeHtml(resultado.nome_cargo)})</h3>
          <ul>${renderMelhoresPorArea(resultado.melhores_por_area)}</ul>
        </div>`
      : "";

    return `
      <div class="res-secao">
        <h3>${icone} Ranking — ${escapeHtml(resultado.nome_cargo)}</h3>
        <div class="ranking-list">${renderRanking(resultado.ranking)}</div>
        <div class="wrap-table">${tabela}</div>
      </div>
      ${melhoresHtml}
      <div class="res-secao">
        <h3>🧪 Teste de robustez — ${escapeHtml(resultado.nome_cargo)}</h3>
        ${renderRobustez(resultado.robustez, labelLookup, plural)}
      </div>
      <p class="footer-disclaimer">
        ${escapeHtml(resultado.aviso || "")} Última atualização: ${escapeHtml(resultado.atualizado_em || "")}.
      </p>
    `;
  }

  function renderResultado(data) {
    const { narrativa, macros, temas, cargos } = data;
    state.temasPorId = {};
    temas.forEach((t) => (state.temasPorId[t.id] = t));

    const secoesHtml = narrativa.secoes
      .map(
        (s) => `
      <div class="res-secao">
        <h3>${escapeHtml(s.emoji || "")} ${escapeHtml(s.titulo || "")}</h3>
        <span class="classificacao">${escapeHtml(s.classificacao || "")}</span>
        <ul>${(s.bullets || []).map((b) => `<li>${escapeHtml(b)}</li>`).join("")}</ul>
        <div class="lema">${escapeHtml(s.lema || "")}</div>
      </div>`
      )
      .join("");

    const cargosHtml = Object.keys(cargos)
      .map((cid) => renderCargoSecao(cid, cargos[cid], temas))
      .join("");

    main.innerHTML = `
      <div class="resultado-wrap">
        <div class="res-hero">
          <div class="emoji">🧭✨</div>
          <h1>${escapeHtml(narrativa.estilo_geral || "Seu mapa político")}</h1>
          <p class="frase">“${escapeHtml(narrativa.frase_estilo || "")}”</p>
        </div>

        <div class="res-secao">
          <h3>📍 Onde você está no espectro</h3>
          ${renderSpectrum(macros)}
        </div>

        ${secoesHtml}

        <div class="res-secao resumo-final">
          <h3>🎯 Em resumo</h3>
          <p>${escapeHtml(narrativa.resumo_final || "")}</p>
        </div>

        <div class="res-secao" style="text-align:center">
          <h3 style="justify-content:center">🏆 Meus rankings 2026</h3>
          <p style="color:var(--text-muted);font-size:0.9rem">
            "Este é o candidato mais compatível com as posições que você declarou" — isso não é uma recomendação de voto.
          </p>
        </div>

        ${cargosHtml}

        <div class="footer-acoes">
          <button type="button" class="btn-primario" id="btn-baixar-pdf">⬇️ Baixar PDF do resultado</button>
          <a class="btn-secundario" href="/">Refazer o teste</a>
        </div>
      </div>
    `;

    document.getElementById("btn-baixar-pdf").addEventListener("click", (ev) => baixarPdf(ev.currentTarget, data));
  }

  async function baixarPdf(botao, data) {
    const textoOriginal = botao.textContent;
    botao.disabled = true;
    botao.textContent = "Gerando PDF…";
    try {
      const res = await fetch("/api/resultado/pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nome: state.nome,
          narrativa: data.narrativa,
          macros: data.macros,
          cargos: data.cargos,
        }),
      });
      if (!res.ok) throw new Error("Falha ao gerar PDF");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "mapa-politico-2026.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Não foi possível gerar o PDF agora. Tenta de novo em alguns segundos.");
    } finally {
      botao.disabled = false;
      botao.textContent = textoOriginal;
    }
  }

  init();
})();

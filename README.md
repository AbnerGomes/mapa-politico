# 🧭 Mapa Político 2026

Teste de posicionamento político que calcula seu mapa político e compara com os
candidatos a **Presidente da República**, **Governador do RS** e **Senador pelo RS**
nas eleições de 2026, gerando um ranking de compatibilidade — **sem recomendar voto**.

Deputado Estadual e Deputado Federal (RS) ficaram de fora por enquanto: são
centenas de candidatos cada um, inviável pesquisar e sustentar fonte individual como
foi feito para os demais cargos.

## Como funciona

0. **Escolha de cargos** — antes das perguntas, o usuário marca quais eleições quer
   comparar (Presidente / Governador RS / Senador RS). As mesmas respostas do quiz
   valem pra todas as eleições marcadas — não precisa refazer o teste pra cada uma.
1. **Quiz** (`/quiz`) — ~20 perguntas objetivas, de múltipla escolha, cada uma com
   opção "Outros" pra resposta livre. Cobre economia, impostos, Estado, privatizações,
   programas sociais, SUS, educação, segurança, armas, aborto, liberdades individuais,
   políticas para mulheres, corrupção, meio ambiente, relação Executivo/Congresso/STF
   e polarização.
2. **Prioridades** — depois do quiz, o usuário classifica cada tema como
   🔴 inegociável / 🟠 muito importante / 🟡 importante / 🟢 secundário.
3. **Cálculo** — o backend (`engine/scoring.py` + `engine/compatibility.py`) calcula
   um perfil de -2 a +2 em 16 temas, agrega em 6 macro categorias (economia, Estado,
   políticas sociais, costumes, segurança, instituições).
   - Pra **Presidente**, a compatibilidade é calculada tema a tema (`comparar_candidato`),
     com o mesmo nível de detalhe que cada tema pede.
   - Pra **Governador RS** e **Senador RS**, o perfil dos candidatos é mais resumido —
     6 eixos macro em vez de 16 temas (`comparar_candidato_macro`) — porque a pesquisa
     individual desses candidatos foi mais rasa.
   - Em ambos os casos, candidatos com pouca cobertura de dados confirmados têm o
     resultado puxado em direção a 50% (neutro), pra não parecerem "100% compatíveis"
     por coincidência de 1 ou 2 respostas.
4. **Narrativa** — `engine/llm.py` usa a API da Anthropic (Claude Haiku, mesma chave/
   modelo do `.env`) pra gerar o texto do mapa político no estilo conversa, e também
   pra classificar respostas livres ("Outros") num delta numérico. Se a chave não
   estiver disponível, cai automaticamente num modo de fallback sem IA.
5. **Resultado** — mostra o mapa visual (comum a todos os cargos) e, pra cada cargo
   marcado: ranking de compatibilidade, quem mais combina em cada área (só Presidente)
   e um teste de robustez (o 1º colocado se mantém se tirarmos os temas/eixo de maior
   concordância?).

Nada é salvo em banco de dados — todo o cálculo acontece por requisição.

## PDF do resultado e notificação ao administrador

Na página inicial, antes do quiz, a pessoa informa nome e e-mail. Ao final do teste:

- Ela pode **baixar um PDF** do próprio resultado direto na tela (botão "Baixar PDF
  do resultado") — gerado por `engine/pdf.py` (via `reportlab`, sem depender de
  Chrome/wkhtmltopdf) a partir dos mesmos dados já exibidos na tela, então bate
  exatamente com o que ela viu.
- Em paralelo, o backend manda um e-mail curto pro administrador do projeto
  (`ADMIN_EMAIL`, padrão `abwgomes@gmail.com`) com nome, e-mail e data/hora de quem
  respondeu, e o PDF do resultado em anexo — via `engine/email_service.py`, API do
  **Resend** (HTTPS — Render bloqueia SMTP de saída em contas free).
- Se esse e-mail falhar por qualquer motivo, o resultado na tela e o download do PDF
  continuam funcionando normal — é best-effort, só pro administrador saber quem
  respondeu.

Não mandamos o PDF por e-mail pra quem respondeu o teste — o Resend, sem um domínio
verificado em [resend.com/domains](https://resend.com/domains), só entrega e-mail de
verdade pro endereço que criou a conta (a API aceita qualquer destinatário e devolve
200, mas não chega na caixa de entrada de outra pessoa). Por isso o caminho escolhido
foi o download direto na tela, que não depende disso.

Variáveis de ambiente usadas: `RESEND_API_KEY` (obrigatória pra notificar o
administrador), `RESEND_FROM` (opcional, remetente customizado) e `ADMIN_EMAIL`
(opcional, padrão `abwgomes@gmail.com`).

## Dados dos candidatos

- `data/candidatos.json` — 13 candidatos a Presidente com candidatura oficializada
  (fonte: TSE/DivulgaCand, planos de governo registrados e imprensa, coletado em
  25/08/2026), com posição por tema (16 temas).
- `data/candidatos_governador_rs.json` — 7 candidatos a Governador do RS, perfil
  resumido (6 eixos macro).
- `data/candidatos_senador_rs.json` — 13 candidatos às 2 vagas de Senador pelo RS
  em disputa em 2026, perfil resumido (6 eixos macro). No Senado o eleitor vota em
  2 nomes diferentes; são eleitos os 2 mais votados, sem 2º turno.

Cada tema/eixo de cada candidato tem um `score` (-2 a 2), um nível de `confianca` e
uma `nota` com a fonte da informação. Quando não foi possível confirmar a posição de
um candidato, o `score` fica `null` e isso aparece no resultado como "Não foi possível
determinar com segurança" — não entra no cálculo daquele candidato.

⚠️ **Isso precisa ser atualizado conforme a campanha avança** (novos planos de
governo, mudanças de candidatura, decisões judiciais como a de Pablo Marçal/PRTB,
etc). Edite os JSONs diretamente — não tem painel administrativo.

## Rodando localmente

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Acesse `http://localhost:5000`. Configure `ANTHROPIC_API_KEY` no `.env` pra habilitar
a narrativa gerada por IA (opcional — sem isso o app funciona com fallback local).

## Deploy no Render

Já tem `Procfile` e `render.yaml` prontos. Basta conectar o repositório no Render e
configurar a env var `ANTHROPIC_API_KEY` no painel (não versionada, fica só no `.env`
local).

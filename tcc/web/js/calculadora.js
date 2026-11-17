// calculadora.js — Liga o frontend (calculadora.html) ao backend Flask
// Cada função lê os inputs do HTML, chama o endpoint correspondente
// e exibe o resultado no card-result correto.

const API = ''; // mesma origem — Flask serve o HTML e a API juntos

// ─── Utilitários ─────────────────────────────────────────────────────────────

function fmt(n) {
  return 'R$ ' + Number(n).toFixed(2).replace('.', ',');
}

function mostrar(idResult, html) {
  const el = document.getElementById(idResult);
  el.innerHTML = html;
  el.classList.add('visible');
}

function erro(idResult, msg) {
  mostrar(idResult, `<div class="result-line"><span class="lbl">⚠ Erro</span><span class="val neg">${msg}</span></div>`);
}

async function chamarAPI(endpoint, body) {
  const resp = await fetch(API + endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (resp.status === 401) { window.location.href = '/pages/login.html'; }
  return resp.json();
}

async function sair() {
  try { await fetch('/api/logout', { method: 'POST' }); } catch {}
  window.location.href = '/pages/login.html';
}

// ─── Card 01 — Lucro por Unidade ─────────────────────────────────────────────

async function calcLucroUnidade() {
  const custo       = parseFloat(document.getElementById('l-custo').value);
  const preco_venda = parseFloat(document.getElementById('l-preco').value);

  if (!custo || !preco_venda) {
    erro('r-lucro', 'Preencha custo e preço de venda.');
    return;
  }

  try {
    const data = await chamarAPI('/api/lucro-unidade', { custo, preco_venda });
    if (!data.sucesso) { erro('r-lucro', data.erro); return; }

    const cor = data.lucro >= 0 ? 'pos' : 'neg';
    mostrar('r-lucro', `
      <div class="result-line">
        <span class="lbl">Lucro por unidade</span>
        <span class="val ${cor}">${fmt(data.lucro)}</span>
      </div>`);
  } catch {
    erro('r-lucro', 'Não foi possível conectar ao servidor.');
  }
}

// ─── Card 02 — Percentual de Lucro ───────────────────────────────────────────

async function calcPercentual() {
  const custo       = parseFloat(document.getElementById('p-custo').value);
  const preco_venda = parseFloat(document.getElementById('p-preco').value);

  if (!custo || !preco_venda) {
    erro('r-pct', 'Preencha custo e preço de venda.');
    return;
  }

  try {
    const data = await chamarAPI('/api/percentual-lucro', { custo, preco_venda });
    if (!data.sucesso) { erro('r-pct', data.erro); return; }

    const cor = data.percentual >= 0 ? 'pos' : 'neg';
    mostrar('r-pct', `
      <div class="result-line">
        <span class="lbl">Percentual de lucro</span>
        <span class="val ${cor}">${Number(data.percentual).toFixed(2).replace('.', ',')}%</span>
      </div>`);
  } catch {
    erro('r-pct', 'Não foi possível conectar ao servidor.');
  }
}

// ─── Card 03 — Totais de Vendas ───────────────────────────────────────────────

async function calcTotais() {
  const custo       = parseFloat(document.getElementById('t-custo').value);
  const preco_venda = parseFloat(document.getElementById('t-preco').value);
  const quantidade  = parseFloat(document.getElementById('t-qtd').value);

  if (!custo || !preco_venda || !quantidade) {
    erro('r-totais', 'Preencha todos os campos.');
    return;
  }

  try {
    const data = await chamarAPI('/api/vendas-totais', { custo, preco_venda, quantidade });
    if (!data.sucesso) { erro('r-totais', data.erro); return; }

    const corLucro = data.lucro_total >= 0 ? 'pos' : 'neg';
    mostrar('r-totais', `
      <div class="result-line">
        <span class="lbl">Receita total</span>
        <span class="val">${fmt(data.receita_total)}</span>
      </div>
      <div class="result-line">
        <span class="lbl">Custo total</span>
        <span class="val">${fmt(data.custo_total)}</span>
      </div>
      <div class="result-line">
        <span class="lbl">Lucro total</span>
        <span class="val ${corLucro}">${fmt(data.lucro_total)}</span>
      </div>
      <div class="result-line">
        <span class="lbl">% Lucro</span>
        <span class="val ${corLucro}">${Number(data.percentual_lucro).toFixed(2).replace('.', ',')}%</span>
      </div>`);
  } catch {
    erro('r-totais', 'Não foi possível conectar ao servidor.');
  }
}

// ─── Card 04 — Preço por Markup ──────────────────────────────────────────────

async function calcMarkup() {
  const custo          = parseFloat(document.getElementById('m-custo').value);
  const markup_percent = parseFloat(document.getElementById('m-markup').value);

  if (custo === undefined || isNaN(custo) || markup_percent === undefined || isNaN(markup_percent)) {
    erro('r-markup', 'Preencha custo e markup.');
    return;
  }

  try {
    const data = await chamarAPI('/api/markup', { custo, markup_percent });
    if (!data.sucesso) { erro('r-markup', data.erro); return; }

    mostrar('r-markup', `
      <div class="result-line">
        <span class="lbl">Preço de venda sugerido</span>
        <span class="val pos">${fmt(data.preco_venda)}</span>
      </div>`);
  } catch {
    erro('r-markup', 'Não foi possível conectar ao servidor.');
  }
}

// ─── Enter key nos inputs ─────────────────────────────────────────────────────

document.addEventListener('keydown', (e) => {
  if (e.key !== 'Enter') return;
  const id = document.activeElement?.id;
  if (id === 'l-custo' || id === 'l-preco')           calcLucroUnidade();
  else if (id === 'p-custo' || id === 'p-preco')       calcPercentual();
  else if (id === 't-custo' || id === 't-preco' || id === 't-qtd') calcTotais();
  else if (id === 'm-custo' || id === 'm-markup')      calcMarkup();
});

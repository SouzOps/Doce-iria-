// equipe.js — Abas "Pessoal" e "Equipe" do painel.
// Usa fmt(), fmtData() e showMsg() definidas no main.html.

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function chamar(url, metodo = 'GET', corpo) {
  const res = await fetch(url, {
    method: metodo,
    headers: { 'Content-Type': 'application/json' },
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
  if (res.status === 401) { window.location.href = '/pages/login.html'; throw new Error('401'); }
  return res.json();
}

// ─── Abas ────────────────────────────────────────────────────────────────────

function abrirAba(nome) {
  const equipe = nome === 'equipe';
  document.getElementById('aba-pessoal').hidden = equipe;
  document.getElementById('aba-equipe').hidden = !equipe;
  document.getElementById('tab-pessoal').classList.toggle('ativa', !equipe);
  document.getElementById('tab-equipe').classList.toggle('ativa', equipe);
  history.replaceState(null, '', equipe ? '#equipe' : location.pathname);
  if (equipe) carregarEquipe();
}
document.getElementById('tab-pessoal').onclick = () => abrirAba('pessoal');
document.getElementById('tab-equipe').onclick  = () => abrirAba('equipe');

// ─── Carregar e desenhar ─────────────────────────────────────────────────────

async function carregarEquipe() {
  let d;
  try {
    d = await chamar('/api/equipe');
  } catch { 
    document.getElementById('eq-carregando').textContent = 'Não foi possível conectar ao servidor.';
    return;
  }
  document.getElementById('eq-carregando').hidden = true;

  // convites recebidos (aparecem com ou sem equipe) + selo na aba
  const recebidos = d.convites_recebidos || [];
  const badge = document.getElementById('badge-convites');
  badge.hidden = recebidos.length === 0;
  badge.textContent = recebidos.length;
  document.getElementById('eq-convites').hidden = recebidos.length === 0;
  document.getElementById('eq-lista-convites').innerHTML = recebidos.map((c) => `
    <li class="eq-li">
      <span class="eq-pessoa">${esc(c.de)} convidou você para <strong>${esc(c.equipe)}</strong></span>
      <button class="btn-venda btn-mini" onclick="responderConvite(${c.id}, true)">Aceitar</button>
      <button class="btn-mini sec" onclick="responderConvite(${c.id}, false)">Recusar</button>
    </li>`).join('');

  const temEquipe = !!d.equipe;
  document.getElementById('eq-criar').hidden = temEquipe;
  document.getElementById('eq-painel').hidden = !temEquipe;
  if (!temEquipe) return;

  document.getElementById('eq-titulo').textContent = d.equipe.nome;
  document.getElementById('eqVendas').textContent = fmt(d.totais.vendas);
  document.getElementById('eqGastos').textContent = fmt(d.totais.gastos);
  const lucro = document.getElementById('eqLucro');
  lucro.textContent = fmt(d.totais.lucro);
  lucro.className = 'valor ' + (d.totais.lucro > 0 ? 'pos' : d.totais.lucro < 0 ? 'neg' : '');

  document.getElementById('eq-membros').innerHTML = d.membros.map((m) => `
    <li class="eq-li">
      <span class="eq-pessoa">${esc(m.email)}${m.eu ? '<span class="eq-tag">você</span>' : ''}${m.ativo ? '' : '<span class="eq-tag">saiu da equipe</span>'}</span>
      <span class="eq-num">Vendas <b>${fmt(m.vendas)}</b></span>
      <span class="eq-num">Gastos <b>${fmt(m.gastos)}</b></span>
      <span class="eq-num">Lucro <b>${fmt(m.lucro)}</b></span>
    </li>`).join('');

  document.getElementById('eq-enviados').innerHTML = (d.convites_enviados || []).map((c) => `
    <li class="eq-li">
      <span class="eq-pessoa">${esc(c.email)} <span class="eq-tag">aguardando</span></span>
      <button class="btn-mini sec" onclick="responderConvite(${c.id}, false)">Cancelar</button>
    </li>`).join('');

  const hist = document.getElementById('eq-historico');
  hist.innerHTML = d.historico.length === 0
    ? '<li class="empty">Nenhum registro na equipe ainda.</li>'
    : d.historico.map((r) => {
        const venda = r.tipo === 'Venda';
        return `<li>
          <span class="pill ${venda ? 'venda' : 'gasto'}"></span>
          <span class="li-desc">${esc(r.autor)}${r.meu ? '<span class="eq-tag">você</span>' : ''} · ${esc(r.tipo)}</span>
          <span class="li-hora">${fmtData(r.criado_em)}</span>
          <span class="li-val ${venda ? 'venda' : 'gasto'}">${venda ? '+' : '−'} ${fmt(r.valor)}</span>
          ${r.meu ? `<button class="del" title="Remover" onclick="removerEquipe(${r.id})">×</button>` : '<span style="width:30px"></span>'}
        </li>`;
      }).join('');
}

// ─── Ações ───────────────────────────────────────────────────────────────────

async function criarEquipe() {
  const nome = document.getElementById('eq-nome').value.trim();
  if (!nome) { showMsg('msg-criar', 'Dê um nome para a equipe.', false); return; }
  try {
    const d = await chamar('/api/equipe', 'POST', { nome });
    if (!d.sucesso) { showMsg('msg-criar', d.erro, false); return; }
    document.getElementById('eq-nome').value = '';
    await carregarEquipe();
  } catch { showMsg('msg-criar', 'Erro ao conectar com o servidor.', false); }
}

async function convidar() {
  const campo = document.getElementById('eq-email');
  const email = campo.value.trim();
  if (!email) { showMsg('msg-convidar', 'Digite o e-mail da pessoa.', false); return; }
  try {
    const d = await chamar('/api/equipe/convidar', 'POST', { email });
    if (!d.sucesso) { showMsg('msg-convidar', d.erro, false); return; }
    campo.value = '';
    showMsg('msg-convidar', 'Convite enviado! A pessoa verá na aba Equipe dela.', true);
    await carregarEquipe();
  } catch { showMsg('msg-convidar', 'Erro ao conectar com o servidor.', false); }
}

async function responderConvite(id, aceitar) {
  try {
    const d = aceitar
      ? await chamar(`/api/equipe/convites/${id}/aceitar`, 'POST')
      : await chamar(`/api/equipe/convites/${id}`, 'DELETE');
    if (!d.sucesso) { showMsg('msg-convites', d.erro, false); alert(d.erro); return; }
    await carregarEquipe();
  } catch { alert('Erro ao conectar com o servidor.'); }
}

async function registrarEquipe(tipo) {
  const campo = document.getElementById(tipo === 'venda' ? 'eq-valorVenda' : 'eq-valorGasto');
  const msgId = tipo === 'venda' ? 'msg-eq-venda' : 'msg-eq-gasto';
  const valor = parseFloat(campo.value);
  if (!valor || valor <= 0) { campo.focus(); showMsg(msgId, 'Digite um valor maior que zero.', false); return; }
  try {
    const d = await chamar(tipo === 'venda' ? '/api/venda' : '/api/gasto', 'POST', { valor, escopo: 'equipe' });
    if (!d.sucesso) { showMsg(msgId, d.erro, false); return; }
    campo.value = '';
    showMsg(msgId, tipo === 'venda' ? 'Venda registrada na equipe!' : 'Gasto registrado na equipe!', true);
    await carregarEquipe();
  } catch { showMsg(msgId, 'Erro ao conectar com o servidor.', false); }
}

async function removerEquipe(id) {
  try {
    await chamar('/api/transacao/' + id, 'DELETE');
    await carregarEquipe();
  } catch { alert('Erro ao conectar com o servidor.'); }
}

async function sairEquipe() {
  if (!confirm('Sair da equipe? Os registros que você fez continuam na equipe. Se você for a última pessoa, a equipe e seus registros serão apagados.')) return;
  try {
    const d = await chamar('/api/equipe/sair', 'POST');
    if (!d.sucesso) { alert(d.erro); return; }
    await carregarEquipe();
  } catch { alert('Erro ao conectar com o servidor.'); }
}

document.addEventListener('keydown', (e) => {
  if (e.key !== 'Enter') return;
  const id = document.activeElement.id;
  if (id === 'eq-valorVenda') registrarEquipe('venda');
  else if (id === 'eq-valorGasto') registrarEquipe('gasto');
  else if (id === 'eq-email') convidar();
  else if (id === 'eq-nome') criarEquipe();
});

// Ao abrir o painel: mostra o selo de convites e respeita o endereço #equipe
if (location.hash === '#equipe') abrirAba('equipe'); else carregarEquipe();

// Se o endereço mudar para #equipe (ou voltar), troca de aba também
window.addEventListener('hashchange', () => abrirAba(location.hash === '#equipe' ? 'equipe' : 'pessoal'));

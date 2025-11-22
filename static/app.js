function alertBox(msg, type = 'info') {
  document.getElementById('alert-area').innerHTML = `<div class="alert alert-${type} mt-2">${msg}</div>`;
}

async function loadInfractions() {
  try {
    const res = await fetch('/infractions');
    const data = await res.json();
    const list = document.getElementById('infraction-list');
    const search = document.getElementById('searchPlate').value.trim().toUpperCase();
    list.innerHTML = '';
    let shown = 0;
    (data.infractions || []).slice().reverse().forEach(item => {
      if (search && !item.placa.toUpperCase().includes(search)) return;
      const li = document.createElement('li');
      li.className = 'list-group-item';
      li.innerHTML = `<strong>${item.tipo || ''}</strong> — <em>${item.placa}</em><br>
                      <small>${item.data}</small><br>
                      ${item.valor ? 'Valor: R$ ' + Number(item.valor).toFixed(2) + '<br>' : ''}
                      Status: ${item.status || ''}`;
      list.appendChild(li);
      shown++;
    });
    if (shown === 0) alertBox('Sem infrações encontradas', 'secondary'); else alertBox(shown + ' infração(ões) exibida(s)', 'primary');
  } catch (e) {
    console.error(e);
    alertBox('Erro ao carregar infrações', 'danger');
  }
}

async function simulateInfraction() {
  try {
    const res = await fetch('/simulate/new_infraction');
    const js = await res.json();
    alertBox('🔥 Nova infração detectada (simulada)!', 'warning');
    loadInfractions();
  } catch (e) {
    alertBox('Erro ao simular infração', 'danger');
  }
}

async function simulateFailure() {
  try {
    const res = await fetch('/simulate/api_failure');
    if (!res.ok) throw new Error('API não disponível');
    await res.json();
  } catch (e) {
    alertBox('⚠️ Falha simulada: ' + (e.message || ''), 'danger');
  }
}

async function enviar() {
  const placa = document.getElementById('placa').value.trim();
  const valor = document.getElementById('valor').value;
  const tipo = document.getElementById('tipo').value.trim() || 'Não especificado';
  if (!placa || !valor) { alertBox('Preencha placa e valor', 'warning'); return; }
  try {
    const res = await fetch('/nova_infracao', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ placa, valor, tipo })
    });
    const data = await res.json();
    document.getElementById('resposta').style.display = 'block';
    document.getElementById('resposta').innerText = JSON.stringify(data, null, 2);
    if (res.ok) {
      alertBox('Infração registrada com sucesso', 'success');
      loadInfractions();
    } else {
      alertBox(data.erro || 'Erro ao registrar', 'danger');
    }
  } catch (e) {
    console.error(e);
    alertBox('Erro de comunicação', 'danger');
  }
}

setInterval(loadInfractions, 5000);
window.addEventListener('load', loadInfractions);

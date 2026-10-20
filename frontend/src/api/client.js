const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    const detail = data?.detail || data?.message || text || res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

export const api = {
  health: () => request("/health"),
  produtores: (apenasAtivos = true) =>
    request(`/produtores?apenas_ativos=${apenasAtivos}`),
  criarProdutor: (body) =>
    request("/produtores", { method: "POST", body: JSON.stringify(body) }),
  atualizarProdutor: (id, body) =>
    request(`/produtores/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  propriedades: () => request("/propriedades"),
  propriedade: (id) => request(`/propriedades/${id}`),
  criarPropriedade: (body) =>
    request("/propriedades", { method: "POST", body: JSON.stringify(body) }),
  atualizarPropriedade: (id, body) =>
    request(`/propriedades/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  tiposVinculo: () => request("/vinculos/tipos"),
  adicionarVinculo: (propriedadeId, body) =>
    request(`/propriedades/${propriedadeId}/vinculos`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  removerVinculo: (propriedadeId, vinculoId) =>
    request(`/propriedades/${propriedadeId}/vinculos/${vinculoId}`, { method: "DELETE" }),
  veterinarios: (apenasAtivos = true) =>
    request(`/veterinarios?apenas_ativos=${apenasAtivos}`),
  criarVeterinario: (body) =>
    request("/veterinarios", { method: "POST", body: JSON.stringify(body) }),
  atualizarVeterinario: (id, body) =>
    request(`/veterinarios/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  saldo: (exploracaoId) => request(`/exploracoes/${exploracaoId}/saldo`),
  animais: (exploracaoId) => request(`/exploracoes/${exploracaoId}/animais`),
  nascimento: (body) =>
    request("/exploracoes/nascimentos", { method: "POST", body: JSON.stringify(body) }),
  morte: (body) =>
    request("/exploracoes/mortes", { method: "POST", body: JSON.stringify(body) }),
  declaracoes: (exploracaoId) =>
    request(`/declaracoes?exploracao_id=${exploracaoId}`),
  filaMortalidade: () => request("/oesa/fila-mortalidade"),
  homologar: (id, aprovar) =>
    request(`/oesa/declaracoes/${id}/homologar`, {
      method: "POST",
      body: JSON.stringify({ aprovar }),
    }),
  estoque: (propriedadeId) => request(`/propriedades/${propriedadeId}/estoque-ids`),
  aplicarIds: (body) =>
    request("/identificacao/aplicar", { method: "POST", body: JSON.stringify(body) }),
  emitirGta: (body) => request("/gtas", { method: "POST", body: JSON.stringify(body) }),
  gtas: () => request("/gtas"),
  vacinar: (body) =>
    request("/vacinacoes/brucelose", { method: "POST", body: JSON.stringify(body) }),
};

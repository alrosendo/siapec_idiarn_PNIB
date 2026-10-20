<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { api } from "../api/client";

const tab = ref("propriedades");
const erro = ref("");
const msg = ref("");
const loading = ref(false);

const propriedades = ref([]);
const produtores = ref([]);
const veterinarios = ref([]);
const tipos = ref([]);
const detalhe = ref(null);
const propSelecionada = ref(null);

const formProdutor = ref({ cpf_cnpj: "", nome: "", telefone: "", email: "" });
const formProp = ref({
  codigo: "",
  nome: "",
  municipio: "",
  uf: "RN",
  produtor_id: null,
});
const formVet = ref({
  crmv: "",
  uf_crmv: "RN",
  nome: "",
  cpf: "",
  telefone: "",
  email: "",
});
const formVinculo = ref({
  produtor_id: null,
  tipo_vinculo: "parceiro",
  observacao: "",
});

const rotulosTipo = {
  proprietario: "Proprietário",
  arrendatario: "Arrendatário",
  parceiro: "Parceiro",
  comodato: "Comodato",
  posseiro: "Posseiro",
  administrador: "Administrador",
  outro: "Outro",
};

const vinculosPorTipo = computed(() => {
  const map = {};
  for (const t of tipos.value) map[t] = [];
  for (const v of detalhe.value?.vinculos || []) {
    if (!map[v.tipo_vinculo]) map[v.tipo_vinculo] = [];
    map[v.tipo_vinculo].push(v);
  }
  return map;
});

const produtoresDisponiveis = computed(() => {
  const ja = new Set(
    (detalhe.value?.vinculos || [])
      .filter((v) => v.tipo_vinculo === formVinculo.value.tipo_vinculo)
      .map((v) => v.produtor_id)
  );
  return produtores.value.filter((p) => !ja.has(p.id));
});

function flash(ok, text) {
  msg.value = ok ? text : "";
  erro.value = ok ? "" : text;
}

async function carregarBase() {
  erro.value = "";
  try {
    const [props, prods, vets, t] = await Promise.all([
      api.propriedades(),
      api.produtores(),
      api.veterinarios(),
      api.tiposVinculo(),
    ]);
    propriedades.value = props;
    produtores.value = prods;
    veterinarios.value = vets;
    tipos.value = t;
    if (!formProp.value.produtor_id && prods.length) {
      formProp.value.produtor_id = prods[0].id;
    }
    if (!formVinculo.value.produtor_id && prods.length) {
      formVinculo.value.produtor_id = prods[0].id;
    }
    if (!propSelecionada.value && props.length) {
      await abrirPropriedade(props[0].id);
    } else if (propSelecionada.value) {
      await abrirPropriedade(propSelecionada.value);
    }
  } catch (e) {
    flash(false, e.message);
  }
}

async function abrirPropriedade(id) {
  propSelecionada.value = id;
  detalhe.value = await api.propriedade(id);
}

async function criarProdutor() {
  loading.value = true;
  try {
    const p = await api.criarProdutor({ ...formProdutor.value });
    flash(true, `Produtor ${p.nome} cadastrado`);
    formProdutor.value = { cpf_cnpj: "", nome: "", telefone: "", email: "" };
    await carregarBase();
  } catch (e) {
    flash(false, e.message);
  } finally {
    loading.value = false;
  }
}

async function criarPropriedade() {
  loading.value = true;
  try {
    const p = await api.criarPropriedade({
      ...formProp.value,
      produtor_id: Number(formProp.value.produtor_id),
    });
    flash(true, `Propriedade ${p.codigo} criada`);
    formProp.value = {
      codigo: "",
      nome: "",
      municipio: "",
      uf: "RN",
      produtor_id: produtores.value[0]?.id || null,
    };
    await carregarBase();
    await abrirPropriedade(p.id);
    tab.value = "propriedades";
  } catch (e) {
    flash(false, e.message);
  } finally {
    loading.value = false;
  }
}

async function criarVet() {
  loading.value = true;
  try {
    const v = await api.criarVeterinario({ ...formVet.value });
    flash(true, `RT ${v.nome} cadastrado`);
    formVet.value = {
      crmv: "",
      uf_crmv: "RN",
      nome: "",
      cpf: "",
      telefone: "",
      email: "",
    };
    await carregarBase();
  } catch (e) {
    flash(false, e.message);
  } finally {
    loading.value = false;
  }
}

async function incluirVinculo() {
  if (!propSelecionada.value) return;
  loading.value = true;
  try {
    await api.adicionarVinculo(propSelecionada.value, {
      produtor_id: Number(formVinculo.value.produtor_id),
      tipo_vinculo: formVinculo.value.tipo_vinculo,
      observacao: formVinculo.value.observacao || null,
    });
    flash(true, "Vínculo incluído");
    formVinculo.value.observacao = "";
    await abrirPropriedade(propSelecionada.value);
    propriedades.value = await api.propriedades();
  } catch (e) {
    flash(false, e.message);
  } finally {
    loading.value = false;
  }
}

async function excluirVinculo(v) {
  const ok = confirm(
    `Remover ${rotulosTipo[v.tipo_vinculo] || v.tipo_vinculo}: ${v.produtor_nome}?`
  );
  if (!ok) return;
  loading.value = true;
  try {
    await api.removerVinculo(propSelecionada.value, v.id);
    flash(true, "Vínculo removido (inativado)");
    await abrirPropriedade(propSelecionada.value);
    propriedades.value = await api.propriedades();
  } catch (e) {
    flash(false, e.message);
  } finally {
    loading.value = false;
  }
}

watch(
  () => formVinculo.value.tipo_vinculo,
  () => {
    const disp = produtoresDisponiveis.value;
    if (disp.length && !disp.find((p) => p.id === Number(formVinculo.value.produtor_id))) {
      formVinculo.value.produtor_id = disp[0].id;
    }
  }
);

onMounted(carregarBase);
</script>

<template>
  <div class="stack">
    <div v-if="erro" class="banner err">{{ erro }}</div>
    <div v-if="msg" class="banner ok">{{ msg }}</div>

    <section class="panel">
      <h2 style="margin-top: 0; font-family: var(--display)">Cadastros</h2>
      <p class="muted">
        Controle de produtores, propriedades e veterinários (RT). Na propriedade, gerencie
        proprietário, arrendatário, parceiros e demais vínculos.
      </p>
      <div class="tabs">
        <button
          class="tab"
          :class="{ on: tab === 'propriedades' }"
          @click="tab = 'propriedades'"
        >
          Propriedades e vínculos
        </button>
        <button class="tab" :class="{ on: tab === 'produtores' }" @click="tab = 'produtores'">
          Produtores
        </button>
        <button class="tab" :class="{ on: tab === 'veterinarios' }" @click="tab = 'veterinarios'">
          Veterinários (RT)
        </button>
      </div>
    </section>

    <!-- PROPRIEDADES + VÍNCULOS -->
    <div v-show="tab === 'propriedades'" class="cad-grid">
      <aside class="panel">
        <h3 style="margin-top: 0">Propriedades</h3>
        <button
          v-for="p in propriedades"
          :key="p.id"
          class="prop-item"
          :class="{ on: propSelecionada === p.id }"
          @click="abrirPropriedade(p.id)"
        >
          <strong>{{ p.codigo }}</strong>
          <span>{{ p.nome }}</span>
          <small class="muted">{{ p.municipio }}/{{ p.uf }} · {{ p.titular_nome }}</small>
        </button>

        <hr class="sep" />
        <h4>Nova propriedade</h4>
        <div class="stack-sm">
          <div class="field">
            <label>Código</label>
            <input v-model="formProp.codigo" placeholder="PROP-RN-002" />
          </div>
          <div class="field">
            <label>Nome</label>
            <input v-model="formProp.nome" />
          </div>
          <div class="field">
            <label>Município</label>
            <input v-model="formProp.municipio" />
          </div>
          <div class="field">
            <label>UF</label>
            <input v-model="formProp.uf" maxlength="2" />
          </div>
          <div class="field">
            <label>Titular (proprietário inicial)</label>
            <select v-model.number="formProp.produtor_id">
              <option v-for="pr in produtores" :key="pr.id" :value="pr.id">
                {{ pr.nome }} — {{ pr.cpf_cnpj }}
              </option>
            </select>
          </div>
          <button class="btn" :disabled="loading" @click="criarPropriedade">Cadastrar</button>
        </div>
      </aside>

      <section class="panel" v-if="detalhe">
        <div class="row" style="justify-content: space-between; align-items: start">
          <div>
            <h3 style="margin: 0; font-family: var(--display)">{{ detalhe.nome }}</h3>
            <p class="muted" style="margin: 0.35rem 0 0">
              {{ detalhe.codigo }} · {{ detalhe.municipio }}/{{ detalhe.uf }}
              <span v-if="detalhe.interditada" class="badge" style="margin-left: 0.4rem">interditada</span>
            </p>
          </div>
          <span class="badge">{{ detalhe.vinculos?.length || 0 }} vínculo(s) ativo(s)</span>
        </div>

        <div class="vinculo-board">
          <div v-for="tipo in tipos" :key="tipo" class="vinculo-col">
            <header>
              <strong>{{ rotulosTipo[tipo] || tipo }}</strong>
              <span class="count">{{ (vinculosPorTipo[tipo] || []).length }}</span>
            </header>
            <div
              v-for="v in vinculosPorTipo[tipo] || []"
              :key="v.id"
              class="vinculo-card"
            >
              <div>
                <strong>{{ v.produtor_nome }}</strong>
                <small class="muted">{{ v.produtor_cpf_cnpj }}</small>
                <small v-if="v.observacao" class="muted">{{ v.observacao }}</small>
              </div>
              <button
                class="btn-icon"
                title="Excluir vínculo"
                :disabled="loading"
                @click="excluirVinculo(v)"
              >
                ✕
              </button>
            </div>
            <p v-if="!(vinculosPorTipo[tipo] || []).length" class="empty">Nenhum</p>
          </div>
        </div>

        <div class="incluir-box">
          <h4 style="margin-top: 0">Incluir vínculo</h4>
          <div class="row">
            <div class="field" style="min-width: 160px">
              <label>Tipo</label>
              <select v-model="formVinculo.tipo_vinculo">
                <option v-for="t in tipos" :key="t" :value="t">
                  {{ rotulosTipo[t] || t }}
                </option>
              </select>
            </div>
            <div class="field" style="min-width: 260px; flex: 1">
              <label>Produtor</label>
              <select v-model.number="formVinculo.produtor_id">
                <option v-for="p in produtoresDisponiveis" :key="p.id" :value="p.id">
                  {{ p.nome }} — {{ p.cpf_cnpj }}
                </option>
              </select>
            </div>
            <div class="field" style="min-width: 180px; flex: 1">
              <label>Observação</label>
              <input v-model="formVinculo.observacao" placeholder="Contrato, % parceria…" />
            </div>
            <button class="btn" :disabled="loading || !produtoresDisponiveis.length" @click="incluirVinculo">
              Incluir
            </button>
          </div>
          <p v-if="!produtoresDisponiveis.length" class="muted" style="margin: 0.5rem 0 0">
            Todos os produtores já estão neste tipo — cadastre outro na aba Produtores.
          </p>
        </div>
      </section>

      <section v-else class="panel">
        <p class="muted">Selecione uma propriedade à esquerda.</p>
      </section>
    </div>

    <!-- PRODUTORES -->
    <section v-show="tab === 'produtores'" class="panel">
      <h3 style="margin-top: 0">Produtores cadastrados</h3>
      <table>
        <thead>
          <tr>
            <th>Nome</th>
            <th>CPF/CNPJ</th>
            <th>Telefone</th>
            <th>E-mail</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in produtores" :key="p.id">
            <td>{{ p.nome }}</td>
            <td>{{ p.cpf_cnpj }}</td>
            <td>{{ p.telefone || "—" }}</td>
            <td>{{ p.email || "—" }}</td>
            <td><span class="badge">{{ p.ativo ? "ativo" : "inativo" }}</span></td>
          </tr>
        </tbody>
      </table>

      <h4>Novo produtor</h4>
      <div class="row">
        <div class="field">
          <label>CPF/CNPJ</label>
          <input v-model="formProdutor.cpf_cnpj" />
        </div>
        <div class="field" style="min-width: 220px">
          <label>Nome</label>
          <input v-model="formProdutor.nome" />
        </div>
        <div class="field">
          <label>Telefone</label>
          <input v-model="formProdutor.telefone" />
        </div>
        <div class="field">
          <label>E-mail</label>
          <input v-model="formProdutor.email" />
        </div>
        <button class="btn" :disabled="loading" @click="criarProdutor">Cadastrar</button>
      </div>
    </section>

    <!-- VETERINÁRIOS -->
    <section v-show="tab === 'veterinarios'" class="panel">
      <h3 style="margin-top: 0">Veterinários (RT)</h3>
      <table>
        <thead>
          <tr>
            <th>Nome</th>
            <th>CRMV</th>
            <th>UF</th>
            <th>CPF</th>
            <th>Telefone</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in veterinarios" :key="v.id">
            <td>{{ v.nome }}</td>
            <td>{{ v.crmv }}</td>
            <td>{{ v.uf_crmv }}</td>
            <td>{{ v.cpf || "—" }}</td>
            <td>{{ v.telefone || "—" }}</td>
            <td><span class="badge">{{ v.ativo ? "ativo" : "inativo" }}</span></td>
          </tr>
        </tbody>
      </table>

      <h4>Novo RT</h4>
      <div class="row">
        <div class="field">
          <label>CRMV</label>
          <input v-model="formVet.crmv" />
        </div>
        <div class="field">
          <label>UF</label>
          <input v-model="formVet.uf_crmv" maxlength="2" />
        </div>
        <div class="field" style="min-width: 220px">
          <label>Nome</label>
          <input v-model="formVet.nome" />
        </div>
        <div class="field">
          <label>CPF</label>
          <input v-model="formVet.cpf" />
        </div>
        <div class="field">
          <label>Telefone</label>
          <input v-model="formVet.telefone" />
        </div>
        <button class="btn" :disabled="loading" @click="criarVet">Cadastrar</button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-top: 1rem;
}
.tab {
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 999px;
  padding: 0.45rem 0.9rem;
  cursor: pointer;
  color: var(--muted);
}
.tab.on {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  font-weight: 600;
}
.cad-grid {
  display: grid;
  grid-template-columns: minmax(260px, 320px) 1fr;
  gap: 1rem;
  align-items: start;
}
@media (max-width: 900px) {
  .cad-grid {
    grid-template-columns: 1fr;
  }
}
.prop-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
  width: 100%;
  text-align: left;
  border: 1px solid var(--line);
  background: #fff;
  border-radius: 12px;
  padding: 0.7rem 0.8rem;
  margin-bottom: 0.45rem;
  cursor: pointer;
}
.prop-item.on {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(47, 107, 58, 0.15);
}
.sep {
  border: 0;
  border-top: 1px solid var(--line);
  margin: 1rem 0;
}
.stack-sm {
  display: grid;
  gap: 0.55rem;
}
.vinculo-board {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
  margin: 1.25rem 0;
}
.vinculo-col {
  background: linear-gradient(180deg, #fff, var(--bg-deep));
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 0.7rem;
  min-height: 120px;
}
.vinculo-col header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.55rem;
  font-size: 0.9rem;
}
.vinculo-col .count {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0.05rem 0.45rem;
  font-size: 0.75rem;
}
.vinculo-card {
  display: flex;
  justify-content: space-between;
  gap: 0.4rem;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.55rem 0.6rem;
  margin-bottom: 0.4rem;
}
.vinculo-card strong {
  display: block;
  font-size: 0.92rem;
}
.vinculo-card small {
  display: block;
  font-size: 0.75rem;
}
.btn-icon {
  border: 0;
  background: #fdecec;
  color: var(--danger);
  width: 28px;
  height: 28px;
  border-radius: 8px;
  cursor: pointer;
  flex-shrink: 0;
  font-weight: 700;
}
.empty {
  color: var(--muted);
  font-size: 0.82rem;
  margin: 0.4rem 0 0;
}
.incluir-box {
  border-top: 1px solid var(--line);
  padding-top: 1rem;
  margin-top: 0.5rem;
}
</style>

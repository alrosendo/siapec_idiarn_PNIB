<script setup>
import { onMounted, ref } from "vue";
import { api } from "../api/client";

const saldo = ref(null);
const animais = ref([]);
const historico = ref([]);
const erro = ref("");
const msg = ref("");
const exploracaoId = ref(1);
const loading = ref(false);

const nasc = ref({
  sexo: "F",
  faixa: "0-12",
  quantidade: 1,
  ids: "",
});

const morte = ref({
  tipo_baixa: "morte",
  sexo: "F",
  faixa: "0-12",
  quantidade: 1,
  ids: "",
  observacao: "",
});

async function carregar() {
  erro.value = "";
  try {
    saldo.value = await api.saldo(exploracaoId.value);
    animais.value = await api.animais(exploracaoId.value);
    historico.value = await api.declaracoes(exploracaoId.value);
  } catch (e) {
    erro.value = e.message;
  }
}

function parseIds(texto) {
  return texto
    .split(/[\n,;\s]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

async function declararNascimento() {
  loading.value = true;
  msg.value = "";
  erro.value = "";
  try {
    const decl = await api.nascimento({
      exploracao_id: exploracaoId.value,
      data_evento: new Date().toISOString().slice(0, 10),
      sexo: nasc.value.sexo,
      faixa: nasc.value.faixa,
      quantidade: nasc.value.quantidade,
      ids_oficiais: parseIds(nasc.value.ids),
    });
    msg.value = `Nascimento #${decl.id} confirmado · ${decl.quantidade} cabeça(s)`;
    nasc.value.ids = "";
    await carregar();
  } catch (e) {
    erro.value = e.message;
  } finally {
    loading.value = false;
  }
}

async function declararMorte() {
  loading.value = true;
  msg.value = "";
  erro.value = "";
  try {
    const ids = parseIds(morte.value.ids);
    const decl = await api.morte({
      exploracao_id: exploracaoId.value,
      data_evento: new Date().toISOString().slice(0, 10),
      tipo_baixa: morte.value.tipo_baixa,
      sexo: ids.length ? null : morte.value.sexo,
      faixa: ids.length ? null : morte.value.faixa,
      quantidade: ids.length ? 0 : morte.value.quantidade,
      ids_oficiais: ids,
      observacao: morte.value.observacao || null,
    });
    const aviso = decl.acima_indice ? " · enviada à fila OESA (acima do índice)" : "";
    msg.value = `Baixa #${decl.id} · ${decl.quantidade} · ${decl.status}${aviso}`;
    morte.value.ids = "";
    await carregar();
  } catch (e) {
    erro.value = e.message;
  } finally {
    loading.value = false;
  }
}

onMounted(carregar);
</script>

<template>
  <div class="stack">
    <div v-if="erro" class="banner err">{{ erro }}</div>
    <div v-if="msg" class="banner ok">{{ msg }}</div>

    <section class="panel">
      <div class="row" style="justify-content: space-between">
        <div>
          <h2 style="margin: 0; font-family: var(--display)">Saldo do rebanho</h2>
          <p class="muted" style="margin: 0.3rem 0 0">Visão híbrida SIAPEC + PNIB</p>
        </div>
        <div class="field">
          <label>Exploração ID</label>
          <input v-model.number="exploracaoId" type="number" min="1" @change="carregar" />
        </div>
      </div>

      <template v-if="saldo">
        <div class="banner" style="margin-top: 1rem">
          {{ saldo.propriedade_nome }} · Etapa PNIB {{ saldo.pnib_etapa }} —
          identificação ainda sob gatilho (não universal)
        </div>
        <div class="grid-stats">
          <div class="stat"><span>Total</span><strong>{{ saldo.total }}</strong></div>
          <div class="stat"><span>Com ID</span><strong>{{ saldo.identificados }}</strong></div>
          <div class="stat"><span>Sem ID</span><strong>{{ saldo.sem_id }}</strong></div>
          <div class="stat"><span>Cobertura</span><strong>{{ saldo.cobertura_pct }}%</strong></div>
        </div>

        <table>
          <thead>
            <tr>
              <th>Sexo</th>
              <th>Faixa</th>
              <th>Saldo</th>
              <th>Com ID</th>
              <th>Sem ID</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in saldo.celulas" :key="`${c.sexo}-${c.faixa}`">
              <td>{{ c.sexo }}</td>
              <td>{{ c.faixa }}</td>
              <td>{{ c.quantidade }}</td>
              <td>{{ c.com_id }}</td>
              <td>{{ c.sem_id }}</td>
            </tr>
          </tbody>
        </table>
      </template>
    </section>

    <section class="panel">
      <h3 style="margin-top: 0">Declarar nascimento</h3>
      <p class="muted">Incrementa saldo na faixa 0–12. Opcional: informar IDs do estoque para identificar já no nascimento.</p>
      <div class="row" style="margin: 0.75rem 0">
        <div class="field">
          <label>Sexo</label>
          <select v-model="nasc.sexo"><option>F</option><option>M</option></select>
        </div>
        <div class="field">
          <label>Faixa</label>
          <select v-model="nasc.faixa"><option>0-12</option></select>
        </div>
        <div class="field">
          <label>Quantidade</label>
          <input v-model.number="nasc.quantidade" type="number" min="1" />
        </div>
      </div>
      <div class="field" style="min-width: 100%">
        <label>IDs oficiais (opcional)</label>
        <textarea
          v-model="nasc.ids"
          rows="2"
          style="width: 100%; border: 1px solid var(--line); border-radius: 10px; padding: 0.6rem"
          placeholder="BR-RN-00001"
        />
      </div>
      <button class="btn" style="margin-top: 0.75rem" :disabled="loading" @click="declararNascimento">
        Gravar nascimento
      </button>
    </section>

    <section class="panel">
      <h3 style="margin-top: 0">Declarar morte / baixa</h3>
      <p class="muted">
        Por faixa (só saldo sem ID) ou por ID. Acima do índice de mortalidade do mês → fila OESA.
      </p>
      <div class="row" style="margin: 0.75rem 0">
        <div class="field">
          <label>Tipo</label>
          <select v-model="morte.tipo_baixa">
            <option value="morte">morte</option>
            <option value="abate">abate</option>
            <option value="desaparecimento">desaparecimento</option>
          </select>
        </div>
        <div class="field">
          <label>Sexo</label>
          <select v-model="morte.sexo"><option>F</option><option>M</option></select>
        </div>
        <div class="field">
          <label>Faixa</label>
          <select v-model="morte.faixa">
            <option>0-12</option>
            <option>13-24</option>
            <option>25-36</option>
            <option>36+</option>
          </select>
        </div>
        <div class="field">
          <label>Quantidade</label>
          <input v-model.number="morte.quantidade" type="number" min="1" />
        </div>
      </div>
      <div class="field" style="min-width: 100%">
        <label>IDs (se informar, ignora sexo/faixa/qtd)</label>
        <textarea
          v-model="morte.ids"
          rows="2"
          style="width: 100%; border: 1px solid var(--line); border-radius: 10px; padding: 0.6rem"
        />
      </div>
      <div class="field" style="min-width: 100%; margin-top: 0.5rem">
        <label>Observação</label>
        <input v-model="morte.observacao" />
      </div>
      <button class="btn" style="margin-top: 0.75rem" :disabled="loading" @click="declararMorte">
        Gravar baixa
      </button>
    </section>

    <section class="panel">
      <h3 style="margin-top: 0">Histórico de declarações</h3>
      <p v-if="!historico.length" class="muted">Nenhuma declaração ainda.</p>
      <table v-else>
        <thead>
          <tr>
            <th>#</th>
            <th>Tipo</th>
            <th>Data</th>
            <th>Detalhe</th>
            <th>Qtd</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in historico" :key="d.id">
            <td>{{ d.id }}</td>
            <td>{{ d.tipo }}</td>
            <td>{{ d.data_evento }}</td>
            <td>
              <span v-if="d.sexo">{{ d.sexo }}/{{ d.faixa }}</span>
              <span v-else>{{ d.ids_oficiais?.length || 0 }} ID(s)</span>
              <span v-if="d.acima_indice" class="badge" style="margin-left: 0.35rem">índice</span>
            </td>
            <td>{{ d.quantidade }}</td>
            <td><span class="badge">{{ d.status }}</span></td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="panel">
      <h3 style="margin-top: 0">Animais identificados</h3>
      <p v-if="!animais.length" class="muted">Nenhum animal identificado ainda. Use Identificação.</p>
      <table v-else>
        <thead>
          <tr>
            <th>ID oficial</th>
            <th>Brinco</th>
            <th>Sexo</th>
            <th>Faixa</th>
            <th>Nascimento</th>
            <th>Status</th>
            <th>Sync</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in animais" :key="a.id">
            <td>{{ a.id_oficial }}</td>
            <td>{{ a.brinco_visual || "—" }}</td>
            <td>{{ a.sexo }}</td>
            <td>{{ a.faixa }}</td>
            <td>{{ a.data_nascimento }}</td>
            <td>{{ a.status }}</td>
            <td><span class="badge">{{ a.sync_status }}</span></td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

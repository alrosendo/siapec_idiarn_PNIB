<script setup>
import { onMounted, ref } from "vue";
import { api } from "../api/client";

const exploracaoId = ref(1);
const destinoCodigo = ref("PROP-RN-002");
const destinoNome = ref("Fazenda Destino Demo");
const finalidade = ref("engorda");
const sexo = ref("F");
const faixa = ref("0-12");
const quantidade = ref(2);
const idsTexto = ref("");
const forcar = ref(false);
const msg = ref("");
const erro = ref("");
const gtas = ref([]);
const loading = ref(false);

async function carregar() {
  gtas.value = await api.gtas();
}

async function emitir() {
  loading.value = true;
  msg.value = "";
  erro.value = "";
  try {
    const ids = idsTexto.value
      .split(/[\n,;\s]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    const res = await api.emitirGta({
      exploracao_origem_id: exploracaoId.value,
      destino_codigo: destinoCodigo.value,
      destino_nome: destinoNome.value,
      finalidade: finalidade.value,
      quantidades: [{ sexo: sexo.value, faixa: faixa.value, quantidade: quantidade.value }],
      ids_oficiais: ids,
      forcar_exigir_ids: forcar.value,
    });
    msg.value = `GTA ${res.numero} emitida · ${res.total_cabecas} cabeças · IDs: ${res.ids_vinculados.length}`;
    idsTexto.value = "";
    await carregar();
  } catch (e) {
    erro.value = e.message;
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  try {
    await carregar();
  } catch (e) {
    erro.value = e.message;
  }
});
</script>

<template>
  <div class="stack">
    <div v-if="erro" class="banner err">{{ erro }}</div>
    <div v-if="msg" class="banner ok">{{ msg }}</div>

    <section class="panel">
      <h2 style="margin-top: 0; font-family: var(--display)">Emitir GTA</h2>
      <p class="muted">Passos 1–2–3 condensados: destino, quantidade (SIAPEC) e IDs (PNIB se regra).</p>

      <div class="row" style="margin: 1rem 0">
        <div class="field">
          <label>Exploração origem</label>
          <input v-model.number="exploracaoId" type="number" />
        </div>
        <div class="field">
          <label>Destino código</label>
          <input v-model="destinoCodigo" />
        </div>
        <div class="field" style="min-width: 220px">
          <label>Destino nome</label>
          <input v-model="destinoNome" />
        </div>
        <div class="field">
          <label>Finalidade</label>
          <select v-model="finalidade">
            <option value="engorda">engorda</option>
            <option value="abate">abate</option>
            <option value="protocolo_privado">protocolo_privado</option>
          </select>
        </div>
      </div>

      <div class="row">
        <div class="field">
          <label>Sexo</label>
          <select v-model="sexo"><option>F</option><option>M</option></select>
        </div>
        <div class="field">
          <label>Faixa</label>
          <select v-model="faixa">
            <option>0-12</option>
            <option>13-24</option>
            <option>25-36</option>
            <option>36+</option>
          </select>
        </div>
        <div class="field">
          <label>Quantidade</label>
          <input v-model.number="quantidade" type="number" min="1" />
        </div>
        <label style="display: flex; gap: 0.4rem; align-items: center; padding-bottom: 0.4rem">
          <input v-model="forcar" type="checkbox" />
          Exigir 100% IDs
        </label>
      </div>

      <div class="field" style="margin-top: 1rem; min-width: 100%">
        <label>IDs oficiais (opcional na etapa 2; um por linha)</label>
        <textarea
          v-model="idsTexto"
          rows="4"
          style="width: 100%; border: 1px solid var(--line); border-radius: 10px; padding: 0.6rem"
          placeholder="BR-RN-00001"
        />
      </div>

      <button class="btn" style="margin-top: 1rem" :disabled="loading" @click="emitir">
        Confirmar emissão
      </button>
    </section>

    <section class="panel">
      <h3 style="margin-top: 0">GTAs emitidas</h3>
      <table>
        <thead>
          <tr>
            <th>Número</th>
            <th>Destino</th>
            <th>Cabeças</th>
            <th>IDs</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="g in gtas" :key="g.id">
            <td>{{ g.numero }}</td>
            <td>{{ g.destino_nome }}</td>
            <td>{{ g.total_cabecas }}</td>
            <td>{{ g.ids_vinculados.length }}</td>
            <td><span class="badge">{{ g.status }}</span></td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { api } from "../api/client";

const exploracaoId = ref(1);
const partida = ref("PART-DEMO-001");
const rtNome = ref("Dr(a). Demo CRMV-RN");
const idsTexto = ref("");
const animais = ref([]);
const msg = ref("");
const erro = ref("");
const loading = ref(false);

async function carregarAnimais() {
  animais.value = await api.animais(exploracaoId.value);
  const femeas = animais.value.filter((a) => a.sexo === "F" && a.status === "ativo");
  if (!idsTexto.value && femeas.length) {
    idsTexto.value = femeas.slice(0, Math.min(5, femeas.length)).map((a) => a.id_oficial).join("\n");
  }
}

async function declarar() {
  loading.value = true;
  msg.value = "";
  erro.value = "";
  try {
    const ids = idsTexto.value
      .split(/[\n,;\s]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    const res = await api.vacinar({
      exploracao_id: exploracaoId.value,
      data_vacinacao: new Date().toISOString().slice(0, 10),
      partida: partida.value,
      rt_nome: rtNome.value,
      ids_oficiais: ids,
    });
    msg.value = `Protocolo ${res.protocolo} · ${res.total_animais} animais · sync pendentes ${res.sync_pendentes}`;
  } catch (e) {
    erro.value = e.message;
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  try {
    await carregarAnimais();
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
      <h2 style="margin-top: 0; font-family: var(--display)">Vacinação brucelose</h2>
      <div class="banner">
        Etapa 3 PNIB — toda fêmea vacinada deve estar identificada. Sem ID? use Identificação antes.
      </div>

      <div class="row">
        <div class="field">
          <label>Exploração</label>
          <input v-model.number="exploracaoId" type="number" @change="carregarAnimais" />
        </div>
        <div class="field">
          <label>Partida</label>
          <input v-model="partida" />
        </div>
        <div class="field" style="min-width: 240px">
          <label>RT</label>
          <input v-model="rtNome" />
        </div>
      </div>

      <p class="muted" style="margin-top: 1rem">
        Fêmeas ativas na exploração: {{ animais.filter((a) => a.sexo === "F").length }}
      </p>

      <div class="field" style="min-width: 100%">
        <label>IDs a vacinar (obrigatório)</label>
        <textarea
          v-model="idsTexto"
          rows="6"
          style="width: 100%; border: 1px solid var(--line); border-radius: 10px; padding: 0.6rem"
        />
      </div>

      <div class="row" style="margin-top: 1rem">
        <button class="btn" :disabled="loading" @click="declarar">Confirmar declaração</button>
        <router-link class="btn secondary" to="/identificar">Identificar agora</router-link>
      </div>
    </section>
  </div>
</template>

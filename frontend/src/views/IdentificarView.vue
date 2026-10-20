<script setup>
import { computed, onMounted, ref } from "vue";
import { api } from "../api/client";

const propriedadeId = ref(1);
const exploracaoId = ref(1);
const estoque = ref([]);
const qtd = ref(5);
const sexo = ref("F");
const faixa = ref("0-12");
const msg = ref("");
const erro = ref("");
const loading = ref(false);

const nascPorFaixa = {
  "0-12": "2025-10-01",
  "13-24": "2024-10-01",
  "25-36": "2023-10-01",
  "36+": "2021-06-01",
};

const selecionados = computed(() => estoque.value.slice(0, qtd.value));

async function carregar() {
  erro.value = "";
  try {
    estoque.value = await api.estoque(propriedadeId.value);
  } catch (e) {
    erro.value = e.message;
  }
}

async function aplicar() {
  loading.value = true;
  msg.value = "";
  erro.value = "";
  try {
    const itens = selecionados.value.map((e) => ({
      id_oficial: e.id_oficial,
      sexo: sexo.value,
      data_nascimento: nascPorFaixa[faixa.value],
      nascimento_estimado: true,
      brinco_visual: e.brinco_visual,
    }));
    const res = await api.aplicarIds({
      exploracao_id: exploracaoId.value,
      data_aplicacao: new Date().toISOString().slice(0, 10),
      itens,
    });
    msg.value = `${res.aplicados} animais identificados · sync pendentes: ${res.sync_pendentes}`;
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
      <h2 style="margin-top: 0; font-family: var(--display)">Identificar agora</h2>
      <p class="muted">Wizard MVP: reserva sequencial do estoque → cria animais → fila sync PNIB.</p>

      <div class="row" style="margin: 1rem 0">
        <div class="field">
          <label>Propriedade ID</label>
          <input v-model.number="propriedadeId" type="number" @change="carregar" />
        </div>
        <div class="field">
          <label>Exploração ID</label>
          <input v-model.number="exploracaoId" type="number" />
        </div>
        <div class="field">
          <label>Quantidade</label>
          <input v-model.number="qtd" type="number" min="1" :max="estoque.length || 1" />
        </div>
        <div class="field">
          <label>Sexo</label>
          <select v-model="sexo">
            <option value="F">Fêmea</option>
            <option value="M">Macho</option>
          </select>
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
      </div>

      <p class="muted">Estoque disponível: {{ estoque.length }} · Será aplicado: {{ selecionados.length }}</p>

      <table>
        <thead>
          <tr>
            <th>ID oficial</th>
            <th>Brinco</th>
            <th>Lote</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in selecionados" :key="e.id_oficial">
            <td>{{ e.id_oficial }}</td>
            <td>{{ e.brinco_visual }}</td>
            <td>{{ e.lote_remessa }}</td>
          </tr>
        </tbody>
      </table>

      <div class="row" style="margin-top: 1rem">
        <button class="btn" :disabled="loading || !selecionados.length" @click="aplicar">
          Confirmar identificação
        </button>
        <button class="btn secondary" @click="carregar">Atualizar estoque</button>
      </div>
    </section>
  </div>
</template>

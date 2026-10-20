<script setup>
import { onMounted, ref } from "vue";
import { api } from "../api/client";

const fila = ref([]);
const erro = ref("");
const msg = ref("");
const loading = ref(false);

async function carregar() {
  erro.value = "";
  try {
    fila.value = await api.filaMortalidade();
  } catch (e) {
    erro.value = e.message;
  }
}

async function decidir(id, aprovar) {
  loading.value = true;
  msg.value = "";
  erro.value = "";
  try {
    const d = await api.homologar(id, aprovar);
    msg.value = aprovar
      ? `Declaração #${d.id} homologada`
      : `Declaração #${d.id} estornada (saldo revertido)`;
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
      <h2 style="margin-top: 0; font-family: var(--display)">Fila OESA — mortalidade</h2>
      <p class="muted">
        Declarações acima do índice mensal aguardando homologação ou estorno (estilo SIAPEC).
      </p>

      <p v-if="!fila.length" class="muted" style="margin-top: 1rem">Fila vazia.</p>
      <table v-else>
        <thead>
          <tr>
            <th>#</th>
            <th>Exploração</th>
            <th>Data</th>
            <th>Tipo baixa</th>
            <th>Detalhe</th>
            <th>Qtd</th>
            <th>Obs.</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in fila" :key="d.id">
            <td>{{ d.id }}</td>
            <td>{{ d.exploracao_id }}</td>
            <td>{{ d.data_evento }}</td>
            <td>{{ d.tipo_baixa || "—" }}</td>
            <td>
              <span v-if="d.sexo">{{ d.sexo }}/{{ d.faixa }}</span>
              <span v-else>{{ (d.ids_oficiais || []).join(", ") || "—" }}</span>
            </td>
            <td>{{ d.quantidade }}</td>
            <td class="muted">{{ d.observacao || "—" }}</td>
            <td>
              <div class="row">
                <button class="btn" :disabled="loading" @click="decidir(d.id, true)">Homologar</button>
                <button class="btn secondary" :disabled="loading" @click="decidir(d.id, false)">
                  Estornar
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <button class="btn secondary" style="margin-top: 1rem" @click="carregar">Atualizar</button>
    </section>
  </div>
</template>

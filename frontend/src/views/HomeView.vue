<script setup>
import { onMounted, ref } from "vue";
import { api } from "../api/client";

const health = ref(null);
const props = ref([]);
const erro = ref("");

onMounted(async () => {
  try {
    health.value = await api.health();
    props.value = await api.propriedades();
  } catch (e) {
    erro.value = e.message;
  }
});
</script>

<template>
  <div class="stack">
    <div v-if="erro" class="banner err">{{ erro }}</div>
    <section class="panel">
      <h2 style="margin-top: 0; font-family: var(--display)">Portal do produtor (demo)</h2>
      <p class="muted">
        Fluxo SIAPEC: saldo e GTA rápidos. PNIB entra nos gatilhos (identificar, brucelose, etapa 4).
      </p>
      <div v-if="health" class="grid-stats" style="margin-top: 1rem">
        <div class="stat">
          <span>API</span>
          <strong>{{ health.status }}</strong>
        </div>
        <div class="stat">
          <span>Etapa PNIB</span>
          <strong>{{ health.pnib_etapa }}</strong>
        </div>
      </div>
    </section>

    <section class="panel">
      <h3 style="margin-top: 0">Propriedades seed</h3>
      <table v-if="props.length">
        <thead>
          <tr>
            <th>Código</th>
            <th>Nome</th>
            <th>Município</th>
            <th>Explorações</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in props" :key="p.id">
            <td>{{ p.codigo }}</td>
            <td>{{ p.nome }}</td>
            <td>{{ p.municipio }}/{{ p.uf }}</td>
            <td>
              <span v-for="e in p.exploracoes" :key="e.id" class="badge" style="margin-right: 0.35rem">
                #{{ e.id }} {{ e.especie }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="muted">Carregando…</p>
      <div class="row" style="margin-top: 1rem">
        <router-link class="btn" to="/exploracao">Ver saldo</router-link>
        <router-link class="btn secondary" to="/identificar">Identificar agora</router-link>
      </div>
    </section>
  </div>
</template>

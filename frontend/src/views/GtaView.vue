<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { api } from "../api/client";

const FAIXAS = [
  { id: "0-12", label: "0 a 12 meses" },
  { id: "13-24", label: "13 a 24 meses" },
  { id: "25-36", label: "25 a 36 meses" },
  { id: "36+", label: "acima de 36 meses" },
];

const propriedades = ref([]);
const gtas = ref([]);
const saldo = ref(null);
const origemId = ref(null);
const destinoId = ref(null);
const finalidade = ref("engorda");
const embarque = ref({});
const idsTexto = ref("");
const forcar = ref(false);
const msg = ref("");
const erro = ref("");
const loading = ref(false);
const conferencia = ref(null);

function chave(sexo, faixa) {
  return `${sexo}|${faixa}`;
}

function gradeVazia() {
  const next = {};
  for (const f of FAIXAS) {
    next[chave("M", f.id)] = 0;
    next[chave("F", f.id)] = 0;
  }
  return next;
}

const exploracoes = computed(() => {
  const lista = [];
  for (const p of propriedades.value) {
    for (const e of p.exploracoes || []) {
      lista.push({
        id: e.id,
        especie: e.especie,
        label: `${p.codigo} · ${p.nome} · ${rotuloEspecie(e.especie)}/${e.finalidade}`,
      });
    }
  }
  return lista;
});

const origem = computed(() => exploracoes.value.find((e) => e.id === origemId.value) || null);

const destinos = computed(() =>
  exploracoes.value.filter((e) => e.id !== origemId.value && e.especie === origem.value?.especie)
);

const especieOrigem = computed(() => rotuloEspecie(origem.value?.especie));

const totalEmbarque = computed(() =>
  Object.values(embarque.value).reduce((acc, n) => acc + (Number(n) || 0), 0)
);

function rotuloEspecie(especie) {
  if (especie === "bovino") return "Bovinos";
  if (especie === "bubalino") return "Bubalinos";
  return especie || "Rebanho";
}

function disponivel(sexo, faixa) {
  const cel = saldo.value?.celulas?.find((c) => c.sexo === sexo && c.faixa === faixa);
  return cel ? cel.quantidade : 0;
}

function parseIds(texto) {
  return texto
    .split(/[\n,;\s]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

async function carregarSaldo() {
  if (!origemId.value) {
    saldo.value = null;
    return;
  }
  saldo.value = await api.saldo(origemId.value);
}

async function carregar() {
  propriedades.value = await api.propriedades();
  gtas.value = await api.gtas();
  if (!origemId.value && exploracoes.value.length) {
    origemId.value = exploracoes.value.find((e) => e.especie === "bovino")?.id || exploracoes.value[0].id;
  }
  embarque.value = gradeVazia();
  await carregarSaldo();
  alinharDestino();
}

function alinharDestino() {
  if (!destinos.value.find((e) => e.id === destinoId.value)) {
    destinoId.value = destinos.value[0]?.id ?? null;
  }
}

async function emitir() {
  loading.value = true;
  msg.value = "";
  erro.value = "";
  try {
    const quantidades = [];
    for (const f of FAIXAS) {
      for (const sexo of ["M", "F"]) {
        const qtd = Number(embarque.value[chave(sexo, f.id)] || 0);
        if (qtd <= 0) continue;
        if (qtd > disponivel(sexo, f.id)) {
          throw new Error(`Embarque maior que o saldo em ${sexo === "M" ? "macho" : "fêmea"} ${f.label}`);
        }
        quantidades.push({ sexo, faixa: f.id, quantidade: qtd });
      }
    }
    if (!quantidades.length) throw new Error("Informe ao menos uma cabeça na grade");
    const res = await api.emitirGta({
      exploracao_origem_id: Number(origemId.value),
      exploracao_destino_id: Number(destinoId.value),
      finalidade: finalidade.value,
      quantidades,
      ids_oficiais: parseIds(idsTexto.value),
      forcar_exigir_ids: forcar.value,
    });
    const resumo = quantidades.map((q) => `${q.sexo} ${q.faixa}: ${q.quantidade}`).join(" · ");
    msg.value = `GTA ${res.numero} emitida (${especieOrigem.value}) · ${res.total_cabecas} cabeças · ${resumo}`;
    idsTexto.value = "";
    await carregar();
  } catch (e) {
    erro.value = e.message;
  } finally {
    loading.value = false;
  }
}

function qtdEmitida(g, sexo, faixa) {
  return g.quantidades?.find((q) => q.sexo === sexo && q.faixa === faixa)?.quantidade || 0;
}

function abrirConferencia(g) {
  conferencia.value = {
    gta: g,
    linhas: FAIXAS.map((f) => ({
      faixa: f.id,
      label: f.label,
      M: { emitido: qtdEmitida(g, "M", f.id), recebido: qtdEmitida(g, "M", f.id) },
      F: { emitido: qtdEmitida(g, "F", f.id), recebido: qtdEmitida(g, "F", f.id) },
    })),
    ids: (g.ids_vinculados || []).map((id) => ({ id, recebido: true })),
    observacao: "",
  };
}

async function confirmar() {
  const c = conferencia.value;
  if (!c) return;
  loading.value = true;
  msg.value = "";
  erro.value = "";
  try {
    const quantidades = [];
    for (const linha of c.linhas) {
      for (const sexo of ["M", "F"]) {
        if (!linha[sexo].emitido) continue;
        quantidades.push({
          sexo,
          faixa: linha.faixa,
          quantidade: Number(linha[sexo].recebido || 0),
        });
      }
    }
    const res = await api.confirmarChegada(c.gta.id, {
      quantidades,
      ids_oficiais: c.ids.filter((i) => i.recebido).map((i) => i.id),
      observacao: c.observacao || null,
    });
    msg.value =
      res.status === "recebida"
        ? `${res.numero} recebida. Saldo creditado em ${res.destino_nome}.`
        : `${res.numero} com divergência. Ocorrência enviada à OESA.`;
    conferencia.value = null;
    await carregar();
  } catch (e) {
    erro.value = e.message;
  } finally {
    loading.value = false;
  }
}

watch(origemId, async () => {
  embarque.value = gradeVazia();
  alinharDestino();
  try {
    await carregarSaldo();
  } catch (e) {
    erro.value = e.message;
  }
});

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
      <p class="muted">
        A grade segue a espécie da exploração de origem. Bovinos e bubalinos não se misturam na mesma guia.
      </p>

      <div class="row" style="margin: 1rem 0">
        <div class="field" style="min-width: 280px; flex: 1">
          <label>Origem</label>
          <select v-model.number="origemId">
            <option v-for="e in exploracoes" :key="`o-${e.id}`" :value="e.id">{{ e.label }}</option>
          </select>
        </div>
        <div class="field" style="min-width: 280px; flex: 1">
          <label>Destino (mesma espécie)</label>
          <select v-model.number="destinoId">
            <option v-for="e in destinos" :key="`d-${e.id}`" :value="e.id">{{ e.label }}</option>
          </select>
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

      <div class="banner" v-if="origem">
        Embarque de {{ especieOrigem }} · saldo disponível na origem
        <strong>{{ saldo?.total ?? 0 }}</strong>
        · nesta guia <strong>{{ totalEmbarque }}</strong>
      </div>

      <table class="grade">
        <thead>
          <tr>
            <th>Faixa etária</th>
            <th>Macho disponível</th>
            <th>Macho embarcar</th>
            <th>Fêmea disponível</th>
            <th>Fêmea embarcar</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in FAIXAS" :key="f.id">
            <td>{{ f.label }}</td>
            <td>{{ disponivel("M", f.id) }}</td>
            <td>
              <input
                v-model.number="embarque[chave('M', f.id)]"
                type="number"
                min="0"
                :max="disponivel('M', f.id)"
              />
            </td>
            <td>{{ disponivel("F", f.id) }}</td>
            <td>
              <input
                v-model.number="embarque[chave('F', f.id)]"
                type="number"
                min="0"
                :max="disponivel('F', f.id)"
              />
            </td>
          </tr>
        </tbody>
      </table>

      <label class="check">
        <input v-model="forcar" type="checkbox" />
        Exigir 100% dos animais identificados
      </label>

      <div class="field" style="margin-top: 1rem; min-width: 100%">
        <label>IDs oficiais (opcional na etapa 2; um por linha)</label>
        <textarea
          v-model="idsTexto"
          rows="3"
          style="width: 100%; border: 1px solid var(--line); border-radius: 10px; padding: 0.6rem"
          placeholder="BR-RN-00001"
        />
      </div>

      <button class="btn" style="margin-top: 1rem" :disabled="loading || !destinoId" @click="emitir">
        Confirmar emissão
      </button>
    </section>

    <section v-if="conferencia" class="panel">
      <h3 style="margin-top: 0">Confirmar chegada · {{ conferencia.gta.numero }}</h3>
      <p class="muted">
        Destino: {{ conferencia.gta.destino_nome }}. A grade repete macho e fêmea. Ajuste só o que chegou.
      </p>
      <table class="grade">
        <thead>
          <tr>
            <th>Faixa etária</th>
            <th>Macho emitido</th>
            <th>Macho recebido</th>
            <th>Fêmea emitido</th>
            <th>Fêmea recebido</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="linha in conferencia.linhas" :key="linha.faixa">
            <td>{{ linha.label }}</td>
            <td>{{ linha.M.emitido }}</td>
            <td>
              <input
                v-model.number="linha.M.recebido"
                type="number"
                min="0"
                :max="linha.M.emitido"
                :disabled="!linha.M.emitido"
              />
            </td>
            <td>{{ linha.F.emitido }}</td>
            <td>
              <input
                v-model.number="linha.F.recebido"
                type="number"
                min="0"
                :max="linha.F.emitido"
                :disabled="!linha.F.emitido"
              />
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="conferencia.ids.length" style="margin-top: 0.8rem">
        <strong>IDs do embarque</strong>
        <label v-for="item in conferencia.ids" :key="item.id" class="check">
          <input v-model="item.recebido" type="checkbox" />
          {{ item.id }}
        </label>
      </div>
      <div class="field" style="margin-top: 0.8rem; min-width: 100%">
        <label>Observação</label>
        <input v-model="conferencia.observacao" />
      </div>
      <div class="row" style="margin-top: 0.8rem">
        <button class="btn" :disabled="loading" @click="confirmar">Gravar chegada</button>
        <button class="btn secondary" @click="conferencia = null">Cancelar</button>
      </div>
    </section>

    <section class="panel">
      <h3 style="margin-top: 0">GTAs</h3>
      <table>
        <thead>
          <tr>
            <th>Número</th>
            <th>Destino</th>
            <th>Categorias</th>
            <th>Cabeças</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="g in gtas" :key="g.id">
            <td>{{ g.numero }}</td>
            <td>{{ g.destino_nome }}</td>
            <td>{{ (g.quantidades || []).map((q) => `${q.sexo} ${q.faixa}: ${q.quantidade}`).join(" · ") || "—" }}</td>
            <td>{{ g.total_cabecas }}</td>
            <td><span class="badge">{{ g.status }}</span></td>
            <td>
              <button
                v-if="g.status === 'emitida' && g.exploracao_destino_id"
                class="btn secondary"
                @click="abrirConferencia(g)"
              >
                Confirmar chegada
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<style scoped>
.grade input {
  width: 5.5rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0.35rem 0.45rem;
}
.grade input:disabled {
  background: #f3f3f0;
}
.check {
  display: flex;
  gap: 0.45rem;
  align-items: center;
  margin-top: 0.85rem;
}
</style>

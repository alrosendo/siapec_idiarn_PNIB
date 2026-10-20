import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";
import SaldoView from "../views/SaldoView.vue";
import IdentificarView from "../views/IdentificarView.vue";
import GtaView from "../views/GtaView.vue";
import VacinaView from "../views/VacinaView.vue";
import OesaView from "../views/OesaView.vue";
import CadastrosView from "../views/CadastrosView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: HomeView },
    { path: "/cadastros", name: "cadastros", component: CadastrosView },
    { path: "/exploracao", name: "saldo", component: SaldoView },
    { path: "/identificar", name: "identificar", component: IdentificarView },
    { path: "/transito", name: "gta", component: GtaView },
    { path: "/vacina", name: "vacina", component: VacinaView },
    { path: "/oesa", name: "oesa", component: OesaView },
  ],
});

export default router;

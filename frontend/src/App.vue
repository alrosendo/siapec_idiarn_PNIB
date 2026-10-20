<template>
  <div class="shell">
    <header class="topbar">
      <div class="brand">
        <h1>SIAPEC IDIARN × PNIB</h1>
        <p>Defesa agropecuária fluida · identificação individual sob regra</p>
      </div>
      <nav class="nav">
        <router-link to="/">Início</router-link>
        <router-link to="/cadastros">Cadastros</router-link>
        <router-link to="/exploracao">Exploração</router-link>
        <router-link to="/transito">Trânsito</router-link>
        <router-link to="/vacina">Sanidade</router-link>
        <router-link to="/identificar">Identificação</router-link>
        <router-link to="/oesa">OESA</router-link>
      </nav>
    </header>
    <router-view />
  </div>
</template>

import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./styles/main.css";
import { setClusterIdProvider } from "./api/resources";

const app = createApp(App);
const pinia = createPinia();
app.use(pinia);
app.use(router);
app.mount("#app");

// Wire cluster store to resource API — allows all resource calls to include cluster_id
import { useClusterStore } from "./stores/cluster";
const clusterStore = useClusterStore();
setClusterIdProvider(() => clusterStore.currentId);

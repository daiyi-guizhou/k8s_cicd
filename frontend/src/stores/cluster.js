import { ref, computed } from "vue";
import { defineStore } from "pinia";
import { getClusterList } from "../api/clusters";

export const useClusterStore = defineStore("cluster", () => {
  const clusters = ref([]);
  const currentId = ref(null);  // currently selected cluster id
  const loading = ref(false);

  const current = computed(() =>
    clusters.value.find((c) => c.id === currentId.value) || null
  );
  const hasClusters = computed(() => clusters.value.length > 0);

  async function fetchClusters() {
    loading.value = true;
    try {
      const res = await getClusterList();
      clusters.value = res.data?.items || [];
      // Auto-select first cluster if none selected
      if (!currentId.value && clusters.value.length > 0) {
        currentId.value = clusters.value[0].id;
      }
      // If current selection no longer exists, reset
      if (currentId.value && !clusters.value.find((c) => c.id === currentId.value)) {
        currentId.value = clusters.value[0]?.id || null;
      }
    } catch (e) {
      clusters.value = [];
    } finally {
      loading.value = false;
    }
  }

  function selectCluster(id) {
    currentId.value = id;
  }

  return { clusters, currentId, current, hasClusters, loading, fetchClusters, selectCluster };
});

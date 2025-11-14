<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated>
      <q-toolbar>
        <q-toolbar-title>
          Scribble Sense - Title Rating
        </q-toolbar-title>

        <div v-if="authStore.user" class="q-mr-md">
          {{ authStore.user.email }}
        </div>

        <q-btn
          v-if="authStore.isAuthenticated"
          flat
          label="Logout"
          icon="logout"
          @click="onLogout"
        />
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useAuthStore } from 'src/stores/auth-store';
import { useQuasar } from 'quasar';

const router = useRouter();
const authStore = useAuthStore();
const $q = useQuasar();

const onLogout = async () => {
  try {
    await authStore.logout();
    router.push('/login');
    $q.notify({
      type: 'positive',
      message: 'Logged out successfully',
    });
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: 'Logout failed',
    });
  }
};
</script>

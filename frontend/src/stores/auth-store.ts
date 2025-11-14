import { defineStore } from 'pinia';
import { apiService } from 'src/services/api';
import { UserRead, LoginRequest } from 'src/types/api';
import { api } from 'boot/axios';

interface AuthState {
  token: string | null;
  user: UserRead | null;
  isAuthenticated: boolean;
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: localStorage.getItem('access_token'),
    user: null,
    isAuthenticated: false,
  }),

  actions: {
    async login(credentials: LoginRequest) {
      try {
        const response = await apiService.login(credentials);
        this.token = response.access_token;
        localStorage.setItem('access_token', response.access_token);

        // Set the token in axios default headers
        api.defaults.headers.common['Authorization'] = `Bearer ${response.access_token}`;

        // Get user info
        await this.fetchUser();

        this.isAuthenticated = true;
      } catch (error) {
        this.clearAuth();
        throw error;
      }
    },

    async logout() {
      try {
        await apiService.logout();
      } catch (error) {
        console.error('Logout error:', error);
      } finally {
        this.clearAuth();
      }
    },

    async fetchUser() {
      try {
        this.user = await apiService.getCurrentUser();
        this.isAuthenticated = true;
      } catch (error) {
        this.clearAuth();
        throw error;
      }
    },

    clearAuth() {
      this.token = null;
      this.user = null;
      this.isAuthenticated = false;
      localStorage.removeItem('access_token');
      delete api.defaults.headers.common['Authorization'];
    },

    async initAuth() {
      if (this.token) {
        api.defaults.headers.common['Authorization'] = `Bearer ${this.token}`;
        try {
          await this.fetchUser();
        } catch (error) {
          this.clearAuth();
        }
      }
    },
  },
});

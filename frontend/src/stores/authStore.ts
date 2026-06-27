import { defineStore } from 'pinia';
import { auth, provider } from '../firebase';
import { signInWithPopup, signOut as firebaseSignOut, type User } from 'firebase/auth';

export interface BackendUser {
  id: string;
  username: string | null;
  rank: string | null;
  agent_priority: string[] | null;
  mood: string | null;
  party_id: number | null;
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as User | null,
    token: null as string | null,
    loading: true,
    backendUser: null as BackendUser | null,
  }),
  actions: {
    async loginWithGoogle() {
      try {
        const result = await signInWithPopup(auth, provider);
        this.user = result.user;
        // Token will be force-refreshed via getToken() — don't snapshot here
      } catch (error) {
        console.error('Google Sign-In Error', error);
        throw error;
      }
    },

    /**
     * Always returns a fresh, valid Firebase ID token.
     * Passing true forces a refresh, guaranteeing the token isn't expired.
     */
    async getToken(): Promise<string | null> {
      if (!this.user) return null;
      try {
        const freshToken = await this.user.getIdToken(true);
        this.token = freshToken;
        return freshToken;
      } catch (error) {
        console.error('Failed to refresh token', error);
        return null;
      }
    },

    async logout() {
      await firebaseSignOut(auth);
      this.user = null;
      this.token = null;
      this.backendUser = null;
    },

    setUser(user: User | null) {
      this.user = user;
      if (!user) {
        this.token = null;
        this.backendUser = null;
      }
    },

    setToken(token: string | null) {
      this.token = token;
    },

    setLoading(loading: boolean) {
      this.loading = loading;
    },

    setBackendUser(user: BackendUser | null) {
      this.backendUser = user;
    },
  },
});

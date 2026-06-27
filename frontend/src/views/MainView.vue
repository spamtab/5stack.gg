<script setup lang="ts">
import { computed, onBeforeUnmount, ref, onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { useRouter } from 'vue-router'
import draggable from 'vuedraggable'

const authStore = useAuthStore()
const router = useRouter()

// Constants
const ranks = ['Iron 1', 'Iron 2', 'Iron 3', 'Bronze 1', 'Bronze 2', 'Bronze 3', 'Silver 1', 'Silver 2', 'Silver 3', 'Gold 1', 'Gold 2', 'Gold 3', 'Platinum 1', 'Platinum 2', 'Platinum 3', 'Diamond 1', 'Diamond 2', 'Diamond 3', 'Ascendant 1', 'Ascendant 2', 'Ascendant 3', 'Immortal 1', 'Immortal 2', 'Immortal 3', 'Radiant']
const initialAgents = ['Astra', 'Breach', 'Brimstone', 'Chamber', 'Clove', 'Cypher', 'Deadlock', 'Fade', 'Gekko', 'Harbor', 'Iso', 'Jett', 'KAY/O', 'Killjoy', 'Neon', 'Omen', 'Phoenix', 'Raze', 'Reyna', 'Sage', 'Skye', 'Sova', 'Viper', 'Yoru']
const moods = ['serious locked in', 'chill competitive']
const moodFilters = [
  { label: 'Any', value: 'any' },
  { label: 'Chill', value: 'chill' },
  { label: 'Locked In', value: 'locked' },
]

// User State — seeded from the store's cached profile (set by App.vue on auth)
const backendUser = authStore.backendUser
const username = ref(backendUser?.username ?? '')
const isEditingUsername = ref(false)
const editUsernameInput = ref('')
const editTaglineInput = ref('')
const selectedRank = ref(backendUser?.rank ?? ranks[0])
const selectedMood = ref(backendUser?.mood ?? moods[0])
const agentPriority = ref(backendUser?.agent_priority ? [...backendUser.agent_priority] : [...initialAgents])
const selectedMoodFilter = ref<'any' | 'chill' | 'locked'>('any')
const selectedMinRating = ref(ranks[0])
const selectedMaxRating = ref(ranks[ranks.length - 1])

// App State
const currentMode = ref<'none' | 'create' | 'search'>('none')
const partyCode = ref('')
const isLoading = ref(false)
const prefSaved = ref(false)  // shows brief "Saved!" feedback

// Data Lists
const individualPlayers = ref<any[]>([])
const partiesList = ref<any[]>([])
const incomingRequests = ref<any[]>([])
const currentParty = ref<any | null>(null)
let refreshTimer: number | undefined

const getPriorityAgents = (agents?: string[] | null) => {
  return (agents ?? []).slice(0, 5)
}

const rankToIndex = (rank?: string | null) => {
  if (!rank) return -1
  return ranks.indexOf(rank)
}

const filteredIndividualPlayers = computed(() => {
  const moodFilterValue = selectedMoodFilter.value
  const minIndex = rankToIndex(selectedMinRating.value)
  const maxIndex = rankToIndex(selectedMaxRating.value)
  const lowerBound = Math.min(minIndex, maxIndex)
  const upperBound = Math.max(minIndex, maxIndex)

  return individualPlayers.value.filter((player: any) => {
    const playerMood = String(player.mood ?? '').toLowerCase()
    const matchesMood =
      moodFilterValue === 'any' ||
      (moodFilterValue === 'chill' && playerMood === 'chill competitive') ||
      (moodFilterValue === 'locked' && playerMood === 'serious locked in')

    const playerRankIndex = rankToIndex(player.rank)
    const matchesRank =
      playerRankIndex >= 0 &&
      playerRankIndex >= lowerBound &&
      playerRankIndex <= upperBound

    return matchesMood && matchesRank
  })
})

onMounted(async () => {
  // If App.vue already loaded the profile into the store, we're done.
  // Only re-fetch if the store is empty (e.g., hard refresh on MainView directly).
  if (!authStore.backendUser) {
    await fetchUserData()
  }

  if (authStore.backendUser?.party_id) {
    await fetchMyParty()
  }

  // Auto-save whenever rank or mood dropdown changes
  watch([selectedRank, selectedMood], () => {
    if (currentMode.value === 'none') savePreferencesQuiet()
  })

  refreshTimer = window.setInterval(() => {
    refreshDashboardState()
  }, 5000)
})

onBeforeUnmount(() => {
  if (refreshTimer) {
    window.clearInterval(refreshTimer)
  }
})

const fetchUserData = async () => {
  try {
    const token = await authStore.getToken()
    if (!token) return
    const response = await fetch('http://localhost:8000/api/users/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (response.ok) {
      const data = await response.json()
      authStore.setBackendUser(data)
      username.value = data.username ?? ''
      if (data.rank) selectedRank.value = data.rank
      if (data.mood) selectedMood.value = data.mood
      if (data.agent_priority && data.agent_priority.length > 0) {
        agentPriority.value = data.agent_priority
      }
    }
  } catch (e) {
    console.error('fetchUserData error:', e)
  }
}

const refreshCurrentViews = async () => {
  if (currentMode.value === 'create') {
    await fetchIndividualPlayers()
  }
  if (currentMode.value === 'search') {
    await fetchParties()
  }
  if (currentMode.value !== 'none') {
    await fetchIncomingRequests()
  }
}

const refreshPartyAndUser = async () => {
  await fetchUserData()
  await fetchMyParty()
}

const refreshDashboardState = async () => {
  await fetchUserData()
  await fetchMyParty()
  await fetchIncomingRequests()
  if (currentMode.value === 'search') {
    await fetchParties()
  }
  if (currentMode.value === 'create') {
    await fetchIndividualPlayers()
  }
}

const savePreferences = async () => {
  try {
    const token = await authStore.getToken()
    if (!token) return
    const response = await fetch('http://localhost:8000/api/users', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        rank: selectedRank.value,
        mood: selectedMood.value,
        agent_priority: agentPriority.value,
      }),
    })
    if (response.ok) {
      const data = await response.json()
      authStore.setBackendUser(data)
    }
  } catch (e) {
    console.error('savePreferences error:', e)
  }
}

const setLookingForParty = async (lookingForParty: boolean) => {
  try {
    const token = await authStore.getToken()
    if (!token) return
    const response = await fetch('http://localhost:8000/api/users', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ looking_for_party: lookingForParty }),
    })
    if (response.ok) {
      const data = await response.json()
      authStore.setBackendUser(data)
    }
  } catch (e) {
    console.error('setLookingForParty error:', e)
  }
}

/** Saves preferences and shows the brief "Saved!" badge. */
const savePreferencesWithFeedback = async () => {
  await savePreferences()
  prefSaved.value = true
  setTimeout(() => { prefSaved.value = false }, 2000)
}

/** Silent save — used by watchers and auto-save on logout. */
const savePreferencesQuiet = async () => {
  await savePreferences()
}

const saveUsername = async () => {
  if (!editUsernameInput.value || !editTaglineInput.value) return
  const fullUsername = `${editUsernameInput.value}#${editTaglineInput.value}`

  try {
    const token = await authStore.getToken()
    if (!token) return
    const response = await fetch('http://localhost:8000/api/users', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ username: fullUsername }),
    })
    if (response.ok) {
      const data = await response.json()
      authStore.setBackendUser(data)
      username.value = fullUsername
      isEditingUsername.value = false
    }
  } catch (e) {
    console.error('saveUsername error:', e)
  }
}

const toggleCreateParty = async () => {
  if (currentMode.value === 'create') return;
  if (!partyCode.value.trim()) {
    console.error('party code is required')
    return
  }
  isLoading.value = true;
  await savePreferences();
  await setLookingForParty(false)

  try {
    const token = await authStore.getToken()
    if (token) {
      const response = await fetch('http://localhost:8000/api/parties', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ code: partyCode.value || null }),
      })
      if (!response.ok) {
        console.error('create party failed', await response.text())
      }
    }
  } catch (e) {
    console.error('create party error:', e)
  }

  currentMode.value = 'create';
  isLoading.value = false;
  await refreshPartyAndUser()
  await fetchIndividualPlayers()
}

const toggleSearchParty = async () => {
  if (currentMode.value === 'search') return;
  isLoading.value = true;
  await savePreferences();
  await setLookingForParty(true)
  currentMode.value = 'search';
  isLoading.value = false;
  await refreshDashboardState()
  fetchParties();
}

const cancelMode = () => {
  setLookingForParty(false)
  currentMode.value = 'none'
}

const fetchIndividualPlayers = async () => {
  try {
    const token = await authStore.getToken()
    if (!token) return
    const response = await fetch('http://localhost:8000/api/users', {
      headers: { Authorization: `Bearer ${token}` },
    })
    const players = await response.json()
    const currentPartyMemberIds = new Set((currentParty.value?.members || []).map((member: any) => member.id))
    const currentUserId = authStore.backendUser?.id
    individualPlayers.value = players.filter((player: any) => {
      return player.id !== currentUserId && !currentPartyMemberIds.has(player.id)
    })
  } catch (e) { console.error('fetchIndividualPlayers error:', e) }
}

const leaveCurrentParty = async () => {
  try {
    const token = await authStore.getToken()
    if (!token) return
    const response = await fetch('http://localhost:8000/api/parties/leave', {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (response.ok) {
      await setLookingForParty(false)
      await refreshDashboardState()
      currentMode.value = 'none'
    }
  } catch (e) {
    console.error('leaveCurrentParty error:', e)
  }
}

const removePartyMember = async (memberId: string) => {
  try {
    const token = await authStore.getToken()
    if (!token) return
    const response = await fetch(`http://localhost:8000/api/parties/members/${memberId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (response.ok) {
      await refreshDashboardState()
      await fetchIndividualPlayers()
    }
  } catch (e) {
    console.error('removePartyMember error:', e)
  }
}

const fetchParties = async () => {
  try {
    const token = await authStore.getToken()
    if (!token) return
    const response = await fetch('http://localhost:8000/api/parties', {
      headers: { Authorization: `Bearer ${token}` },
    })
    partiesList.value = await response.json()
  } catch (e) { console.error('fetchParties error:', e) }
}

const fetchMyParty = async () => {
  try {
    const token = await authStore.getToken()
    if (!token) {
      currentParty.value = null
      return
    }
    const response = await fetch('http://localhost:8000/api/parties/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (response.ok) {
      currentParty.value = await response.json()
    } else {
      currentParty.value = null
    }
  } catch (e) {
    currentParty.value = null
    console.error('fetchMyParty error:', e)
  }
}

const fetchIncomingRequests = async () => {
  try {
    const token = await authStore.getToken()
    if (!token) return
    const response = await fetch('http://localhost:8000/api/requests/incoming', {
      headers: { Authorization: `Bearer ${token}` },
    })
    incomingRequests.value = await response.json()
  } catch (e) { console.error('fetchIncomingRequests error:', e) }
}

const sendJoinRequest = async (party: any) => {
  try {
    const token = await authStore.getToken()
    if (!token) return
    const response = await fetch('http://localhost:8000/api/requests', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ type: 'join', party_id: party.id }),
    })
    if (response.ok) {
      await fetchIncomingRequests()
    }
  } catch (e) {
    console.error('sendJoinRequest error:', e)
  }
}

const sendInviteRequest = async (player: any) => {
  try {
    const token = await authStore.getToken()
    if (!token) return
    const response = await fetch('http://localhost:8000/api/requests', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ type: 'invite', receiver_id: player.id }),
    })
    if (response.ok) {
      await fetchIncomingRequests()
    }
  } catch (e) {
    console.error('sendInviteRequest error:', e)
  }
}

const respondToIncomingRequest = async (request: any, accept: boolean) => {
  try {
    const token = await authStore.getToken()
    if (!token) return
    const response = await fetch(`http://localhost:8000/api/requests/${request.id}/respond?accept=${accept}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (response.ok) {
      await fetchIncomingRequests()
      await refreshPartyAndUser()
      await refreshCurrentViews()
    }
  } catch (e) {
    console.error('respondToIncomingRequest error:', e)
  }
}

const handleLogout = async () => {
  // Persist current preferences before signing out
  await savePreferencesQuiet()
  try {
    const token = await authStore.getToken()
    if (token && authStore.backendUser?.party_id) {
      await fetch('http://localhost:8000/api/parties/disband', {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
    }
  } catch (e) {
    console.error('disband party on logout error:', e)
  }
  currentMode.value = 'none'
  partyCode.value = ''
  individualPlayers.value = []
  partiesList.value = []
  incomingRequests.value = []
  currentParty.value = null
  await setLookingForParty(false)
  await authStore.logout()
  router.push('/login')
}

watch(currentMode, async (mode, previousMode) => {
  if (mode !== 'none') {
    await fetchIncomingRequests()
    if (mode === 'create') {
      await fetchIndividualPlayers()
      await fetchMyParty()
    }
    if (mode === 'search') {
      await fetchParties()
    }
  }

  if (previousMode !== 'none' && mode === 'none') {
    incomingRequests.value = []
    individualPlayers.value = []
    partiesList.value = []
    currentParty.value = null
  }
})
</script>

<template>
  <div class="dashboard">
    <!-- Navbar -->
    <nav class="navbar d-flex justify-between align-center px-4 py-3 glass-panel m-4">
      <h2 class="text-danger">5stack.gg</h2>
      <div class="d-flex align-center gap-3">
        <div v-if="!isEditingUsername" class="d-flex align-center gap-2">
          <span class="username">{{ username }}</span>
          <button class="btn-icon-small" @click="() => {
            const parts = username.split('#');
            editUsernameInput = parts[0] || '';
            editTaglineInput = parts[1] || '';
            isEditingUsername = true;
          }">✏️</button>
        </div>
        <div v-else class="d-flex align-center gap-2">
          <input v-model="editUsernameInput" class="input-field" style="width: 120px; padding: 4px;" placeholder="Name">
          <span class="text-muted">#</span>
          <input v-model="editTaglineInput" class="input-field" style="width: 60px; padding: 4px;" placeholder="TAG">
          <button class="btn-primary" style="padding: 4px 12px; font-size: 0.8rem;" @click="saveUsername">Save</button>
          <button class="btn-secondary" style="padding: 4px 12px; font-size: 0.8rem;" @click="isEditingUsername = false">Cancel</button>
        </div>
        <button class="btn-secondary ml-3" @click="handleLogout">Logout</button>
      </div>
    </nav>

    <div class="container mt-4">
      <!-- Preferences Section -->
      <div class="glass-panel p-4 mb-4">
        <h3 class="mb-4">Playstyle Preferences</h3>
        
        <div class="preferences-grid" :class="{ 'disabled-overlay': currentMode !== 'none' }">
          <div class="pref-item">
            <label>Rank</label>
            <select v-model="selectedRank" class="input-field mt-2" :disabled="currentMode !== 'none'">
              <option v-for="rank in ranks" :key="rank" :value="rank">{{ rank }}</option>
            </select>
          </div>
          
          <div class="pref-item">
            <label>Mood</label>
            <select v-model="selectedMood" class="input-field mt-2" :disabled="currentMode !== 'none'">
              <option v-for="mood in moods" :key="mood" :value="mood">{{ mood }}</option>
            </select>
          </div>
          
          <div class="pref-item agent-priority-section">
            <label>Agent Priority (Drag to reorder)</label>
            <draggable v-model="agentPriority" item-key="agent" class="agent-list mt-2" :disabled="currentMode !== 'none'">
              <template #item="{element}">
                <div class="agent-badge">{{ element }}</div>
              </template>
            </draggable>
          </div>
        </div>

        <!-- Save Preferences button (only shown when not in a mode) -->
        <div v-if="currentMode === 'none'" class="d-flex align-center gap-3 mt-4">
          <button class="btn-primary" style="min-width:160px" @click="savePreferencesWithFeedback">
            {{ prefSaved ? '✓ Saved!' : 'Save Preferences' }}
          </button>
          <span v-if="prefSaved" class="text-muted" style="font-size:0.85rem">Your rank, mood &amp; agent order have been saved.</span>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="actions-section d-flex gap-4 mb-4">
        <div class="action-card glass-panel flex-1 p-4" :class="{ active: currentMode === 'create' }">
          <h4 class="mb-3">Become a Party Leader</h4>
          <input v-if="currentMode === 'none'" v-model="partyCode" type="text" class="input-field mb-3" placeholder="Enter Party Code" required />
          
          <div class="d-flex align-center justify-between">
            <button class="btn-primary w-100" @click="toggleCreateParty" :disabled="(currentMode !== 'none' && currentMode !== 'create') || !!currentParty">
              <span v-if="isLoading && currentMode === 'create'" class="spinner mr-2"></span>
              {{ currentParty ? 'Leave or Disband First' : currentMode === 'create' ? 'Looking for Players...' : 'Create a Party' }}
            </button>
            <button v-if="currentMode === 'create'" class="btn-icon ml-3 text-danger" @click="cancelMode" title="Cancel">✕</button>
          </div>
        </div>

        <div class="action-card glass-panel flex-1 p-4" :class="{ active: currentMode === 'search' }">
          <h4 class="mb-3">Find a Squad</h4>
          <p class="text-muted mb-3">Browse existing parties looking for members.</p>
          
          <div class="d-flex align-center justify-between">
            <button class="btn-primary w-100" @click="toggleSearchParty" :disabled="currentMode !== 'none' && currentMode !== 'search'">
              <span v-if="isLoading && currentMode === 'search'" class="spinner mr-2"></span>
              {{ currentMode === 'search' ? 'Searching...' : 'Search for Existing Party' }}
            </button>
            <button v-if="currentMode === 'search'" class="btn-icon ml-3 text-danger" @click="cancelMode" title="Cancel">✕</button>
          </div>
        </div>
      </div>

      <div v-if="currentParty" class="glass-panel p-4 mb-4 active-party-panel">
        <div class="d-flex justify-between align-center mb-3">
          <div>
            <h3 class="mb-1">Your Party</h3>
            <p class="text-muted">{{ currentParty.members.length }}/5 members</p>
            <p class="text-muted">Party Code: {{ currentParty.code || 'No code set' }}</p>
          </div>
          <div class="d-flex gap-2">
            <button class="btn-secondary" @click="refreshPartyAndUser">Refresh Party</button>
            <button class="btn-secondary text-danger" @click="leaveCurrentParty">{{ currentParty.leader_id === authStore.backendUser?.id ? 'Disband Party' : 'Leave Party' }}</button>
          </div>
        </div>
        <div class="party-member-grid">
          <div v-for="member in currentParty.members" :key="member.id" class="party-member-card glass-panel">
            <h5>{{ member.username || 'Unknown User' }}</h5>
            <p class="text-muted">Rank: {{ member.rank || 'Unranked' }}</p>
            <p class="text-muted">Mood: {{ member.mood || 'Not set' }}</p>
            <div class="agent-column">
              <span class="text-muted agent-title">Top 5 Agents</span>
              <span v-for="agent in getPriorityAgents(member.agent_priority)" :key="agent" class="agent-line">{{ agent }}</span>
            </div>
            <button
              v-if="currentParty.leader_id === authStore.backendUser?.id && member.id !== authStore.backendUser?.id"
              class="btn-secondary text-danger mt-2"
              @click="removePartyMember(member.id)"
            >
              Remove
            </button>
          </div>
        </div>
      </div>

      <!-- List Views -->
      <div class="views-section glass-panel p-4">
        <div v-if="currentMode === 'none'" class="text-center py-5 text-muted">
          Select one of the options above to see the playerbase or parties.
        </div>
        
        <div v-if="currentMode === 'search'" class="animate-fade-in">
          <h3 class="mb-4">Available Parties</h3>
          <div class="grid-list">
            <div v-for="party in partiesList" :key="party.id" class="card p-3 glass-panel">
              <div class="d-flex justify-between align-center mb-3">
                <div>
                  <h5>Party #{{ party.id }}</h5>
                  <p class="text-muted">Code: {{ party.code }}</p>
                  <p class="text-muted">Members: {{ party.members.length }}/5</p>
                </div>
                <button class="btn-primary" @click="sendJoinRequest(party)" :disabled="!!currentParty">Request to Join</button>
              </div>
              <div class="party-member-grid search-party-member-grid">
                <div v-for="member in party.members" :key="member.id" class="party-member-card glass-panel">
                  <h5>{{ member.username || 'Unknown User' }}</h5>
                  <p class="text-muted">Rank: {{ member.rank || 'Unranked' }}</p>
                  <p class="text-muted">Mood: {{ member.mood || 'Not set' }}</p>
                  <div class="agent-column">
                    <span class="text-muted agent-title">Top 5 Agents</span>
                    <span v-for="agent in getPriorityAgents(member.agent_priority)" :key="agent" class="agent-line">{{ agent }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="partiesList.length === 0" class="text-muted">No parties found.</div>
          </div>
        </div>

        <div v-if="currentMode === 'create'" class="animate-fade-in">
          <div class="d-flex justify-between align-center mb-4">
            <h3>Individual Players</h3>
            <button class="btn-secondary" @click="fetchIndividualPlayers">Refresh Players</button>
          </div>
          <div class="filter-panel glass-panel p-3 mb-4">
            <div class="filter-row">
              <div class="filter-item">
                <label>Mood</label>
                <select v-model="selectedMoodFilter" class="input-field mt-2">
                  <option v-for="filter in moodFilters" :key="filter.value" :value="filter.value">
                    {{ filter.label }}
                  </option>
                </select>
              </div>
              <div class="filter-item">
                <label>Min Rating</label>
                <select v-model="selectedMinRating" class="input-field mt-2">
                  <option v-for="rank in ranks" :key="`min-${rank}`" :value="rank">{{ rank }}</option>
                </select>
              </div>
              <div class="filter-item">
                <label>Max Rating</label>
                <select v-model="selectedMaxRating" class="input-field mt-2">
                  <option v-for="rank in ranks" :key="`max-${rank}`" :value="rank">{{ rank }}</option>
                </select>
              </div>
            </div>
          </div>
          <div class="grid-list">
            <div v-for="player in filteredIndividualPlayers" :key="player.id" class="card p-3 glass-panel">
              <h5>{{ player.username || 'Unknown User' }}</h5>
              <p class="text-muted">Rank: {{ player.rank || 'Unranked' }}</p>
              <p class="text-muted">Mood: {{ player.mood || 'Not set' }}</p>
              <div class="agent-column">
                <span class="text-muted agent-title">Top 5 Agents</span>
                <span v-for="agent in getPriorityAgents(player.agent_priority)" :key="agent" class="agent-line">{{ agent }}</span>
              </div>
              <button class="btn-primary mt-3 w-100" @click="sendInviteRequest(player)">Invite to Party</button>
            </div>
            <div v-if="filteredIndividualPlayers.length === 0" class="text-muted">No players found.</div>
          </div>
        </div>
      </div>
      
      <!-- Incoming Requests View -->
      <div class="glass-panel p-4 mt-4" v-if="currentMode !== 'none'">
        <div class="d-flex justify-between align-center mb-4">
          <h3>Incoming Requests</h3>
          <button class="btn-secondary" @click="fetchIncomingRequests">Refresh</button>
        </div>
        <div class="grid-list">
          <div v-for="req in incomingRequests" :key="req.id" class="card p-3 glass-panel d-flex justify-between request-card">
            <div>
              <h5>{{ req.type === 'join' ? 'Join Request' : 'Party Invite' }}</h5>
              <p class="text-muted">
                From {{ req.sender?.username || `User ID: ${req.sender_id}` }}
              </p>
              <p class="text-muted">Rank: {{ req.sender?.rank || 'Unranked' }}</p>
              <p class="text-muted">Mood: {{ req.sender?.mood || 'Not set' }}</p>
              <div class="agent-column">
                <span class="text-muted agent-title">Top 5 Agents</span>
                <span v-for="agent in getPriorityAgents(req.sender?.agent_priority)" :key="agent" class="agent-line">{{ agent }}</span>
              </div>
            </div>
            <div class="d-flex gap-2">
              <button class="btn-primary" @click="respondToIncomingRequest(req, true)">Accept</button>
              <button class="btn-secondary text-danger" @click="respondToIncomingRequest(req, false)">Reject</button>
            </div>
          </div>
          <div v-if="incomingRequests.length === 0" class="text-muted">No incoming requests.</div>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
}
.m-4 { margin: 16px; }
.p-4 { padding: 24px; }
.px-4 { padding-left: 24px; padding-right: 24px; }
.py-3 { padding-top: 16px; padding-bottom: 16px; }
.py-5 { padding-top: 48px; padding-bottom: 48px; }
.flex-1 { flex: 1; }

.username {
  font-weight: 600;
  letter-spacing: 1px;
}

.btn-icon-small {
  background: none;
  border: none;
  cursor: pointer;
  opacity: 0.7;
  font-size: 1rem;
  transition: opacity 0.2s;
}
.btn-icon-small:hover {
  opacity: 1;
}

.preferences-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 2fr;
  gap: 24px;
  position: relative;
}

.disabled-overlay {
  opacity: 0.6;
  pointer-events: none;
}

.agent-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  background: rgba(0,0,0,0.2);
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--glass-border);
}

.agent-badge {
  background: var(--dark-elevated);
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 0.85rem;
  cursor: grab;
  border: 1px solid var(--glass-border);
  transition: all var(--transition-fast);
}
.agent-badge:hover {
  border-color: var(--riot-red);
}

.action-card {
  transition: all var(--transition-normal);
}
.action-card.active {
  border-color: var(--riot-red);
  box-shadow: 0 0 20px rgba(255, 70, 85, 0.2);
}

.btn-icon {
  background: none;
  border: 1px solid var(--riot-red);
  color: var(--riot-red);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  font-size: 1.2rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}
.btn-icon:hover {
  background: var(--riot-red);
  color: white;
}

.grid-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.filter-panel {
  border-color: var(--glass-border);
}

.filter-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.filter-item label {
  display: block;
  margin-bottom: 4px;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.active-party-panel {
  border-color: var(--riot-red);
}

.party-member-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
}

.search-party-member-grid {
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  margin-top: 12px;
}

.party-member-card {
  aspect-ratio: 1 / 1;
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  gap: 8px;
}

.agent-column {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 4px;
}

.agent-title {
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.agent-line {
  display: block;
  padding-left: 8px;
  border-left: 2px solid var(--glass-border);
  font-size: 0.9rem;
}

.request-card {
  align-items: flex-start;
}
</style>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, onMounted, watch } from 'vue'
import { useAuthStore } from '../stores/authStore'
import { useRouter } from 'vue-router'
import draggable from 'vuedraggable'
import { apiUrl } from '../config/api'

const authStore = useAuthStore()
const router = useRouter()

// Constants
const ranks = ['Iron 1', 'Iron 2', 'Iron 3', 'Bronze 1', 'Bronze 2', 'Bronze 3', 'Silver 1', 'Silver 2', 'Silver 3', 'Gold 1', 'Gold 2', 'Gold 3', 'Platinum 1', 'Platinum 2', 'Platinum 3', 'Diamond 1', 'Diamond 2', 'Diamond 3', 'Ascendant 1', 'Ascendant 2', 'Ascendant 3', 'Immortal 1', 'Immortal 2', 'Immortal 3', 'Radiant']
const initialAgents = ['Astra', 'Breach', 'Brimstone', 'Chamber', 'Clove', 'Cypher', 'Deadlock', 'Fade', 'Gekko', 'Harbor', 'Iso', 'Jett', 'KAY/O', 'Killjoy', 'Miks', 'Neon', 'Omen', 'Phoenix', 'Raze', 'Reyna', 'Sage', 'Skye', 'Sova', 'Tejo', 'Veto', 'Viper', 'Vyse', 'Waylay', 'Yoru']
const moods = ['serious', 'chill']
const moodFilters = [
  { label: 'Any', value: 'any' },
  { label: 'Chill', value: 'chill' },
  { label: 'Locked In', value: 'locked' },
]

// Migrates old mood values stored in DB to the new short names
const normalizeMood = (mood: string | null | undefined): string => {
  if (!mood) return moods[0]
  const map: Record<string, string> = {
    'serious locked in': 'serious',
    'chill competitive': 'chill',
  }
  return map[mood.toLowerCase()] ?? mood
}

// User State — seeded from the store's cached profile (set by App.vue on auth)
const backendUser = authStore.backendUser
const username = ref(backendUser?.username ?? '')
const isEditingUsername = ref(false)
const editUsernameInput = ref('')
const editTaglineInput = ref('')
const selectedRank = ref(backendUser?.rank ?? ranks[0])
const selectedMood = ref(normalizeMood(backendUser?.mood) ?? moods[0])
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

// Sidebar state
const sidebarOpen = ref(false)

// Tracks which parties/players the user has already sent a request to (until refresh)
const sentJoinPartyIds = ref<Set<string>>(new Set())
const sentInvitePlayerIds = ref<Set<string>>(new Set())

const getPriorityAgents = (agents?: string[] | null) => {
  return (agents ?? []).slice(0, 5)
}

// Maps agent display names to their icon filenames.
// Agents without a PNG yet have an empty string — icons will resolve once
// the matching file is dropped into src/assets/agent images/.
const agentIconMap: Record<string, string> = {
  'Astra':      'Astra_icon.png',
  'Breach':     'Breach_icon.png',
  'Brimstone':  'Brimstone_icon.png',
  'Chamber':    'Chamber_icon.png',
  'Clove':      '',            // PNG not yet available
  'Cypher':     'Cypher_icon.png',
  'Deadlock':   'Deadlock_icon.png',
  'Fade':       'Fade_icon.png',
  'Gekko':      'Gekko_icon.png',
  'Harbor':     '',            // PNG not yet available
  'Iso':        '',            // PNG not yet available
  'Jett':       'Jett_icon.png',
  'KAY/O':      'KAYO_icon.png',
  'Killjoy':    'Killjoy_icon.png',
  'Miks':       'Miks_icon.png',
  'Neon':       'Neon_icon.png',
  'Omen':       'Omen_icon.png',
  'Phoenix':    'Phoenix_icon.png',
  'Raze':       'Raze_icon.png',
  'Reyna':      'Reyna_icon.png',
  'Sage':       'Sage_icon.png',
  'Skye':       'Skye_icon.png',
  'Sova':       'Sova_icon.png',
  'Tejo':       'Tejo_icon.png',
  'Veto':       '',            // PNG not yet available
  'Viper':      'Viper_icon.png',
  'Vyse':       'Vyse_icon.png',
  'Waylay':     '',            // PNG not yet available
  'Yoru':       'Yoru_icon.png',
}

const getAgentIcon = (agentName: string): string => {
  const filename = agentIconMap[agentName]
  if (!filename) return ''
  return new URL(`../assets/agent images/${filename}`, import.meta.url).href
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
    const playerMood = normalizeMood(player.mood)
    const matchesMood =
      moodFilterValue === 'any' ||
      (moodFilterValue === 'chill' && playerMood === 'chill') ||
      (moodFilterValue === 'locked' && playerMood === 'serious')

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

  // Always load incoming requests on mount so the sidebar badge is accurate
  await fetchIncomingRequests()

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
    const response = await fetch(apiUrl('/api/users/me'), {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (response.ok) {
      const data = await response.json()
      authStore.setBackendUser(data)
      username.value = data.username ?? ''
      if (data.rank) selectedRank.value = data.rank
      if (data.mood) selectedMood.value = normalizeMood(data.mood)
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
  await fetchIncomingRequests()  // always — keeps sidebar badge live
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
    const response = await fetch(apiUrl('/api/users'), {
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
    const response = await fetch(apiUrl('/api/users'), {
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
    const response = await fetch(apiUrl('/api/users'), {
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
      const response = await fetch(apiUrl('/api/parties'), {
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
    const response = await fetch(apiUrl('/api/users'), {
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
    const response = await fetch(apiUrl('/api/parties/leave'), {
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
    const response = await fetch(apiUrl(`/api/parties/members/${memberId}`), {
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
    const response = await fetch(apiUrl('/api/parties'), {
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
    const response = await fetch(apiUrl('/api/parties/me'), {
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
    const response = await fetch(apiUrl('/api/requests/incoming'), {
      headers: { Authorization: `Bearer ${token}` },
    })
    incomingRequests.value = await response.json()
  } catch (e) { console.error('fetchIncomingRequests error:', e) }
}

const sendJoinRequest = async (party: any) => {
  try {
    const token = await authStore.getToken()
    if (!token) return
    const response = await fetch(apiUrl('/api/requests'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ type: 'join', party_id: party.id }),
    })
    if (response.ok) {
      sentJoinPartyIds.value = new Set([...sentJoinPartyIds.value, String(party.id)])
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
    const response = await fetch(apiUrl('/api/requests'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ type: 'invite', receiver_id: player.id }),
    })
    if (response.ok) {
      sentInvitePlayerIds.value = new Set([...sentInvitePlayerIds.value, String(player.id)])
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
    const response = await fetch(apiUrl(`/api/requests/${request.id}/respond?accept=${accept}`), {
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
      await fetch(apiUrl('/api/parties/disband'), {
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
  sidebarOpen.value = false
  sentJoinPartyIds.value = new Set()
  sentInvitePlayerIds.value = new Set()
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
    sentJoinPartyIds.value = new Set()
    sentInvitePlayerIds.value = new Set()
  }
})
</script>

<template>
  <div class="dashboard">
    <!-- Requests Sidebar Toggle Button -->
    <button
      class="sidebar-toggle"
      :class="{ 'sidebar-toggle--open': sidebarOpen }"
      @click="sidebarOpen = !sidebarOpen"
      :title="sidebarOpen ? 'Close Requests' : 'Incoming Requests'"
      aria-label="Toggle incoming requests sidebar"
    >
      <!-- Envelope SVG icon -->
      <svg class="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
        <polyline points="22,6 12,13 2,6"/>
      </svg>
      <span v-if="incomingRequests.length > 0" class="sidebar-badge">{{ incomingRequests.length }}</span>
    </button>

    <!-- Sidebar Overlay -->
    <transition name="overlay-fade">
      <div v-if="sidebarOpen" class="sidebar-overlay" @click="sidebarOpen = false"></div>
    </transition>

    <!-- Requests Sidebar Panel -->
    <transition name="sidebar-slide">
      <aside v-if="sidebarOpen" class="requests-sidebar glass-panel">
        <div class="sidebar-header d-flex justify-between align-center">
          <div class="section-header section-header--inline">
            <span class="section-accent"></span>
            <h3>Incoming Requests</h3>
          </div>
          <div class="d-flex align-center gap-2">
            <button class="btn-icon-small" title="Refresh" @click="fetchIncomingRequests">↻</button>
            <button class="btn-icon-small sidebar-close" title="Close" @click="sidebarOpen = false">✕</button>
          </div>
        </div>
        <div class="sidebar-body">
          <div v-if="incomingRequests.length === 0" class="empty-state">No incoming requests.</div>
          <div v-for="req in incomingRequests" :key="req.id" class="request-card glass-panel player-card">
            <div class="request-type-badge">{{ req.type === 'join' ? 'Join Request' : 'Party Invite' }}</div>
            <h5 class="player-card__name">{{ req.sender?.username || `User ID: ${req.sender_id}` }}</h5>
            <div class="stat-row">
              <span class="stat-pill stat-pill--rank">{{ req.sender?.rank || 'Unranked' }}</span>
              <span class="stat-pill stat-pill--mood">{{ req.sender?.mood || 'Not set' }}</span>
            </div>
            <div class="agent-column">
              <span class="agent-title">Top 5 Agents</span>
              <span v-for="(agent, idx) in getPriorityAgents(req.sender?.agent_priority)" :key="agent" class="agent-line">
                <span class="agent-rank">{{ idx + 1 }}</span>
                <img v-if="getAgentIcon(agent)" :src="getAgentIcon(agent)" :alt="agent" class="agent-line-icon" />
                <span v-else class="agent-line-icon agent-line-icon--placeholder"></span>
                {{ agent }}
              </span>
            </div>
            <div class="d-flex gap-2 request-actions">
              <button class="btn-primary btn-primary--sm flex-1" @click="respondToIncomingRequest(req, true)">Accept</button>
              <button class="btn-secondary btn-secondary--sm btn-danger-outline flex-1" @click="respondToIncomingRequest(req, false)">Reject</button>
            </div>
          </div>
        </div>
      </aside>
    </transition>
    <!-- Navbar -->
    <nav class="navbar glass-panel">
      <div class="navbar-inner d-flex justify-between align-center">
        <div class="navbar-brand">
          <span class="brand-accent"></span>
          <h2 class="text-danger brand-title">5stack.gg</h2>
        </div>
        <div class="navbar-actions d-flex align-center gap-3">
          <div v-if="!isEditingUsername" class="profile-chip d-flex align-center gap-2">
            <span class="profile-avatar">{{ (username.split('#')[0] || '?').charAt(0).toUpperCase() }}</span>
            <span class="username">{{ username }}</span>
            <button class="btn-icon-small" title="Edit Riot ID" @click="() => {
              const parts = username.split('#');
              editUsernameInput = parts[0] || '';
              editTaglineInput = parts[1] || '';
              isEditingUsername = true;
            }">✎</button>
          </div>
          <div v-else class="profile-edit d-flex align-center gap-2">
            <input v-model="editUsernameInput" class="input-field input-field--compact input-field--name" placeholder="Name">
            <span class="hashtag-sep">#</span>
            <input v-model="editTaglineInput" class="input-field input-field--compact input-field--tag" placeholder="TAG">
            <button class="btn-primary btn-primary--sm" @click="saveUsername">Save</button>
            <button class="btn-secondary btn-secondary--sm" @click="isEditingUsername = false">Cancel</button>
          </div>
          <button class="btn-secondary btn-danger-outline" @click="handleLogout">Logout</button>
        </div>
      </div>
    </nav>

    <div class="container dashboard-body">
      <!-- Preferences Section -->
      <div class="glass-panel panel prefs-panel">
        <div class="section-header">
          <span class="section-accent"></span>
          <h3>Playstyle Preferences</h3>
        </div>
        
        <div class="preferences-grid" :class="{ 'disabled-overlay': currentMode !== 'none' }">
          <div class="pref-item">
            <label class="field-label">Rank</label>
            <select v-model="selectedRank" class="input-field mt-2" :disabled="currentMode !== 'none'">
              <option v-for="rank in ranks" :key="rank" :value="rank">{{ rank }}</option>
            </select>
          </div>
          
          <div class="pref-item">
            <label class="field-label">Mood</label>
            <select v-model="selectedMood" class="input-field mt-2" :disabled="currentMode !== 'none'">
              <option v-for="mood in moods" :key="mood" :value="mood">{{ mood }}</option>
            </select>
          </div>
          
          <div class="pref-item agent-priority-section">
            <label class="field-label">Agent Priority <span class="field-hint">Drag to reorder</span></label>
            <div class="agent-list-scroll-wrap mt-2">
              <draggable v-model="agentPriority" item-key="agent" class="agent-list-vertical" :disabled="currentMode !== 'none'">
                <template #item="{element, index}">
                  <div class="agent-badge-vertical">
                    <span class="agent-badge-rank">{{ index + 1 }}</span>
                    <img v-if="getAgentIcon(element)" :src="getAgentIcon(element)" :alt="element" class="agent-badge-icon" />
                    <span v-else class="agent-badge-icon agent-badge-icon--placeholder"></span>
                    <span class="agent-badge-name">{{ element }}</span>
                    <span class="drag-handle">⠿</span>
                  </div>
                </template>
              </draggable>
            </div>
          </div>
        </div>

        <div v-if="currentMode === 'none'" class="save-row d-flex align-center gap-3 mt-4">
          <button class="btn-primary save-btn" @click="savePreferencesWithFeedback">
            {{ prefSaved ? '✓ Saved!' : 'Save Preferences' }}
          </button>
          <span v-if="prefSaved" class="save-hint text-muted">Your rank, mood &amp; agent order have been saved.</span>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="actions-section d-flex gap-4">
        <div class="action-card glass-panel flex-1 panel" :class="{ active: currentMode === 'create' }">
          <div class="action-card-header">
            <span class="action-icon">◆</span>
            <h4>Become a Party Leader</h4>
          </div>
          <input v-if="currentMode === 'none'" v-model="partyCode" type="text" class="input-field mb-3" placeholder="Enter Party Code" required />
          
          <div class="d-flex align-center justify-between action-row">
            <button class="btn-primary w-100" @click="toggleCreateParty" :disabled="(currentMode !== 'none' && currentMode !== 'create') || !!currentParty">
              <span v-if="isLoading && currentMode === 'create'" class="spinner mr-2"></span>
              {{ currentParty ? 'Leave or Disband First' : currentMode === 'create' ? 'Looking for Players...' : 'Create a Party' }}
            </button>
            <button v-if="currentMode === 'create'" class="btn-icon ml-3 text-danger" @click="cancelMode" title="Cancel">✕</button>
          </div>
        </div>

        <div class="action-card glass-panel flex-1 panel" :class="{ active: currentMode === 'search' }">
          <div class="action-card-header">
            <span class="action-icon">▣</span>
            <h4>Find a Squad</h4>
          </div>
          <p class="text-muted action-desc">Browse existing parties looking for members.</p>
          
          <div class="d-flex align-center justify-between action-row">
            <button class="btn-primary w-100" @click="toggleSearchParty" :disabled="currentMode !== 'none' && currentMode !== 'search'">
              <span v-if="isLoading && currentMode === 'search'" class="spinner mr-2"></span>
              {{ currentMode === 'search' ? 'Searching...' : 'Search for Existing Party' }}
            </button>
            <button v-if="currentMode === 'search'" class="btn-icon ml-3 text-danger" @click="cancelMode" title="Cancel">✕</button>
          </div>
        </div>
      </div>

      <div v-if="currentParty" class="glass-panel panel active-party-panel">
        <div class="party-header d-flex justify-between align-center">
          <div class="party-header-info">
            <div class="section-header party-title-row">
              <span class="section-accent"></span>
              <h3>Your Party</h3>
            </div>
            <div class="party-meta d-flex align-center gap-3">
              <span class="count-badge">{{ currentParty.members.length }}/5</span>
              <span class="stat-pill">Code: {{ currentParty.code || 'No code set' }}</span>
            </div>
          </div>
          <div class="d-flex gap-2 party-actions">
            <button class="btn-secondary btn-secondary--sm" @click="refreshPartyAndUser">Refresh</button>
            <button class="btn-secondary btn-secondary--sm btn-danger-outline" @click="leaveCurrentParty">{{ currentParty.leader_id === authStore.backendUser?.id ? 'Disband' : 'Leave' }}</button>
          </div>
        </div>
        <div class="party-member-grid">
          <div v-for="member in currentParty.members" :key="member.id" class="party-member-card glass-panel player-card">
            <h5 class="player-card__name">{{ member.username || 'Unknown User' }}</h5>
            <div class="stat-row">
              <span class="stat-pill stat-pill--rank">{{ member.rank || 'Unranked' }}</span>
              <span class="stat-pill stat-pill--mood">{{ member.mood || 'Not set' }}</span>
            </div>
            <div class="agent-column">
              <span class="agent-title">Top 5 Agents</span>
              <span v-for="(agent, idx) in getPriorityAgents(member.agent_priority)" :key="agent" class="agent-line">
                <span class="agent-rank">{{ idx + 1 }}</span>
                <img v-if="getAgentIcon(agent)" :src="getAgentIcon(agent)" :alt="agent" class="agent-line-icon" />
                <span v-else class="agent-line-icon agent-line-icon--placeholder"></span>
                {{ agent }}
              </span>
            </div>
            <button
              v-if="currentParty.leader_id === authStore.backendUser?.id && member.id !== authStore.backendUser?.id"
              class="btn-secondary btn-secondary--sm btn-danger-outline w-100 player-card__actions"
              @click="removePartyMember(member.id)"
            >
              Remove
            </button>
          </div>
        </div>
      </div>

      <!-- List Views -->
      <div class="views-section glass-panel panel">
        <div v-if="currentMode === 'none'" class="empty-state">
          Select one of the options above to see the playerbase or parties.
        </div>
        
        <div v-if="currentMode === 'search'" class="animate-fade-in">
          <div class="section-header">
            <span class="section-accent"></span>
            <h3>Available Parties</h3>
          </div>
          <div class="grid-list">
            <div v-for="party in partiesList" :key="party.id" class="party-list-card glass-panel">
              <div class="party-list-header d-flex justify-between align-center">
                <div class="party-list-info">
                  <h5 class="party-list-title">Party #{{ party.id }}</h5>
                  <div class="party-list-meta d-flex align-center gap-2 mt-2">
                    <span class="stat-pill">Code: {{ party.code }}</span>
                    <span class="count-badge">{{ party.members.length }}/5</span>
                  </div>
                </div>
                <button
                  class="btn-primary btn-primary--sm"
                  :class="{ 'btn-sent': sentJoinPartyIds.has(String(party.id)) }"
                  @click="sendJoinRequest(party)"
                  :disabled="!!currentParty || sentJoinPartyIds.has(String(party.id))"
                >
                  <span v-if="sentJoinPartyIds.has(String(party.id))">✓ Requested</span>
                  <span v-else>Request to Join</span>
                </button>
              </div>
              <div class="party-member-grid search-party-member-grid">
                <div v-for="member in party.members" :key="member.id" class="party-member-card glass-panel player-card player-card--compact">
                  <h5 class="player-card__name">{{ member.username || 'Unknown User' }}</h5>
                  <div class="stat-row">
                    <span class="stat-pill stat-pill--rank">{{ member.rank || 'Unranked' }}</span>
                    <span class="stat-pill stat-pill--mood">{{ member.mood || 'Not set' }}</span>
                  </div>
                  <div class="agent-column">
                    <span class="agent-title">Top 5 Agents</span>
                    <span v-for="(agent, idx) in getPriorityAgents(member.agent_priority)" :key="agent" class="agent-line">
                      <span class="agent-rank">{{ idx + 1 }}</span>
                      <img v-if="getAgentIcon(agent)" :src="getAgentIcon(agent)" :alt="agent" class="agent-line-icon" />
                      <span v-else class="agent-line-icon agent-line-icon--placeholder"></span>
                      {{ agent }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="partiesList.length === 0" class="empty-state">No parties found.</div>
          </div>
        </div>

        <div v-if="currentMode === 'create'" class="animate-fade-in">
          <div class="d-flex justify-between align-center mb-4 list-toolbar">
            <div class="section-header section-header--inline">
              <span class="section-accent"></span>
              <h3>Individual Players</h3>
            </div>
            <button class="btn-secondary btn-secondary--sm" @click="fetchIndividualPlayers">Refresh</button>
          </div>
          <div class="filter-panel glass-panel panel-sm">
            <div class="filter-row">
              <div class="filter-item">
                <label class="field-label">Mood</label>
                <select v-model="selectedMoodFilter" class="input-field mt-2">
                  <option v-for="filter in moodFilters" :key="filter.value" :value="filter.value">
                    {{ filter.label }}
                  </option>
                </select>
              </div>
              <div class="filter-item">
                <label class="field-label">Min Rating</label>
                <select v-model="selectedMinRating" class="input-field mt-2">
                  <option v-for="rank in ranks" :key="`min-${rank}`" :value="rank">{{ rank }}</option>
                </select>
              </div>
              <div class="filter-item">
                <label class="field-label">Max Rating</label>
                <select v-model="selectedMaxRating" class="input-field mt-2">
                  <option v-for="rank in ranks" :key="`max-${rank}`" :value="rank">{{ rank }}</option>
                </select>
              </div>
            </div>
          </div>
          <div class="grid-list">
            <div v-for="player in filteredIndividualPlayers" :key="player.id" class="player-card glass-panel">
              <h5 class="player-card__name">{{ player.username || 'Unknown User' }}</h5>
              <div class="stat-row">
                <span class="stat-pill stat-pill--rank">{{ player.rank || 'Unranked' }}</span>
                <span class="stat-pill stat-pill--mood">{{ player.mood || 'Not set' }}</span>
              </div>
              <div class="agent-column">
                <span class="agent-title">Top 5 Agents</span>
                <span v-for="(agent, idx) in getPriorityAgents(player.agent_priority)" :key="agent" class="agent-line">
                  <span class="agent-rank">{{ idx + 1 }}</span>
                  <img v-if="getAgentIcon(agent)" :src="getAgentIcon(agent)" :alt="agent" class="agent-line-icon" />
                  <span v-else class="agent-line-icon agent-line-icon--placeholder"></span>
                  {{ agent }}
                </span>
              </div>
              <button
                class="btn-primary w-100 player-card__actions"
                :class="{ 'btn-sent': sentInvitePlayerIds.has(String(player.id)) }"
                @click="sendInviteRequest(player)"
                :disabled="sentInvitePlayerIds.has(String(player.id))"
              >
                <span v-if="sentInvitePlayerIds.has(String(player.id))">✓ Invited</span>
                <span v-else>Invite to Party</span>
              </button>
            </div>
            <div v-if="filteredIndividualPlayers.length === 0" class="empty-state">No players found.</div>
          </div>
        </div>
      </div>
      
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  min-height: 100vh;
  padding-bottom: 48px;
}

.flex-1 { flex: 1; }

/* Navbar */
.navbar {
  margin: 16px 16px 0;
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.navbar-inner {
  padding: 14px 24px;
}

.navbar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-accent {
  width: 3px;
  height: 28px;
  background: var(--riot-red);
  border-radius: var(--radius-sm);
}

.brand-title {
  font-size: 1.15rem;
  letter-spacing: 0.15em;
  margin: 0;
}

.profile-chip {
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  padding: 6px 14px 6px 8px;
}

.profile-avatar {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--riot-red), #c92a37);
  color: #fff;
  font-weight: 800;
  font-size: 0.85rem;
  border-radius: var(--radius-sm);
  clip-path: polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 4px 100%, 0 calc(100% - 4px));
}

.username {
  font-weight: 600;
  letter-spacing: 0.04em;
  font-size: 0.9rem;
}

.hashtag-sep {
  color: var(--riot-red);
  font-weight: 800;
  font-size: 1.1rem;
}

.btn-icon-small {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--glass-border);
  color: var(--text-secondary);
  cursor: pointer;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.btn-icon-small:hover {
  color: var(--riot-red);
  border-color: var(--riot-red);
  background: var(--riot-red-dim);
}

/* Layout panels */
.dashboard-body {
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.panel {
  padding: 28px;
}

.panel-sm {
  padding: 20px;
}

.field-hint {
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
  color: var(--text-dim);
  font-size: 0.68rem;
}

.preferences-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 2fr;
  gap: 24px;
  position: relative;
}

.disabled-overlay {
  opacity: 0.45;
  pointer-events: none;
  filter: grayscale(0.3);
}

.agent-list-scroll-wrap {
  background: rgba(0, 0, 0, 0.35);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  max-height: 340px;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--riot-red-dim) transparent;
}

.agent-list-scroll-wrap::-webkit-scrollbar {
  width: 4px;
}

.agent-list-scroll-wrap::-webkit-scrollbar-track {
  background: transparent;
}

.agent-list-scroll-wrap::-webkit-scrollbar-thumb {
  background: var(--riot-red-dim);
  border-radius: 2px;
}

.agent-list-vertical {
  display: flex;
  flex-direction: column;
  padding: 8px;
  gap: 4px;
  min-height: 60px;
}

.agent-badge-vertical {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 12px;
  border-radius: var(--radius-sm);
  background: var(--dark-elevated);
  border: 1px solid var(--glass-border);
  cursor: grab;
  transition: all var(--transition-fast);
  user-select: none;
}

.agent-badge-vertical:hover {
  border-color: var(--riot-red);
  background: var(--riot-red-dim);
}

.agent-badge-vertical:active {
  cursor: grabbing;
}

.agent-badge-rank {
  color: var(--riot-red);
  font-weight: 800;
  font-size: 0.72rem;
  min-width: 18px;
  text-align: center;
}

.agent-badge-icon {
  width: 28px;
  height: 28px;
  object-fit: contain;
  border-radius: 2px;
  flex-shrink: 0;
}

.agent-badge-icon--placeholder {
  background: rgba(255, 255, 255, 0.06);
  border: 1px dashed var(--glass-border);
  border-radius: 2px;
}

.agent-badge-name {
  flex: 1;
  font-size: 0.82rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-primary);
}

.drag-handle {
  color: var(--text-dim);
  font-size: 1rem;
  flex-shrink: 0;
  letter-spacing: -2px;
}

.save-row {
  padding-top: 8px;
  border-top: 1px solid var(--glass-border);
}

.save-btn {
  min-width: 180px;
}

.save-hint {
  font-size: 0.85rem;
}

/* Action cards */
.actions-section {
  flex-wrap: wrap;
}

.action-card {
  transition: all var(--transition-normal);
  display: flex;
  flex-direction: column;
}

.action-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.action-icon {
  color: var(--riot-red);
  font-size: 1rem;
}

.action-card h4 {
  margin: 0;
  font-size: 0.95rem;
}

.action-desc {
  font-size: 0.9rem;
  margin-bottom: 16px;
  line-height: 1.5;
}

.action-row {
  margin-top: auto;
}

.action-card.active {
  border-color: var(--riot-red);
  box-shadow: 0 0 32px var(--riot-red-dim), inset 0 0 0 1px rgba(255, 70, 85, 0.15);
  animation: pulse-glow 3s ease-in-out infinite;
}

.btn-icon {
  background: rgba(255, 70, 85, 0.1);
  border: 1px solid var(--riot-red);
  color: var(--riot-red);
  width: 42px;
  height: 42px;
  border-radius: var(--radius-md);
  font-size: 1.1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
  flex-shrink: 0;
}

.btn-icon:hover {
  background: var(--riot-red);
  color: white;
}

/* Active party */
.active-party-panel {
  border-color: rgba(255, 70, 85, 0.35);
  background: linear-gradient(135deg, rgba(255, 70, 85, 0.06) 0%, var(--glass-bg) 40%);
}

.party-header {
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.party-title-row {
  margin-bottom: 12px;
}

.party-title-row::after {
  display: none;
}

.party-meta {
  flex-wrap: wrap;
}

.party-actions {
  flex-wrap: wrap;
}

.party-member-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.search-party-member-grid {
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--glass-border);
}

.party-member-card {
  min-height: 200px;
  display: flex;
  flex-direction: column;
}

.player-card--compact {
  min-height: 180px;
}

/* Party list cards */
.party-list-card {
  padding: 24px;
  grid-column: 1 / -1;
  border-left: 3px solid var(--riot-red);
}

.party-list-header {
  flex-wrap: wrap;
  gap: 16px;
}

.party-list-title {
  font-size: 1rem;
  margin: 0;
}

.party-list-meta {
  flex-wrap: wrap;
}

/* Grids */
.grid-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.requests-grid {
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
}

.filter-panel {
  margin-bottom: 24px;
  background: rgba(0, 0, 0, 0.2);
}

.filter-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 20px;
}

.section-header--inline {
  margin-bottom: 0;
  flex: 1;
}

.section-header--inline::after {
  display: none;
}

.list-toolbar {
  flex-wrap: wrap;
  gap: 12px;
}

/* Agent list in cards */
.agent-column {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
  flex: 1;
}

.agent-title {
  font-size: 0.68rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-dim);
  margin-bottom: 4px;
}

.agent-line {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0 4px 8px;
  border-left: 2px solid var(--glass-border);
  font-size: 0.82rem;
  color: var(--text-secondary);
  transition: border-color var(--transition-fast);
}

.player-card:hover .agent-line {
  border-left-color: var(--riot-red-dim);
}

.agent-rank {
  color: var(--riot-red);
  font-weight: 800;
  font-size: 0.7rem;
  min-width: 14px;
}

.agent-line-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
  border-radius: 2px;
  flex-shrink: 0;
}

.agent-line-icon--placeholder {
  display: inline-block;
  background: rgba(255, 255, 255, 0.06);
  border: 1px dashed var(--glass-border);
  border-radius: 2px;
}

/* Request cards */
.request-card {
  display: flex;
  flex-direction: column;
}

.request-type-badge {
  display: inline-block;
  align-self: flex-start;
  padding: 4px 10px;
  background: var(--riot-red-dim);
  border: 1px solid rgba(255, 70, 85, 0.3);
  color: var(--riot-red);
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  border-radius: var(--radius-sm);
  margin-bottom: 12px;
}

.request-actions {
  margin-top: auto;
  padding-top: 16px;
}

.requests-panel {
  margin-top: 0;
}

/* ── Sent-state button ── */
.btn-sent,
.btn-sent:disabled {
  background: linear-gradient(135deg, #1a7a4a 0%, #145e38 100%) !important;
  opacity: 1 !important;
  cursor: default !important;
  box-shadow: none !important;
  transform: none !important;
}

/* ── Sidebar toggle button ── */
.sidebar-toggle {
  position: fixed;
  top: 50%;
  right: 0;
  transform: translateY(-50%);
  z-index: 300;
  width: 48px;
  height: 56px;
  background: var(--dark-elevated);
  border: 1px solid var(--glass-border);
  border-right: none;
  border-radius: var(--radius-md) 0 0 var(--radius-md);
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
  box-shadow: -4px 0 16px rgba(0,0,0,0.3);
}

.sidebar-toggle:hover,
.sidebar-toggle--open {
  color: var(--text-primary);
  border-color: var(--riot-red);
  background: var(--riot-red-dim);
  box-shadow: -4px 0 20px var(--riot-red-glow);
}

.sidebar-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.sidebar-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  background: var(--riot-red);
  color: #fff;
  font-size: 0.65rem;
  font-weight: 800;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  pointer-events: none;
}

/* ── Sidebar overlay ── */
.sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 299;
  backdrop-filter: blur(2px);
}

/* ── Sidebar panel ── */
.requests-sidebar {
  position: fixed;
  top: 0;
  right: 0;
  height: 100vh;
  width: 360px;
  max-width: 92vw;
  z-index: 300;
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-lg) 0 0 var(--radius-lg);
  border-right: none;
  overflow: hidden;
}

.sidebar-header {
  padding: 20px 20px 16px;
  border-bottom: 1px solid var(--glass-border);
  flex-shrink: 0;
}

.sidebar-close {
  color: var(--text-secondary);
}

.sidebar-close:hover {
  color: var(--riot-red);
  border-color: var(--riot-red);
  background: var(--riot-red-dim);
}

.sidebar-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  scrollbar-width: thin;
  scrollbar-color: var(--riot-red-dim) transparent;
}

.sidebar-body::-webkit-scrollbar {
  width: 4px;
}

.sidebar-body::-webkit-scrollbar-thumb {
  background: var(--riot-red-dim);
  border-radius: 2px;
}

/* ── Sidebar transitions ── */
.sidebar-slide-enter-active,
.sidebar-slide-leave-active {
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-slide-enter-from,
.sidebar-slide-leave-to {
  transform: translateX(100%);
}

.overlay-fade-enter-active,
.overlay-fade-leave-active {
  transition: opacity 0.25s ease;
}

.overlay-fade-enter-from,
.overlay-fade-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .preferences-grid {
    grid-template-columns: 1fr;
  }

  .actions-section {
    flex-direction: column;
  }

  .navbar-actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .profile-edit {
    flex-wrap: wrap;
  }
}

@media (max-width: 640px) {
  .navbar {
    margin: 8px 8px 0;
  }

  .navbar-inner {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .panel {
    padding: 20px;
  }
}
</style>

<script setup lang="ts">
import { RouterLink } from 'vue-router'

const features = [
  {
    icon: '◆',
    title: 'Playstyle Matching',
    description:
      'Set your rank, mood, and draggable agent priority so you find teammates who actually fit how you play.',
  },
  {
    icon: '▣',
    title: 'Create or Search Parties',
    description:
      'Lead a stack with a party code or browse open parties looking for players — pick the mode that fits you.',
  },
  {
    icon: '⇄',
    title: 'Requests & Invites',
    description:
      'Send join requests, receive party invites, and accept or reject with a single click.',
  },
  {
    icon: '⬡',
    title: 'Live Party Management',
    description:
      'View active members, share your party code, kick players, leave, or disband — all in real time.',
  },
]

const steps = [
  {
    number: '01',
    title: 'Sign in with Google',
    description: 'Quick Firebase auth — no passwords, no friction.',
  },
  {
    number: '02',
    title: 'Set your Riot ID & prefs',
    description: 'Choose username#tag, rank, mood, and agent priority.',
  },
  {
    number: '03',
    title: 'Stack up',
    description: 'Create a party or search for one and queue with your squad.',
  },
]

const scrollToSection = (id: string) => {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
}

const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<template>
  <div class="landing">
    <nav class="navbar glass-panel">
      <div class="container navbar-inner d-flex align-center justify-between">
        <button type="button" class="logo" @click="scrollToTop">5stack.gg</button>
        <div class="nav-links d-flex align-center gap-4">
          <button type="button" class="nav-link" @click="scrollToSection('features')">Features</button>
          <button type="button" class="nav-link" @click="scrollToSection('how-it-works')">How it works</button>
          <RouterLink to="/login" class="btn-primary nav-cta">Get Started</RouterLink>
        </div>
      </div>
    </nav>

    <section class="hero">
      <div class="hero-bg"></div>
      <div class="container hero-content text-center animate-fade-in">
        <p class="hero-eyebrow">Valorant squad finder</p>
        <h1 class="hero-title">Stack your perfect Valorant squad</h1>
        <p class="hero-subtitle text-muted">
          Match by rank, mood, and agent priority. Create a party, search for stacks,
          and climb with teammates who fit your vibe.
        </p>
        <div class="hero-actions d-flex align-center justify-center gap-3">
          <RouterLink to="/login" class="btn-primary">Get Started</RouterLink>
          <button class="btn-secondary" @click="scrollToSection('how-it-works')">See how it works</button>
        </div>
      </div>
    </section>

    <section id="features" class="section features-section">
      <div class="container">
        <h2 class="section-title text-center">Built for the grind</h2>
        <p class="section-subtitle text-muted text-center">
          Everything you need to find a five-stack without the Discord chaos.
        </p>
        <div class="features-grid">
          <div
            v-for="(feature, index) in features"
            :key="feature.title"
            class="glass-panel feature-card animate-fade-in"
            :style="{ animationDelay: `${index * 0.1}s` }"
          >
            <span class="feature-icon">{{ feature.icon }}</span>
            <h3 class="feature-title">{{ feature.title }}</h3>
            <p class="feature-desc text-muted">{{ feature.description }}</p>
          </div>
        </div>
      </div>
    </section>

    <section id="how-it-works" class="section steps-section">
      <div class="container">
        <h2 class="section-title text-center">How it works</h2>
        <p class="section-subtitle text-muted text-center">
          Three steps from sign-in to stacked.
        </p>
        <div class="steps-grid">
          <div
            v-for="(step, index) in steps"
            :key="step.number"
            class="glass-panel step-card animate-fade-in"
            :style="{ animationDelay: `${index * 0.12}s` }"
          >
            <span class="step-number">{{ step.number }}</span>
            <h3 class="step-title">{{ step.title }}</h3>
            <p class="step-desc text-muted">{{ step.description }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="section cta-section">
      <div class="container">
        <div class="glass-panel cta-band text-center animate-fade-in">
          <h2 class="cta-title">Ready to stack?</h2>
          <p class="text-muted mb-4">
            Join 5stack.gg and find teammates who match your rank and playstyle.
          </p>
          <RouterLink to="/login" class="btn-primary">Sign in with Google</RouterLink>
        </div>
      </div>
    </section>

    <footer class="footer">
      <div class="container footer-inner d-flex align-center justify-between">
        <span class="footer-brand">5stack.gg</span>
        <span class="footer-note text-muted">Valorant matchmaking MVP</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.landing {
  min-height: 100vh;
}

.navbar {
  position: sticky;
  top: 0;
  z-index: 100;
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-top: none;
}

.navbar-inner {
  padding: 16px 24px;
}

.logo {
  color: var(--riot-red);
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 2px;
  text-decoration: none;
  text-transform: uppercase;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font-family: var(--font-primary);
}

.nav-link {
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  transition: color var(--transition-fast);
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font-family: var(--font-primary);
}

.nav-link:hover {
  color: var(--text-primary);
}

.nav-cta {
  padding: 10px 20px;
  font-size: 0.85rem;
  text-decoration: none;
}

.hero {
  position: relative;
  min-height: 85vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 50% 40%, rgba(255, 70, 85, 0.18) 0%, transparent 55%),
    linear-gradient(135deg, rgba(255, 70, 85, 0.04) 25%, transparent 25%),
    linear-gradient(225deg, rgba(255, 70, 85, 0.04) 25%, transparent 25%);
  background-size: 100% 100%, 40px 40px, 40px 40px;
  pointer-events: none;
}

.hero-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(255, 255, 255, 0.015) 2px,
    rgba(255, 255, 255, 0.015) 4px
  );
}

.hero-content {
  position: relative;
  z-index: 1;
  max-width: 720px;
  padding: 80px 24px;
}

.hero-eyebrow {
  color: var(--riot-red);
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin-bottom: 16px;
}

.hero-title {
  font-size: clamp(2rem, 5vw, 3.25rem);
  line-height: 1.1;
  margin-bottom: 20px;
}

.hero-subtitle {
  font-size: 1.1rem;
  line-height: 1.6;
  margin-bottom: 32px;
}

.hero-actions {
  flex-wrap: wrap;
}

.section {
  padding: 80px 0;
  scroll-margin-top: 72px;
}

.section-title {
  font-size: 1.75rem;
  margin-bottom: 12px;
}

.section-subtitle {
  margin-bottom: 48px;
  font-size: 1.05rem;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 24px;
}

.feature-card {
  padding: 32px;
  transition: transform var(--transition-normal), box-shadow var(--transition-normal);
  opacity: 0;
}

.feature-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 12px 40px rgba(255, 70, 85, 0.15);
}

.feature-icon {
  display: block;
  color: var(--riot-red);
  font-size: 1.5rem;
  margin-bottom: 16px;
}

.feature-title {
  font-size: 1rem;
  margin-bottom: 12px;
}

.feature-desc {
  font-size: 0.95rem;
  line-height: 1.6;
}

.steps-section {
  background: linear-gradient(180deg, transparent, rgba(255, 70, 85, 0.03), transparent);
}

.steps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}

.step-card {
  padding: 32px;
  position: relative;
  opacity: 0;
}

.step-number {
  display: block;
  color: var(--riot-red);
  font-size: 2rem;
  font-weight: 700;
  opacity: 0.5;
  margin-bottom: 12px;
}

.step-title {
  font-size: 1rem;
  margin-bottom: 10px;
}

.step-desc {
  font-size: 0.95rem;
  line-height: 1.6;
}

.cta-band {
  padding: 64px 32px;
}

.cta-title {
  font-size: 1.75rem;
  margin-bottom: 12px;
}

.footer {
  border-top: 1px solid var(--glass-border);
  padding: 24px 0;
}

.footer-inner {
  flex-wrap: wrap;
  gap: 12px;
}

.footer-brand {
  color: var(--riot-red);
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.footer-note {
  font-size: 0.85rem;
}

@media (max-width: 640px) {
  .nav-links .nav-link {
    display: none;
  }

  .hero-content {
    padding: 60px 24px;
  }

  .section {
    padding: 56px 0;
  }
}
</style>

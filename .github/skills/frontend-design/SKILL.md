---
name: frontend-design
description: Generate distinctive, production-grade frontend interfaces with bold aesthetic choices, unique typography, high-impact animations, and context-aware visual details. Avoid generic AI-generated patterns.
argument-hint: "[style] [component-type]"
user-invocable: true
disable-model-invocation: false
---

# Frontend Design Skill

Create polished, production-grade frontend interfaces that stand out from generic AI-generated designs. This skill establishes a design framework before coding—identifying purpose, audience, and specific aesthetic direction.

## Core Philosophy

**Avoid the generic AI look:**
- No system fonts without intentional pairing
- No predictable purple/blue gradients everywhere
- No cookie-cutter Bootstrap/Tailwind defaults
- No bland, safe color choices
- No identical card layouts for everything

**Embrace distinctiveness:**
- Bold aesthetic choices with clear intent
- Unexpected but harmonious combinations
- Context-aware visual decisions
- Memorable user experiences
- Personality and character in every element

## Design Framework (Execute Before Coding)

### Step 1: Understand Context
```
1. PURPOSE: What is this interface trying to achieve?
2. AUDIENCE: Who will use this? (age, tech-savviness, preferences)
3. BRAND PERSONALITY: What feeling should it evoke?
4. CONSTRAINTS: Technical requirements, accessibility needs, performance targets
5. DIFFERENTIATOR: What makes this unique vs competitors?
```

### Step 2: Choose Aesthetic Direction

| Direction | Characteristics | Best For |
|-----------|----------------|----------|
| **Brutalist** | Raw, bold, exposed structure, stark contrasts, unconventional layouts | Tech products, creative agencies, art platforms |
| **Maximalist** | Rich textures, layered elements, vibrant colors, pattern mixing | Fashion, entertainment, lifestyle brands |
| **Retro-Futuristic** | Neon gradients, chrome effects, retrofuture typography, geometric shapes | Gaming, music, nightlife, tech startups |
| **Luxury** | Generous whitespace, refined typography, subtle animations, muted palettes | Finance, real estate, premium services |
| **Playful** | Rounded shapes, bouncy animations, bright primaries, illustrated elements | Consumer apps, education, family products |
| **Minimalist-Bold** | Clean with one strong accent, dramatic scale, purposeful emptiness | SaaS, portfolios, professional services |
| **Organic** | Natural curves, earth tones, plant imagery, flowing layouts | Wellness, sustainability, food/beverage |
| **Neo-Glassmorphism** | Frosted glass, depth layering, soft shadows, translucent panels | Dashboards, data viz, modern apps |

### Step 3: Define Visual DNA

Before writing any code, establish:
- **Primary typeface** (display/headlines)
- **Secondary typeface** (body/UI)
- **Color palette** (5-7 colors with semantic meanings)
- **Spacing scale** (4px, 8px, 16px, 24px, 32px, 48px, 64px, 96px)
- **Animation timing** (fast: 150ms, normal: 300ms, slow: 500ms)
- **Signature element** (one unique visual motif)

## Typography System

### Font Pairing Principles
- Contrast with complement (sans + serif, geometric + humanist)
- One voice, one support (clear hierarchy)
- Consider the emotional weight of each typeface

### Distinctive Font Combinations

**Tech/Modern:**
- Display: `Space Grotesk`, `Cabinet Grotesk`, `Clash Display`
- Body: `Inter`, `General Sans`, `Satoshi`

**Luxury/Editorial:**
- Display: `Playfair Display`, `Cormorant Garamond`, `Freight Display`
- Body: `Source Serif Pro`, `Lora`, `Newsreader`

**Playful/Creative:**
- Display: `Fraunces`, `Lobster Two`, `Righteous`
- Body: `Nunito`, `Quicksand`, `Baloo 2`

**Brutalist/Statement:**
- Display: `Bebas Neue`, `Oswald`, `Anton`
- Body: `Roboto Mono`, `IBM Plex Mono`, `JetBrains Mono`

**Retro-Futuristic:**
- Display: `Orbitron`, `Audiowide`, `Rajdhani`
- Body: `Exo 2`, `Titillium Web`, `Jura`

### Typography Implementation
```css
/* Example: Distinctive type system */
:root {
  --font-display: 'Space Grotesk', system-ui, sans-serif;
  --font-body: 'General Sans', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  
  /* Fluid typography scale */
  --text-xs: clamp(0.75rem, 0.7rem + 0.25vw, 0.875rem);
  --text-sm: clamp(0.875rem, 0.8rem + 0.375vw, 1rem);
  --text-base: clamp(1rem, 0.9rem + 0.5vw, 1.125rem);
  --text-lg: clamp(1.125rem, 1rem + 0.625vw, 1.375rem);
  --text-xl: clamp(1.25rem, 1rem + 1.25vw, 1.75rem);
  --text-2xl: clamp(1.5rem, 1rem + 2.5vw, 2.5rem);
  --text-3xl: clamp(2rem, 1rem + 5vw, 4rem);
  --text-hero: clamp(2.5rem, 1rem + 8vw, 6rem);
}

/* Distinctive headline treatment */
.headline {
  font-family: var(--font-display);
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.1;
}

/* Interesting body text */
.body-text {
  font-family: var(--font-body);
  font-weight: 400;
  letter-spacing: 0.01em;
  line-height: 1.65;
}
```

## Color Systems

### Building Distinctive Palettes

**Avoid:**
- `#6366f1` (generic indigo)
- `#8b5cf6` (overused purple)
- `#3b82f6` (default blue)
- `#10b981` (generic green)

**Instead, create intention:**

```css
/* Example: Warm Tech Palette */
:root {
  --color-surface: #faf9f7;           /* Warm white, not pure */
  --color-text: #1a1814;              /* Deep warm black */
  --color-primary: #e85d04;           /* Bold burnt orange */
  --color-primary-dark: #c44d00;      /* Deeper for hover */
  --color-secondary: #264653;         /* Sophisticated teal */
  --color-accent: #f4a261;            /* Warm complement */
  --color-muted: #94918c;             /* Warm gray */
  --color-border: rgba(26, 24, 20, 0.08);
}

/* Example: Cool Editorial Palette */
:root {
  --color-surface: #f8fafc;           /* Cool off-white */
  --color-text: #0f172a;              /* Deep slate */
  --color-primary: #0891b2;           /* Distinctive cyan */
  --color-primary-dark: #0e7490;
  --color-secondary: #334155;         /* Slate secondary */
  --color-accent: #f97316;            /* Contrast pop */
  --color-muted: #64748b;             /* Cool gray */
  --color-border: rgba(15, 23, 42, 0.06);
}

/* Example: Dark Mode Luxury */
:root {
  --color-surface: #0a0a0b;           /* Rich black */
  --color-surface-elevated: #18181b;  /* Layered surfaces */
  --color-text: #fafafa;              /* Near white */
  --color-text-muted: #a1a1aa;        /* Zinc for secondary */
  --color-primary: #d4af37;           /* Gold accent */
  --color-primary-glow: rgba(212, 175, 55, 0.3);
  --color-border: rgba(250, 250, 250, 0.06);
}
```

### Gradient Techniques

```css
/* Avoid: Generic gradient */
.bad-gradient {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* Better: Intentional, subtle gradient */
.surface-gradient {
  background: linear-gradient(
    180deg,
    var(--color-surface) 0%,
    color-mix(in oklch, var(--color-surface), var(--color-primary) 3%) 100%
  );
}

/* Better: Bold statement gradient */
.hero-gradient {
  background: 
    radial-gradient(
      ellipse 80% 50% at 50% -20%,
      rgba(232, 93, 4, 0.15),
      transparent
    ),
    linear-gradient(
      to bottom,
      var(--color-surface),
      var(--color-surface)
    );
}

/* Mesh gradient for visual interest */
.mesh-gradient {
  background: 
    radial-gradient(at 40% 20%, hsla(28, 100%, 74%, 0.3) 0px, transparent 50%),
    radial-gradient(at 80% 0%, hsla(189, 100%, 56%, 0.2) 0px, transparent 50%),
    radial-gradient(at 0% 50%, hsla(355, 100%, 83%, 0.2) 0px, transparent 50%),
    radial-gradient(at 80% 50%, hsla(340, 100%, 76%, 0.15) 0px, transparent 50%),
    radial-gradient(at 0% 100%, hsla(22, 100%, 77%, 0.25) 0px, transparent 50%),
    var(--color-surface);
}
```

## Animation & Motion

### Timing Principles
- **Micro-interactions**: 100-200ms (instant feedback)
- **Element transitions**: 200-400ms (noticeable but quick)
- **Page transitions**: 400-700ms (dramatic but not slow)
- **Ambient animations**: 2000ms+ (subtle, continuous)

### Distinctive Motion Patterns

```css
/* Custom easing curves */
:root {
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out-back: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-in-out-circ: cubic-bezier(0.85, 0, 0.15, 1);
  --spring: cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

/* Button with character */
.btn-distinctive {
  position: relative;
  overflow: hidden;
  transition: 
    transform 200ms var(--ease-out-back),
    box-shadow 200ms var(--ease-out-expo);
}

.btn-distinctive:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 40px -10px var(--color-primary);
}

.btn-distinctive:active {
  transform: translateY(0) scale(0.98);
  transition-duration: 100ms;
}

/* Staggered entrance animation */
@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.stagger-item {
  animation: slideUp 600ms var(--ease-out-expo) backwards;
}

.stagger-item:nth-child(1) { animation-delay: 0ms; }
.stagger-item:nth-child(2) { animation-delay: 75ms; }
.stagger-item:nth-child(3) { animation-delay: 150ms; }
.stagger-item:nth-child(4) { animation-delay: 225ms; }

/* Scroll-triggered reveal */
.reveal-on-scroll {
  opacity: 0;
  transform: translateY(30px);
  transition: 
    opacity 700ms var(--ease-out-expo),
    transform 700ms var(--ease-out-expo);
}

.reveal-on-scroll.visible {
  opacity: 1;
  transform: translateY(0);
}

/* Ambient floating animation */
@keyframes float {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  33% { transform: translateY(-8px) rotate(1deg); }
  66% { transform: translateY(-4px) rotate(-1deg); }
}

.float {
  animation: float 6s ease-in-out infinite;
}
```

### Scroll-Triggered Interactions

```javascript
// Simple scroll reveal with IntersectionObserver
const revealElements = document.querySelectorAll('.reveal-on-scroll');

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, {
  threshold: 0.1,
  rootMargin: '0px 0px -50px 0px'
});

revealElements.forEach(el => revealObserver.observe(el));

// Parallax scroll effect
const parallaxElements = document.querySelectorAll('[data-parallax]');

window.addEventListener('scroll', () => {
  const scrollY = window.scrollY;
  
  parallaxElements.forEach(el => {
    const speed = parseFloat(el.dataset.parallax) || 0.5;
    const yOffset = scrollY * speed;
    el.style.transform = `translateY(${yOffset}px)`;
  });
}, { passive: true });
```

## Spatial Composition

### Breaking the Grid Intentionally

```css
/* Asymmetric layout */
.hero-asymmetric {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: var(--space-8);
  align-items: center;
}

/* Offset elements for visual interest */
.card-offset {
  position: relative;
}

.card-offset:nth-child(even) {
  transform: translateY(40px);
}

/* Overlapping elements */
.overlap-container {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
}

.overlap-image {
  grid-column: 1 / 8;
  grid-row: 1;
  z-index: 1;
}

.overlap-content {
  grid-column: 5 / 13;
  grid-row: 1;
  z-index: 2;
  padding: var(--space-12);
  background: var(--color-surface);
  margin-top: var(--space-16);
  margin-bottom: var(--space-8);
}

/* Dramatic whitespace */
.section-breathe {
  padding: clamp(80px, 15vh, 200px) 0;
}

/* Breaking alignment */
.text-break-left {
  margin-left: -5vw;
  padding-left: 5vw;
}
```

### Visual Depth & Layering

```css
/* Layered card with depth */
.card-layered {
  position: relative;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  box-shadow: 
    0 1px 2px rgba(0, 0, 0, 0.02),
    0 4px 8px rgba(0, 0, 0, 0.02),
    0 16px 32px rgba(0, 0, 0, 0.04);
}

/* Decorative background element */
.card-layered::before {
  content: '';
  position: absolute;
  inset: -1px;
  border-radius: inherit;
  background: linear-gradient(
    135deg,
    var(--color-primary) 0%,
    var(--color-accent) 100%
  );
  opacity: 0;
  z-index: -1;
  transition: opacity 300ms ease;
}

.card-layered:hover::before {
  opacity: 0.1;
}

/* Glassmorphism with proper backdrop */
.glass-panel {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 20px;
}

/* Inner shadow for depth */
.inset-panel {
  background: var(--color-surface);
  box-shadow: 
    inset 0 2px 4px rgba(0, 0, 0, 0.05),
    inset 0 -1px 0 rgba(255, 255, 255, 0.5);
  border-radius: 12px;
}
```

## Component Patterns

### Distinctive Buttons

```css
/* Primary with glow */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  font-family: var(--font-body);
  font-weight: 600;
  font-size: var(--text-sm);
  color: white;
  background: var(--color-primary);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 200ms var(--ease-out-expo);
  box-shadow: 
    0 1px 2px rgba(0, 0, 0, 0.1),
    0 0 0 0 var(--color-primary);
}

.btn-primary:hover {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
  box-shadow: 
    0 4px 12px rgba(0, 0, 0, 0.15),
    0 0 0 4px color-mix(in oklch, var(--color-primary), transparent 85%);
}

/* Ghost button with border animation */
.btn-ghost {
  position: relative;
  padding: 12px 24px;
  font-weight: 500;
  color: var(--color-text);
  background: transparent;
  border: 1.5px solid var(--color-border);
  border-radius: 10px;
  overflow: hidden;
  transition: all 200ms ease;
}

.btn-ghost::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--color-primary);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 300ms var(--ease-out-expo);
  z-index: -1;
}

.btn-ghost:hover {
  color: white;
  border-color: var(--color-primary);
}

.btn-ghost:hover::before {
  transform: scaleX(1);
}
```

### Distinctive Form Inputs

```css
.input-distinctive {
  width: 100%;
  padding: 14px 16px;
  font-family: var(--font-body);
  font-size: var(--text-base);
  color: var(--color-text);
  background: var(--color-surface);
  border: 1.5px solid var(--color-border);
  border-radius: 10px;
  outline: none;
  transition: all 200ms ease;
}

.input-distinctive::placeholder {
  color: var(--color-muted);
}

.input-distinctive:focus {
  border-color: var(--color-primary);
  box-shadow: 
    0 0 0 4px color-mix(in oklch, var(--color-primary), transparent 90%),
    0 1px 2px rgba(0, 0, 0, 0.05);
}

/* Floating label pattern */
.input-group {
  position: relative;
}

.input-group label {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  font-size: var(--text-base);
  color: var(--color-muted);
  pointer-events: none;
  transition: all 200ms ease;
  background: var(--color-surface);
  padding: 0 4px;
}

.input-group input:focus + label,
.input-group input:not(:placeholder-shown) + label {
  top: 0;
  font-size: var(--text-xs);
  color: var(--color-primary);
}
```

### Distinctive Cards

```css
.card-distinctive {
  position: relative;
  padding: 32px;
  background: var(--color-surface);
  border-radius: 20px;
  border: 1px solid var(--color-border);
  overflow: hidden;
  transition: all 300ms var(--ease-out-expo);
}

/* Accent corner */
.card-distinctive::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 0;
  background: var(--color-primary);
  border-radius: 0 0 4px 0;
  transition: height 300ms var(--ease-out-back);
}

.card-distinctive:hover {
  border-color: color-mix(in oklch, var(--color-primary), transparent 70%);
  box-shadow: 0 20px 40px -20px rgba(0, 0, 0, 0.1);
}

.card-distinctive:hover::before {
  height: 60px;
}

/* Image card with overlay */
.card-image {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  aspect-ratio: 4/3;
}

.card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 500ms var(--ease-out-expo);
}

.card-image:hover img {
  transform: scale(1.05);
}

.card-image-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to top,
    rgba(0, 0, 0, 0.8) 0%,
    transparent 60%
  );
  display: flex;
  align-items: flex-end;
  padding: 24px;
}
```

## Texture & Visual Details

### Subtle Noise Texture

```css
/* Noise overlay for depth */
.noise-texture {
  position: relative;
}

.noise-texture::after {
  content: '';
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%' height='100%' filter='url(%23noise)'/%3E%3C/svg%3E");
  opacity: 0.03;
  pointer-events: none;
  mix-blend-mode: overlay;
}
```

### Decorative Elements

```css
/* Floating orbs */
.decorative-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.4;
  pointer-events: none;
}

.orb-primary {
  width: 300px;
  height: 300px;
  background: var(--color-primary);
  top: -100px;
  right: -100px;
}

.orb-accent {
  width: 200px;
  height: 200px;
  background: var(--color-accent);
  bottom: -50px;
  left: 10%;
}

/* Grid lines background */
.grid-bg {
  background-image: 
    linear-gradient(rgba(0, 0, 0, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 0, 0, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
}

/* Dot pattern */
.dot-pattern {
  background-image: radial-gradient(
    circle,
    var(--color-border) 1px,
    transparent 1px
  );
  background-size: 24px 24px;
}
```

## Responsive Design

### Mobile-First Breakpoints

```css
/* Custom properties for breakpoints */
:root {
  --bp-sm: 640px;
  --bp-md: 768px;
  --bp-lg: 1024px;
  --bp-xl: 1280px;
  --bp-2xl: 1536px;
}

/* Container with fluid padding */
.container {
  width: 100%;
  max-width: var(--bp-xl);
  margin: 0 auto;
  padding: 0 clamp(16px, 5vw, 64px);
}

/* Responsive grid */
.grid-responsive {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(300px, 100%), 1fr));
  gap: clamp(16px, 4vw, 32px);
}
```

## Accessibility Considerations

```css
/* Focus visible for keyboard users */
:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* Reduced motion preference */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* High contrast mode */
@media (prefers-contrast: high) {
  :root {
    --color-border: var(--color-text);
  }
  
  .btn-primary {
    border: 2px solid currentColor;
  }
}

/* Color scheme preference */
@media (prefers-color-scheme: dark) {
  :root {
    /* Auto dark mode variables */
  }
}
```

## Implementation Workflow

1. **Establish design framework** (purpose, audience, aesthetic)
2. **Define visual DNA** (fonts, colors, spacing, motion)
3. **Create CSS custom properties** (variables first)
4. **Build component library** (buttons, inputs, cards)
5. **Compose layouts** (with intentional asymmetry)
6. **Add motion and interactions** (purposeful animations)
7. **Apply textures and details** (polish layer)
8. **Test responsiveness** (all breakpoints)
9. **Verify accessibility** (keyboard, screen readers, contrast)
10. **Performance audit** (animations at 60fps)

## Anti-Patterns to Avoid

### Don't:
- Use default browser focus styles without enhancement
- Apply the same border-radius to everything
- Use pure black (#000) or pure white (#fff)
- Rely solely on color for information
- Create animations longer than 500ms for interactive elements
- Use more than 3 font families
- Forget hover states on interactive elements
- Ignore the spacing scale
- Make all cards identical heights
- Use generic stock photography

### Do:
- Create visual hierarchy through size, weight, and color
- Use consistent but varied spacing
- Establish clear interactive states
- Make animations purposeful and enhancing
- Test with real content, not lorem ipsum
- Consider empty states and loading states
- Build for the edge cases
- Ensure 4.5:1 contrast ratio minimum for text

## Example Prompts for Using This Skill

- "Create a dashboard for a music streaming app" → Apply Retro-Futuristic aesthetic
- "Build a landing page for an AI security startup" → Apply Minimalist-Bold aesthetic
- "Design a settings panel with dark mode support" → Apply Neo-Glassmorphism aesthetic
- "Create an e-commerce checkout flow" → Apply Luxury aesthetic
- "Build a fitness app onboarding" → Apply Playful aesthetic
- "Design a design agency portfolio" → Apply Brutalist aesthetic

## Success Criteria

A successful design implementation includes:
- [ ] Clear aesthetic direction established
- [ ] Custom typography system implemented
- [ ] Distinctive color palette applied
- [ ] Purposeful animation and motion
- [ ] Intentional spatial composition
- [ ] Visual depth through layering
- [ ] Responsive across breakpoints
- [ ] Accessible to all users
- [ ] Performs well (60fps animations)
- [ ] Stands out from generic AI designs

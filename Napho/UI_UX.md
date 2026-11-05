# UI/UX Design Specification
## Reimbursement Management System
> Role: Senior UI/UX Designer
> Stack: Next.js 14 + Shadcn/ui + Tailwind CSS + Framer Motion
> Philosophy: Calm, focused, data-dense but never cluttered. Enterprise-grade with consumer-level delight.

---

## Design Language

### Core Aesthetic
**"Precise Calm"** — Think Linear meets Notion. Dark mode first, with purposeful color only for status communication. Every animation has intent: it either communicates state change or reduces cognitive load during transitions.

### Principles
1. **Hierarchy through weight, not decoration** — Use font weight and size before color or borders
2. **Animation is information** — Only animate when it communicates state change or guides attention
3. **Micro-feedback everywhere** — Every interactive element has a hover, active, and focus state
4. **Progressive disclosure** — Show only what the user needs for the current task; reveal complexity on demand
5. **Status as a first-class citizen** — Claim status is always visible and unmistakable

---

## Design Tokens

### Colors (Tailwind / CSS Variables)

```css
/* Base */
--background:        oklch(0.098 0 0)        /* near-black */
--foreground:        oklch(0.985 0 0)        /* near-white */
--card:              oklch(0.13 0 0)         /* elevated surface */
--card-border:       oklch(0.22 0 0)         /* subtle border */
--muted:             oklch(0.17 0 0)
--muted-foreground:  oklch(0.55 0 0)

/* Brand */
--primary:           oklch(0.71 0.19 251)    /* electric blue */
--primary-hover:     oklch(0.65 0.22 251)

/* Status Colors */
--status-draft:      oklch(0.55 0 0)         /* gray */
--status-submitted:  oklch(0.71 0.19 251)    /* blue */
--status-review:     oklch(0.76 0.17 72)     /* amber */
--status-approved:   oklch(0.72 0.18 145)    /* emerald */
--status-partial:    oklch(0.72 0.15 185)    /* teal */
--status-rejected:   oklch(0.65 0.22 22)     /* red */
--status-paid:       oklch(0.66 0.22 290)    /* violet */

/* Semantic */
--success:           oklch(0.72 0.18 145)
--warning:           oklch(0.76 0.17 72)
--destructive:       oklch(0.65 0.22 22)
--info:              oklch(0.71 0.19 251)
```

### Typography

```css
/* Font Stack */
--font-sans: "Inter Variable", system-ui, sans-serif;
--font-mono: "JetBrains Mono", "Fira Code", monospace;

/* Scale */
--text-xs:   0.75rem   / 1rem      /* 12/16 - labels, badges */
--text-sm:   0.875rem  / 1.25rem   /* 14/20 - body, table cells */
--text-base: 1rem      / 1.5rem    /* 16/24 - default */
--text-lg:   1.125rem  / 1.75rem   /* 18/28 - card titles */
--text-xl:   1.25rem   / 1.75rem   /* 20/28 - page sections */
--text-2xl:  1.5rem    / 2rem      /* 24/32 - page headers */
--text-3xl:  1.875rem  / 2.25rem   /* 30/36 - hero amounts */
```

### Spacing & Radius

```css
--radius-sm:  0.375rem   /* 6px  - badges, chips */
--radius-md:  0.5rem     /* 8px  - buttons, inputs */
--radius-lg:  0.75rem    /* 12px - cards */
--radius-xl:  1rem       /* 16px - modals, panels */
--radius-2xl: 1.5rem     /* 24px - hero cards */
```

### Motion

```css
/* Duration */
--duration-fast:   150ms   /* micro interactions: hover, focus */
--duration-base:   250ms   /* most transitions: appear, expand */
--duration-slow:   400ms   /* complex: page transitions, modals */
--duration-crawl:  600ms   /* status transitions, progress */

/* Easing */
--ease-out:     cubic-bezier(0.16, 1, 0.3, 1)     /* spring out */
--ease-in-out:  cubic-bezier(0.45, 0, 0.55, 1)    /* smooth */
--ease-spring:  cubic-bezier(0.34, 1.56, 0.64, 1) /* overshoot */
```

---

## Component Library (Shadcn Extensions)

### StatusBadge
```tsx
// Variants: draft | submitted | under_review | approved | partially_approved | rejected | paid
<StatusBadge status="approved" />

// Renders as:
// ● Approved  (dot + text in emerald, pill shape, subtle bg)
// Animate: scale-in on mount (spring, 200ms)
```

### ClaimCard
```tsx
// Used in: Employee Dashboard, Approver Queue
// Layout:
// ┌─────────────────────────────────────────────┐
// │ [CategoryIcon]  Title              [Status] │
// │                 NAPHO-0042 · Oct 23          │
// │                                  ₹ 8,500    │
// └─────────────────────────────────────────────┘
// Hover: translateY(-2px), box-shadow increase (150ms ease-out)
// Active: translateY(0px) (100ms)
// Focus-visible: ring-2 ring-primary
```

### AmountDisplay
```tsx
// Large currency display with animated number rollup
// ₹ 8,500.00
// On value change: number ticks up/down like an odometer
// Duration: 600ms, easing: ease-out
```

### ApprovalTimeline
```tsx
// Vertical stepper showing claim lifecycle
// Steps: Created → Submitted → Under Review → Approved → Paid
// Current step: pulsing dot animation (2s loop)
// Completed: filled circle with checkmark (scale-in, 300ms)
// Rejected: X with shake animation (400ms)
```

### FileUploadZone
```tsx
// Drag-and-drop zone
// States: idle | drag-over | uploading | success | error
// Drag over: border pulses, background lightens, scale(1.01) (150ms)
// Upload progress: animated progress bar with shimmer
// Success: icon morphs to checkmark (300ms spring)
```

---

## Page Designs

---

### 1. Login / User Selection Page

**Purpose:** Select demo user to enter the app.

**Layout:** Centered card, max-w-md, full viewport height

```
┌─────────────────────────────────────┐
│                                     │
│      ⬡ Napho RMS                   │
│      Reimbursement Management       │
│                                     │
│  ┌─────────────────────────────┐    │
│  │  Select who you are          │    │
│  │                              │    │
│  │  ○ Aryan Mehta    Employee  │    │
│  │  ○ Sneha Kapoor   Employee  │    │
│  │  ○ Priya Sharma   Approver  │    │
│  │  ○ Rahul Verma    Finance   │    │
│  │  ○ Admin User     Admin     │    │
│  │                              │    │
│  │  [  Continue →  ]            │    │
│  └─────────────────────────────┘    │
│                                     │
└─────────────────────────────────────┘
```

**Animations:**
- Page load: card fades in + slides up 20px (400ms, ease-out)
- User row hover: left border accent appears (150ms), bg subtle highlight
- Selected row: scale(1.01), bold name, checkmark appears (spring 200ms)
- Continue button: disabled until selection, enabled state pulses once

---

### 2. App Shell / Layout

**Layout:** Sidebar + main content

```
┌──────────┬──────────────────────────────────────┐
│          │  Header                               │
│          │  [Breadcrumb]           [🔔 3] [Avatar]│
│ Sidebar  ├──────────────────────────────────────┤
│          │                                       │
│ ⬡ Logo  │  Page Content                         │
│          │                                       │
│ Nav:     │                                       │
│ Dashboard│                                       │
│ My Claims│                                       │
│ New Claim│                                       │
│ ─────── │                                       │
│ (Approver│                                       │
│  visible)│                                       │
│ Review Q.│                                       │
│ ─────── │                                       │
│ (Finance)│                                       │
│ Payments │                                       │
│          │                                       │
│ ─────── │                                       │
│ Settings │                                       │
│ Logout   │                                       │
└──────────┴──────────────────────────────────────┘
```

**Sidebar Specs:**
- Width: 240px expanded, 64px collapsed (icon-only mode)
- Collapse toggle: chevron button at bottom
- Active nav item: left accent bar (3px), bg highlight, bold text
- Hover: bg subtle, icon color primary
- Transition: sidebar width animates 250ms ease-in-out
- Mobile: sidebar becomes a drawer (slides from left, backdrop)

**Header Specs:**
- Height: 56px
- Notification bell: badge animates (bounces once on new notification, scale spring)
- User avatar: dropdown on click (profile, switch user, logout)

**Page transitions:** Content area fades + slides 8px up on route change (300ms)

---

### 3. Employee Dashboard

**Purpose:** At-a-glance overview + claim list

```
┌─────────────────────────────────────────────────────────┐
│  Good morning, Aryan  ·  November 2026                  │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Pending      │  │  Approved     │  │  Paid         │  │
│  │  ₹ 24,500    │  │  ₹ 12,000    │  │  ₹ 68,400    │  │
│  │  3 claims     │  │  1 claim      │  │  8 claims     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  [All] [Draft 2] [Submitted 1] [Approved 1] [Rejected 1] │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │ ✈ Mumbai Trip · Oct 2024       Submitted  ₹8,500 │  │
│  │   NAPHO-0042 · 3 days ago                    →   │  │
│  ├───────────────────────────────────────────────────┤  │
│  │ 🍽 Team Lunch · Nov 1          Approved   ₹2,400 │  │
│  │   NAPHO-0041 · 1 week ago                    →   │  │
│  ├───────────────────────────────────────────────────┤  │
│  │ 📦 Laptop Stand                Draft      ₹3,200 │  │
│  │   NAPHO-0040 · Not submitted              Edit →  │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│                              [+ New Claim]              │
└─────────────────────────────────────────────────────────┘
```

**Summary Card Animations:**
- On page load: cards stagger in (50ms delay each), count animates from 0 to final (600ms ease-out)
- On hover: subtle glow matching status color, slight translateY(-2px)

**Claim List Animations:**
- List items stagger in on load (30ms delay per item)
- Status filter change: list items fade out (150ms), new items fade in (200ms)
- Card hover: translateY(-2px), shadow deepens (150ms)

**"+ New Claim" Button:**
- Floating action button style on mobile
- Sticky to bottom-right corner on scroll
- Pulse animation on first load (draws attention)

---

### 4. New Claim / Edit Claim Form

**Layout:** Full-width form with sticky action bar at bottom

```
┌─────────────────────────────────────────────────────────┐
│  ← Back     New Expense Claim                          │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  CLAIM DETAILS                                   │   │
│  │  ┌─────────────────────────────────────────┐    │   │
│  │  │ Title *                                  │    │   │
│  │  │ [Mumbai Business Trip - Oct 2024      ]  │    │   │
│  │  └─────────────────────────────────────────┘    │   │
│  │                                                  │   │
│  │  Category *               Expense Date *         │   │
│  │  [✈ Travel           ▾]  [Oct 23, 2024    📅]   │   │
│  │                                                  │   │
│  │  Description (optional)                          │   │
│  │  [                                           ]   │   │
│  │  [                                           ]   │   │
│  └─────────────────────────────────────────────┘   │   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  LINE ITEMS                                      │   │
│  │                                                  │   │
│  │  #  Description        Amount    Date   Vendor  ×│   │
│  │  1  Flight BOM-DEL   ₹ 5,200   Oct 22  IndiGo  ×│   │
│  │  2  Hotel 2 nights   ₹ 3,300   Oct 22  Oyo     ×│   │
│  │                                                  │   │
│  │  [+ Add Item]                    Total: ₹8,500  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  ATTACHMENTS                                     │   │
│  │  ┌─────────────────────────────────────────┐    │   │
│  │  │   ↑ Drop receipts here or click to      │    │   │
│  │  │     browse  (PDF, JPG, PNG · max 10MB)  │    │   │
│  │  └─────────────────────────────────────────┘    │   │
│  │  [🧾 flight_receipt.pdf]  [🧾 hotel.jpg]        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─ Sticky Bottom Bar ──────────────────────────────┐  │
│  │  Draft saved 2s ago ·   [Save Draft]  [Submit →] │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Form Animations:**
- Field focus: label floats up + shrinks (floating label pattern, 150ms)
- Field validation error: border flashes red, error message slides down (200ms)
- "Add Item" row: new row slides in from top (spring, 300ms), auto-focuses description
- Remove item: row slides up and fades out (200ms)
- Running total: number animates on each amount change (150ms ease-out)
- Upload zone drag-over: zone scales up 2%, border dashes animate (CSS dash-offset)
- Upload progress: animated stripe progress bar
- Uploaded file chip: slides in from left (spring, 250ms)
- Sticky bar: save confirmation pulse on "Draft saved"

**Validation UX:**
- Real-time validation on blur (not on keystroke)
- Error shake animation on submit attempt with errors (4 keyframes, 400ms)
- Scroll to first error automatically
- Error summary at top after failed submit attempt

---

### 5. Claim Detail Page

```
┌─────────────────────────────────────────────────────────┐
│  ← My Claims    NAPHO-0042                   Submitted  │
│                                                         │
│  Mumbai Business Trip - Oct 2024                        │
│  Aryan Mehta · Travel · Oct 23, 2024                   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │                          ₹ 8,500.00              │   │
│  │                          Claimed Amount          │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ── LINE ITEMS ─────────────────────────────────────   │
│  Description          Category    Amount    Date        │
│  Flight BOM-DEL       Travel      ₹5,200   Oct 22      │
│  Hotel 2 nights       Travel      ₹3,300   Oct 22      │
│                               ─────────────────        │
│                               Total  ₹8,500            │
│                                                         │
│  ── ATTACHMENTS ────────────────────────────────────   │
│  [📄 flight_receipt.pdf]  [🖼 hotel.jpg]               │
│                                                         │
│  ── APPROVAL TIMELINE ──────────────────────────────   │
│  ●─────────────●─────────────◌                         │
│  Submitted     Under Review  Approved/Rejected          │
│  Oct 23        -             -                          │
│                                                         │
│  ── ACTIVITY ────────────────────────────────────────  │
│  [Avatar] Aryan submitted this claim                    │
│            Oct 23, 2024 · 10:32 AM                     │
│                                                         │
│  [Avatar] Aryan created draft                           │
│            Oct 23, 2024 · 10:15 AM                     │
│                                                         │
│  [Comment box for approvers]                            │
└─────────────────────────────────────────────────────────┘
```

**Animations:**
- Hero amount: count-up animation on page load (600ms)
- Timeline: each step draws in left-to-right (400ms stagger)
- Current step: pulsing ring animation (2s infinite)
- Activity items: stagger fade-in from bottom (30ms delay each)
- Attachments: hover shows download overlay with blur backdrop (150ms)

**Rejected State:**
```
┌─ Rejection Banner ─────────────────────────────────────┐
│  ✗  This claim was rejected on Oct 25, 2024             │
│     Priya Sharma: "Flight amount exceeds ₹5,000 policy. │
│      Please resubmit with actual ticket price."         │
│                               [Edit & Resubmit →]       │
└────────────────────────────────────────────────────────┘
```

---

### 6. Approver Review Queue

```
┌─────────────────────────────────────────────────────────┐
│  Review Queue                          3 Pending         │
│                                                         │
│  [Pending Review 3]  [Approved 12]  [Rejected 4]        │
│                                                         │
│  Sort: Oldest First ▾      Category: All ▾              │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Aryan Mehta                           5 days ago │   │
│  │ Mumbai Business Trip · ✈ Travel                  │   │
│  │ ₹ 8,500                [View] [Reject] [Approve] │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ Sneha Kapoor                          2 days ago │   │
│  │ Team Lunch · 🍽 Food                             │   │
│  │ ₹ 2,400                [View] [Reject] [Approve] │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ Rohan Gupta                           1 day ago  │   │
│  │ Laptop Stand · 📦 Office                         │   │
│  │ ₹ 3,200                [View] [Reject] [Approve] │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**"Days waiting" UX:**
- 1–2 days: gray text
- 3–5 days: amber text with ⚠ icon
- 5+ days: red text with pulsing dot

**Row Actions:**
- Approve/Reject buttons: appear fully on row hover (fade in, 150ms)
- Quick Approve: opens inline modal anchored to the row (not full page)

---

### 7. Approve Modal

```
┌─────────────────────────────────────────────────────┐
│  Approve Claim                                  ✕  │
│  NAPHO-0042 · Mumbai Business Trip                  │
│                                                     │
│  Claimed Amount          ₹ 8,500                    │
│                                                     │
│  Approved Amount *                                  │
│  ┌─────────────────────────────────────┐            │
│  │ ₹  8,500                            │            │
│  └─────────────────────────────────────┘            │
│  ↳ Partial approval: enter a lower amount           │
│                                                     │
│  Comment (optional)                                 │
│  ┌─────────────────────────────────────┐            │
│  │                                     │            │
│  └─────────────────────────────────────┘            │
│                                                     │
│             [Cancel]  [✓ Confirm Approval]          │
└─────────────────────────────────────────────────────┘
```

**Partial approval indicator:**
- When approved amount < claimed amount: banner appears below field:
  ```
  ⚡ Partial approval: ₹6,500 of ₹8,500 (₹2,000 not approved)
  ```
  Slides in with ease-out, amber color

### Reject Modal

```
┌─────────────────────────────────────────────────────┐
│  Reject Claim                                   ✕  │
│  NAPHO-0042 · Mumbai Business Trip                  │
│                                                     │
│  This action cannot be undone. The employee will    │
│  be notified and can correct and resubmit.          │
│                                                     │
│  Reason for rejection *                             │
│  ┌─────────────────────────────────────┐            │
│  │                                     │            │
│  │                                     │            │
│  └─────────────────────────────────────┘            │
│  Min 10 characters · Be specific so they can fix it │
│                                                     │
│             [Cancel]  [✕ Confirm Rejection]         │
└─────────────────────────────────────────────────────┘
```

**Modal Animations:**
- Enter: scale(0.95) → scale(1) + fade in (250ms spring)
- Exit: scale(1) → scale(0.95) + fade out (150ms ease-in)
- Backdrop: blur(0) → blur(4px) + opacity 0 → 0.6 (250ms)
- Confirm button: loading spinner replaces text during API call
- On success: modal closes, row in list animates out (slide + fade, 300ms)

---

### 8. Notification Panel

```
┌──────────────────────────────────────┐
│  Notifications                  Mark all read │
├──────────────────────────────────────┤
│  ● Priya approved your claim          │
│    Mumbai Trip · ₹8,500 approved     │
│    2 hours ago                        │
├──────────────────────────────────────┤
│  ● New claim pending your review      │
│    Sneha Kapoor · Team Lunch · ₹2,400│
│    3 hours ago                        │
├──────────────────────────────────────┤
│    Claim NAPHO-0040 has been paid     │
│    ₹3,200 · Yesterday                 │
└──────────────────────────────────────┘
```

**Panel Animations:**
- Open: panel slides down from bell icon (spring, 300ms)
- New notification arrival: bell icon bounces (spring, 400ms), badge scales up briefly
- Notification row: hover bg highlight (150ms)
- Mark as read: blue dot fades out (200ms)
- "Mark all read": dots fade out in staggered sequence (30ms each)

---

## Responsive Behavior

### Breakpoints
```
mobile:   0 – 768px   (card-based, stacked layout)
tablet:   768 – 1024px (sidebar hidden by default, toggle)
desktop:  1024px+     (full sidebar + content)
```

### Mobile Adaptations
- Sidebar → bottom sheet drawer
- Claim list → full-width cards, swipe actions (approve/reject) for approvers
- Form → single column, full-width inputs
- Modals → full-screen bottom sheet on mobile
- Tables → horizontal scroll with frozen first column
- FAB for "New Claim" always visible at bottom-right

---

## Accessibility

- All interactive elements: `focus-visible` ring (2px, primary color, 2px offset)
- Color is never the only indicator of status — always paired with icon + text
- Status badges have `aria-label` with full text
- Form errors linked via `aria-describedby`
- Modal: focus trap, `role="dialog"`, `aria-modal="true"`, closes on Escape
- Timeline: `role="list"` with `aria-current` on active step
- Keyboard nav for all flows (Tab, Enter, Space, Escape, Arrow keys)
- Minimum contrast ratio: 4.5:1 for normal text, 3:1 for large text
- Reduce motion: all animations respect `prefers-reduced-motion`

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## Animation Inventory

| Component | Animation | Duration | Easing | Trigger |
|---|---|---|---|---|
| Page load | Fade + slide up | 400ms | ease-out | route change |
| Sidebar | Width expand/collapse | 250ms | ease-in-out | toggle click |
| Card hover | translateY(-2px) | 150ms | ease-out | hover |
| Modal open | scale + fade in | 250ms | spring | click |
| Modal close | scale + fade out | 150ms | ease-in | dismiss |
| Status badge | scale-in | 200ms | spring | mount |
| Number counter | tick up/down | 600ms | ease-out | value change |
| Timeline step | draw in | 400ms | ease-out | mount, stagger |
| Current step | pulse ring | 2s loop | ease-in-out | active state |
| Row slide out | slide + fade | 300ms | ease-in | list remove |
| List stagger | fade + slide up | 30ms delay | ease-out | list load |
| Bell bounce | spring bounce | 400ms | spring | new notification |
| Upload drag | scale + border dash | continuous | linear | dragover |
| Upload progress | stripe shimmer | continuous | linear | uploading |
| Upload success | icon morph | 300ms | spring | complete |
| Form error shake | shake keyframes | 400ms | ease-in-out | submit fail |
| Partial approve | slide-in banner | 200ms | ease-out | amount < claim |
| "Days waiting" | pulse dot | 2s loop | ease-in-out | > 5 days |

---

## Shadcn Components Used

| Shadcn Component | Usage |
|---|---|
| `Button` | All CTAs, actions |
| `Card` | Claim cards, summary cards, form sections |
| `Dialog` | Approve/reject modals, confirmation dialogs |
| `Form` + `Input` | New claim form, all inputs |
| `Select` | Category picker, sort/filter dropdowns |
| `Badge` | Status badges |
| `Tabs` | Status filter tabs on dashboards |
| `Table` | Line items, review queue |
| `Avatar` | User display in header, activity feed |
| `Separator` | Section dividers |
| `Tooltip` | Icon-only buttons, truncated text |
| `Toast` | Success/error notifications |
| `Sheet` | Mobile sidebar drawer |
| `Skeleton` | Loading states for cards + tables |
| `Progress` | File upload progress |
| `Calendar` | Date picker |
| `Popover` | Notification panel, date picker anchor |
| `ScrollArea` | Notification panel, long lists |
| `DropdownMenu` | User avatar menu |
| `HoverCard` | Category info on hover |
| `Accordion` | Collapsible claim sections on mobile |

---

## Loading & Empty States

### Skeleton Loaders
- Dashboard summary cards: 3 animated skeleton cards
- Claim list: 5 skeleton rows with shimmer animation
- Claim detail: skeleton for each section (header, items table, timeline)

### Empty States

```
My Claims — No claims yet:
  ┌───────────────────────────────┐
  │   [Illustration: receipt]     │
  │   No expense claims yet       │
  │   Start by creating your      │
  │   first claim.                │
  │   [+ Create First Claim]      │
  └───────────────────────────────┘

Review Queue — Nothing pending:
  ┌───────────────────────────────┐
  │   [Illustration: checkmark]   │
  │   All caught up! ✓            │
  │   No claims pending review.   │
  └───────────────────────────────┘
```

Empty state illustrations: simple, single-color SVGs that match the dark theme. No stock photos.

---

## Implementation Notes for Engineers

1. **Framer Motion** for all layout animations and page transitions
   ```tsx
   import { motion, AnimatePresence } from "framer-motion"
   ```

2. **CSS variables for tokens** — define in `globals.css`, use in Tailwind via `tailwind.config.ts`

3. **`cn()` utility** — use `clsx` + `tailwind-merge` for conditional classes

4. **`useReducedMotion()`** hook from Framer Motion — wrap all animations

5. **Optimistic updates** — update UI immediately on approve/reject, rollback on error

6. **`react-hook-form` + `zod`** — form validation with type safety

7. **`@tanstack/react-query`** — data fetching, caching, invalidation

8. **Number formatting:**
   ```tsx
   new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(amount)
   // → ₹8,500.00
   ```

9. **Date formatting:** `date-fns` — `formatDistanceToNow`, `format`

10. **File upload:** `react-dropzone` for drag-and-drop zone

# Accessibility Checklist (WCAG 2.1 AA)

Organized by the four WCAG principles: **P**erceivable, **O**perable, **U**nderstandable, **R**obust.

---

## 1. Perceivable

Users must be able to perceive the information presented.

### 1.1 Text Alternatives
- [ ] All `<img>` elements have `alt` attributes
- [ ] Decorative images use `alt=""` (empty) or CSS background-image
- [ ] Complex images (charts, diagrams) have detailed descriptions
- [ ] Icons with meaning have `aria-label` or visually hidden text
- [ ] `<svg>` elements have `<title>` and/or `aria-label`

### 1.2 Time-based Media
- [ ] Videos have captions/subtitles
- [ ] Audio content has transcripts
- [ ] Auto-playing media can be paused/stopped
- [ ] Auto-playing media is muted by default

### 1.3 Adaptable Content
- [ ] Content structure uses semantic HTML (`header`, `nav`, `main`, `section`, `article`, `aside`, `footer`)
- [ ] Heading hierarchy is logical (H1 > H2 > H3, no skips)
- [ ] Only ONE `<h1>` per page
- [ ] Lists use `<ul>`, `<ol>`, `<dl>` appropriately
- [ ] Tables have `<th>` headers with `scope` attribute
- [ ] Reading order in DOM matches visual order

### 1.4 Distinguishable
- [ ] **Normal text**: contrast ratio >= **4.5:1** against background
- [ ] **Large text** (>= 18px bold or >= 24px): contrast >= **3:1**
- [ ] **UI components** (borders, icons, focus rings): contrast >= **3:1**
- [ ] Color is NOT the sole indicator of meaning (add icon, text, or pattern)
- [ ] Text can be resized to 200% without loss of content
- [ ] No text embedded in images (unless logo)

**Quick Contrast Test:**
```
Use browser DevTools:
  1. Inspect element → Computed styles → color
  2. Check contrast ratio displayed (Chrome shows it)

Or online: webaim.org/resources/contrastchecker/
```

---

## 2. Operable

Users must be able to operate the interface.

### 2.1 Keyboard Accessible
- [ ] ALL interactive elements reachable via **Tab** key
- [ ] Tab order is logical (top-to-bottom, left-to-right)
- [ ] Buttons/links activated with **Enter** key
- [ ] Checkboxes/radios toggled with **Space** key
- [ ] Dropdown menus navigable with **Arrow** keys
- [ ] Modals trap focus (Tab cycles within modal)
- [ ] **Escape** closes modals/dropdowns/menus
- [ ] No keyboard traps (user can always Tab away)
- [ ] Custom widgets have appropriate keyboard interaction

### 2.2 Enough Time
- [ ] Session timeouts warn users before expiration
- [ ] Users can extend time limits
- [ ] Auto-advancing content (carousels) can be paused
- [ ] No content flashes more than 3 times per second

### 2.3 Navigable
- [ ] **Skip navigation** link as first focusable element
- [ ] Page has descriptive `<title>`
- [ ] Links have descriptive text (not "click here" or "read more")
- [ ] Focus indicator is visible on all interactive elements
- [ ] Focus indicator has >= **3:1** contrast
- [ ] `tabindex` used correctly:
  - `tabindex="0"` — element in natural tab order
  - `tabindex="-1"` — programmatically focusable, not in tab order
  - Never use `tabindex` > 0

### 2.4 Input Modalities
- [ ] Touch targets >= **44x44px** (CSS pixels)
- [ ] Adequate spacing between touch targets (>= 8px)
- [ ] Drag operations have alternative controls
- [ ] Gestures (swipe, pinch) have button alternatives

---

## 3. Understandable

Users must be able to understand the information and operation.

### 3.1 Readable
- [ ] Page language set: `<html lang="en">`
- [ ] Language changes marked: `<span lang="fr">Bonjour</span>`
- [ ] Text is plain and clear (avoid jargon where possible)

### 3.2 Predictable
- [ ] Navigation is consistent across pages
- [ ] Components behave consistently (same icon = same action)
- [ ] No unexpected changes on focus or input (e.g., auto-submit on select)

### 3.3 Input Assistance
- [ ] Form fields have visible `<label>` elements
- [ ] Labels linked to inputs via `for`/`id` or nesting
- [ ] Required fields marked with `*` AND `aria-required="true"`
- [ ] Input format hints shown (e.g., "DD/MM/YYYY")
- [ ] Error messages are:
  - Specific: "Email must include @" not just "Invalid"
  - Visible: displayed near the field (not just at top of form)
  - Linked: `aria-describedby` or `aria-errormessage` on the input
  - Persistent: remain until the error is fixed
- [ ] Form validation happens on submit (not just on blur for critical fields)
- [ ] Autocomplete attributes used for common fields:
  ```html
  <input type="email" autocomplete="email">
  <input type="tel" autocomplete="tel">
  <input type="text" autocomplete="name">
  <input type="text" autocomplete="street-address">
  ```

---

## 4. Robust

Content must be robust enough for diverse user agents and assistive technologies.

### 4.1 Compatible
- [ ] HTML is valid (no duplicate IDs, proper nesting)
- [ ] All `id` attributes are unique on the page
- [ ] ARIA attributes are valid and correctly applied:
  ```html
  <!-- Custom button -->
  <div role="button" tabindex="0" aria-label="Close dialog">✕</div>

  <!-- Expandable section -->
  <button aria-expanded="false" aria-controls="section1">Details</button>
  <div id="section1" hidden>Content here</div>

  <!-- Live region for dynamic content -->
  <div aria-live="polite" aria-atomic="true">
    3 items added to cart
  </div>

  <!-- Form error -->
  <input id="email" aria-invalid="true" aria-describedby="email-error">
  <span id="email-error" role="alert">Please enter a valid email</span>
  ```

### 4.2 Status Messages
- [ ] Dynamic status messages use `aria-live` regions
- [ ] `aria-live="polite"` for non-urgent updates
- [ ] `aria-live="assertive"` only for critical alerts
- [ ] Loading states communicated: `aria-busy="true"` on container

---

## Quick Testing Checklist

### Keyboard Test (2 minutes)
1. Put mouse away
2. Tab through entire page
3. Can you reach everything? Can you see where focus is?
4. Can you activate buttons/links with Enter?
5. Can you escape from modals/dropdowns?

### Zoom Test (1 minute)
1. Zoom browser to 200%
2. Is all content still visible and readable?
3. No horizontal scrolling required?

### Color Test (1 minute)
1. Squint at the page — can you still distinguish elements?
2. View in grayscale — is information still conveyed?
3. Check contrast with browser DevTools

### Screen Reader Test (5 minutes)
1. Turn on screen reader (Windows: NVDA free; Mac: VoiceOver Cmd+F5)
2. Navigate with Tab and arrow keys
3. Are images described? Are form fields labeled?
4. Are error messages announced?
5. Can you understand the page structure from headings alone?

---

## Common ARIA Patterns

### Navigation
```html
<nav aria-label="Main navigation">
  <ul>
    <li><a href="/" aria-current="page">Home</a></li>
    <li><a href="/about">About</a></li>
  </ul>
</nav>
```

### Modal Dialog
```html
<div role="dialog" aria-modal="true" aria-labelledby="modal-title">
  <h2 id="modal-title">Confirm Action</h2>
  <p>Are you sure you want to proceed?</p>
  <button>Cancel</button>
  <button>Confirm</button>
</div>
```

### Tab Panel
```html
<div role="tablist" aria-label="Settings">
  <button role="tab" aria-selected="true" aria-controls="panel-1">General</button>
  <button role="tab" aria-selected="false" aria-controls="panel-2">Security</button>
</div>
<div role="tabpanel" id="panel-1" aria-labelledby="tab-1">
  General settings content
</div>
```

### Alert
```html
<div role="alert">
  Your changes have been saved successfully.
</div>
```

### Progress
```html
<div role="progressbar" aria-valuenow="75" aria-valuemin="0" aria-valuemax="100"
     aria-label="Upload progress">
  75%
</div>
```

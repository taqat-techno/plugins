---
name: pm-estimation
description: |
  Project estimation standards — story point scale derivation, person-month calculations with allocation percentages, AI acceleration multipliers, cross-file duration validation, and variance tables. Use when analyzing backlogs, creating proposals, or reviewing effort estimates. Requires Opus for analytical reasoning.


  <example>
  Context: User has a backlog with story points but no scale
  user: "Analyze this backlog and figure out what the story point scale means"
  assistant: "I will use the pm-estimation skill to reverse-engineer the SP scale by counting distribution, grouping by SP value, reading actual stories at each level, and presenting the derived scale for validation."
  <commentary>Scale derivation trigger - reverse-engineer from data patterns.</commentary>
  </example>

  <example>
  Context: User asks to calculate team effort
  user: "Calculate person-months for the team across the project"
  assistant: "I will use the pm-estimation skill to calculate effective person-months as allocation % x duration for each member, not headcount x months."
  <commentary>Person-month calculation trigger - show the math for each member.</commentary>
  </example>

  <example>
  Context: Two versions of a plan exist
  user: "Compare the v1 and v2 project plans"
  assistant: "I will use the pm-estimation skill to create a variance table showing what changed between versions: duration, effort, team size, and percentage changes."
  <commentary>Variance trigger - before/after comparison with delta percentages.</commentary>
  </example>

  <example>
  Context: User asks about AI impact on estimates
  user: "How does AI tooling change our effort estimates?"
  assistant: "I will use the pm-estimation skill to apply role-specific AI acceleration multipliers: QA gets highest (~4x), development (~2.5x), PM gets lowest (~1.5x)."
  <commentary>AI multiplier trigger - role-specific acceleration factors.</commentary>
  </example>

  <example>
  Context: User asks what a term means
  user: "What does person-month mean?"
  assistant: "I will use the pm-estimation skill to define the term using the user's own project data as a concrete example, not a textbook definition."
  <commentary>Jargon definition trigger - explain with project-specific data.</commentary>
  </example>
license: "MIT"
metadata:
  version: "1.0.0"
  priority: 60
  model: opus
  filePattern:
    - "**/*estimation*"
    - "**/*backlog*"
    - "**/*proposal*"
    - "**/*basis*"
    - "**/*effort*"
    - "**/*planning*"
  bashPattern: []
  promptSignals:
    phrases:
      - "story points"
      - "person-months"
      - "estimate effort"
      - "project duration"
      - "sprint velocity"
      - "team allocation"
      - "AI acceleration"
      - "compare plans"
      - "variance table"
      - "effort calculation"
    minScore: 6
---

# PM Estimation Standards

## Rule 24: Cross-Check Duration Across All Files

Different documents (backlog, proposal, basis of calculation) may show **conflicting durations**. Before reporting any duration:

1. Check ALL source files for duration mentions
2. Compare them
3. If they conflict, flag it: "v1 says 9 months, v2 says 4 months — which is current?"
4. The latest versioned file (v2) is the source of truth

### Version Inconsistency Pattern

A v2 file may still contain v1 data in some sections (e.g., team member durations showing 9 months in a 4-month plan). Flag these to the user rather than silently assuming one is correct.

## Rule 25: Document Story Point Scale

If a backlog uses SP without defining what each value means, **derive the scale from actual data**:

### Derivation Process

1. **Count distribution** — How many stories at each SP value?
   ```
   SP 1: 12 stories | SP 2: 18 stories | SP 3: 15 stories
   SP 5: 8 stories  | SP 8: 5 stories  | SP 13: 2 stories
   ```

2. **Sample at each level** — Read 2-3 actual stories at each SP value

3. **Identify complexity patterns** — What distinguishes a 1 from a 5?
   ```
   SP 1: Simple field addition, label change, config tweak
   SP 2: Single model CRUD with basic view
   SP 3: Multi-model with computed fields or workflow
   SP 5: Cross-module integration or complex business logic
   SP 8: Major feature with multiple controllers, views, tests
   SP 13: Epic-level — architectural change or new subsystem
   ```

4. **Present for validation** — Show the derived scale to the team for confirmation

## Rule 26: Person-Months ≠ Calendar Months

**ALWAYS** calculate effective person-months:

```
Effective PM = Allocation % × Duration (months)
```

### Example Calculation (Show the Math)

| Member | Role | Allocation | Duration | Person-Months |
|--------|------|-----------|----------|---------------|
| Ahmad | PM | 50% | 4 months | 2.00 |
| Sara | Backend Lead | 100% | 4 months | 4.00 |
| Omar | Backend Dev | 100% | 4 months | 4.00 |
| Fatima | Frontend | 80% | 4 months | 3.20 |
| Khalid | QA | 60% | 3 months | 1.80 |
| Noor | UI/UX | 20% | 2 months | 0.40 |
| **Total** | | | | **15.40 PM** |

A team of 6 at mixed allocations delivers **15.40 person-months** in 4 calendar months — NOT 24 person-months (6 × 4).

### The Rule: Always Show

```
Allocation % × Duration = Person-Months
```

For EACH member. Stakeholders trust calculations they can verify.

## Rule 27: AI Acceleration Multipliers

When a project uses AI-assisted development, traditional estimates don't apply. Document the multiplier per role:

| Role | Traditional | With AI | Multiplier | Reasoning |
|------|------------|---------|------------|-----------|
| QA/Testing | 8 PM | 2 PM | ~4x | AI generates test cases, mock data, coverage analysis |
| Backend Dev | 10 PM | 4 PM | ~2.5x | AI accelerates model/view/controller generation |
| Frontend Dev | 6 PM | 2.5 PM | ~2.4x | AI generates components, styling, responsive layouts |
| DevOps/CI | 3 PM | 1.5 PM | ~2x | AI generates pipeline configs, Docker setups |
| PM/Analysis | 4 PM | 2.7 PM | ~1.5x | AI helps with docs/reports but decisions are human |
| UI/UX Design | 3 PM | 2 PM | ~1.5x | AI assists but creative direction is human |

**Key**: PM gets the lowest multiplier because project management decisions can't be automated. QA gets the highest because test generation is highly automatable.

## Rule 32b: Derive What's Not Documented

If data exists but analysis doesn't:

1. **Don't ask for documentation** — derive it yourself
2. **Show your work** — present the derivation for validation
3. **Use project data** — not textbook examples

Example: If the backlog has 60 stories with SP values but no velocity history, calculate implied velocity from sprint boundaries.

## Rule 33b: Show the Math, Not Just the Result

| Bad | Good |
|-----|------|
| "Total effort: 15.4 PM" | Table showing each member's allocation × duration = PM |
| "Project takes 4 months" | "4 calendar months at 15.4 effective PM with 6 team members" |
| "AI reduces effort by 60%" | Table showing role-by-role multipliers with reasoning |

## Rule 34b: Compare Before and After

When two versions of a plan exist, ALWAYS present a variance table:

| Metric | v1 | v2 | Change | % |
|--------|-----|-----|--------|---|
| Duration | 9 months | 4 months | -5 months | -56% |
| Team Size | 14 | 6 | -8 | -57% |
| Total PM | 45.2 | 15.4 | -29.8 | -66% |
| Story Count | 60 | 58 | -2 | -3% |

Decision-makers need to see **what changed and by how much**.

## Rule 35b: Define Jargon with Project Examples

When the user asks "what does X mean?", give a concrete example from THEIR project data:

| Term | Bad (Textbook) | Good (Project-Specific) |
|------|----------------|------------------------|
| Person-month | "One person working full-time for one month" | "Sara at 100% for 4 months = 4.0 PM. Khalid at 60% for 3 months = 1.8 PM. Your team total is 15.4 PM." |
| Story point | "A relative measure of effort" | "In your backlog, SP 1 = simple field addition (like adding a phone field). SP 5 = cross-module integration (like the wallet-to-payment bridge)." |
| Sprint velocity | "Story points completed per sprint" | "Your team completes ~18 SP per 2-week sprint based on the last 3 sprints." |

## Estimation Checklist

Before delivering any estimation:

- [ ] Duration cross-checked across all source files
- [ ] Version inconsistencies flagged (v2 files with v1 data)
- [ ] SP scale documented (derived if not provided)
- [ ] Person-months calculated as allocation × duration per member
- [ ] AI multipliers applied per role (if AI-assisted project)
- [ ] Variance table shown when comparing plan versions
- [ ] All math shown, not just results
- [ ] Jargon defined with project-specific examples

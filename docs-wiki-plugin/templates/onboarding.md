# Onboarding: <Role or Team Name>

> Template usage: replace every `<...>` placeholder with real values, delete guidance lines, and remove example blocks that do not apply. Document the system **as it exists today**, not as it is planned to become. If a step only works on a future branch or an unreleased service, mark it clearly or leave it out until it is real.

| Field | Value |
|-------|-------|
| Audience | `<who this page is for, e.g. new backend engineer>` |
| Owner | `<team or person responsible for keeping this current>` |
| Last reviewed | `<YYYY-MM-DD>` |
| Estimated time to first contribution | `<e.g. 2-3 days>` |

## Welcome and overview

Briefly orient the newcomer. Keep it to what is true right now.

- **What this project is**: `<one or two sentences on the product or system>`
- **What you will be doing**: `<the role's day-to-day responsibilities>`
- **How this team works**: `<async/sync, working hours, where decisions happen>`
- **Where to find things**: `<repo locations, docs hub, chat channels>`

> Current-state reminder: link only to pages that describe how the system behaves today. If a doc is aspirational or in-progress, label it as such or omit it.

## Access and accounts checklist

Request and confirm access before local setup. Check each item as it is granted.

- [ ] `<Identity/SSO account>` provisioned and login confirmed
- [ ] `<Source control account>` with access to `<the repositories you will work in>`
- [ ] `<Chat/communication tool>` joined the relevant channels
- [ ] `<Issue/task tracker>` account and assignment to the active board
- [ ] `<CI/CD or build system>` read access (and write if your role needs it)
- [ ] `<Secrets/credentials manager>` access to the entries your role requires
- [ ] `<Cloud/hosting console>` access at the appropriate permission level
- [ ] `<VPN or network access>` configured if required
- [ ] `<Documentation/wiki>` edit access

> Never paste actual credentials, tokens, or secret values into this page or any wiki page. Record only *where* to obtain them (the secrets manager, an onboarding buddy, the team lead).

## Local setup steps

Steps to get a working environment. Keep commands generic; use placeholders for anything machine-, user-, or environment-specific.

1. Install prerequisites: `<language runtime + version>`, `<package manager>`, `<container runtime>`, `<other tools>`.
2. Clone the repository:

   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

3. Configure environment variables. Copy the example file and fill in values from the secrets manager:

   ```bash
   cp <example-env-file> <env-file>
   # edit <env-file> with values obtained from <secrets manager>
   ```

4. Install dependencies:

   ```bash
   <dependency-install-command>
   ```

5. Initialize local data or services (database, cache, message queue, etc.):

   ```bash
   <setup/migrate command>
   ```

6. Run the project and confirm it starts:

   ```bash
   <run command>
   ```

7. Verify your setup works:

   ```bash
   <test or healthcheck command>
   ```

> If any step fails, capture the error and check the troubleshooting page (see Related pages). Update this checklist if a step is outdated. Setup docs rot quickly. The person who hits a stale step should fix it.

Example (illustrative — not required):

```bash
# A typical setup loop looks like this; adapt to your stack
git clone <repository-url> && cd <repository-directory>
cp .env.example .env
<dependency-install-command>
<run command>
```

## Key concepts (links)

Link to existing pages that explain the system's core ideas. Prefer short, accurate pages over long ones. If a concept page does not exist yet, note the gap rather than inventing detail.

- [Architecture overview](<link>) — how the major pieces fit together
- [Data model / domain concepts](<link>) — the core entities and their relationships
- [Conventions and standards](<link>) — naming, structure, style rules
- [Environments](<link>) — what each environment is for and how they differ
- [Glossary](<link>) — shared vocabulary used by the team

## First tasks

A short, ordered list of low-risk tasks that build familiarity. Each should be completable with the access and setup above.

- [ ] Read the architecture overview and skim the main directories
- [ ] Complete local setup and get the project running
- [ ] Make a trivial, reversible change and open a draft change request to learn the workflow
- [ ] Pick a `<good-first-issue label or starter task>` from `<issue tracker>`
- [ ] Pair with `<onboarding buddy>` on `<a small real task>`

> Keep first tasks honest about current reality: assign work against the codebase as it is, not against a planned refactor.

## Who to ask

Point newcomers to the right person or channel by topic. Use roles and channels, not personal contact details.

| Topic | Who / where |
|-------|-------------|
| Access and accounts | `<role or channel>` |
| Local setup problems | `<role or channel>` |
| Architecture and design | `<role or channel>` |
| Task assignment and priorities | `<role or channel>` |
| Deployments and operations | `<role or channel>` |
| Anything unclear | `<onboarding buddy / team lead>` |

## Related pages

- [Repository README](<link>)
- [Contributing / workflow guide](<link>)
- [Troubleshooting and FAQ](<link>)
- [Environments and deployment](<link>)
- [Team directory or contacts](<link>)

---

> Maintenance note: this page is only useful if it matches reality. When a step breaks or a link dies, fix it in place. Review at least every `<interval, e.g. quarter>` and update the "Last reviewed" date.

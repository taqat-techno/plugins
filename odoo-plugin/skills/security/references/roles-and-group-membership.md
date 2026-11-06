# Roles and group membership: OCA `base_user_role`, revocation, global toggles

Read this before you change any user's groups, edit a role, or answer "why did this user lose
(or keep) access" on a database where OCA `base_user_role` is installed. Check that first:
`SELECT state FROM ir_module_module WHERE name = 'base_user_role'`.

## 1. A write to `res.users` rebuilds the user's groups from their roles

`base_user_role` overrides `res.users.write()` to call `set_groups_from_roles()` after every
write, whatever field was written. That call **replaces** the user's groups with the union of
their enabled roles' groups (role group + `implied_ids` + transitive implications).

- A user whose real groups exceed their role lines loses the extra groups on the next unrelated
  save: renaming the admin user can cut it down to one role's groups and lock it out of Settings.
- Other triggers of the same rebuild: `res.users.create`, `res.users.role` create/write/unlink, and
  the "Update user roles" cron (every few hours by default; often inactive on neutralized copies,
  active on production). Check `ir.cron` before assuming a group change will stick.
- **Safe way to change membership:** write from the group side:
  `env['res.groups'].browse(gid).write({'user_ids': [(3, uid)]})` (`users` before 19.0).
  `base_user_role` does not override `res.groups.write`, so `res_groups_users_rel` changes without a
  resync.
- Keep `res.users` **out** of any write allow-list (MCP profiles, integration users, scripts), so a
  routine field update cannot trigger the rebuild by accident.

## 2. When the role sync runs, and for whom

- `set_groups_from_roles()` resyncs **only users who hold at least one role line**. A user with
  zero `res.users.role.line` rows keeps groups added directly. A user with any role line has direct
  groups wiped at the next resync. Check `role_line_ids` before you choose between a direct group
  edit and a role edit.
- **Creating a role line does not sync.** Assigning a role by API, import or `create()` leaves the
  user holding the role and none of its groups. Re-saving the role (any `write`, e.g.
  `implied_ids: [(4, gid)]`) resyncs every holder. Code that assigns roles must call the sync
  itself.
- Roles linked to a job position are added and removed automatically when an employee's job
  changes, so "one role per user" also needs matching jobs.
- Look for overrides of `set_groups_from_roles` in other modules before relying on any of the above:
  a layer that replaces it without `super()` changes the semantics (see the reviewer's terminal
  override rule in `../../reviewer/references/integration_patterns.md`).

## 3. Code-defined roles are reset on every upgrade

A role declared in module XML without `noupdate` gets its group list rewritten on each `-u` of that
module, so groups added to it in the UI vanish at the next deploy.

- No-code extension that survives upgrades: create a **second role in the UI** and assign it
  alongside the first (roles combine). The role engine refuses a role with no user-type group, so
  give the new role `base.group_user` (or the portal type).
- If the access belongs in the official role, change the XML. Changing a role's user type
  (portal and internal) is a code-plus-migration change; the procedure is owned by the upgrade skill
  (`../../upgrade/SKILL.md`, "Production hand-edits to module-owned data").
- Clients that load access once (the POS till, an open Owl app) need a reload after the change.

## 4. A role's xmlid is not its group's xmlid

`res.users.role` `_inherits` `res.groups`, so a role and its group are different records with
different ids. `<field name="implied_ids" eval="[(4, ref('mod.role_x'))]"/>` on a `res.groups`
links `res.groups(<role id>)`: an arbitrary, unrelated group. It is silent, and a transitive
coverage test can still pass if the intended groups arrive by another path.

- Reference the capability group directly. If the role's own group really is the target, Odoo
  registers its xmlid as `<role_xmlid>_res_groups`.
- Test the **direct** `implied_ids` of the group, not the implied closure.
- Do not add an "is this id also a role id" heuristic: role and group ids overlap at low numbers,
  so it flags `base.group_user`.

## 5. `(4, ref(...))` only links: deleting the line revokes nothing

`(4, id)` is the idempotent link command, not a declaration of the full list. Removing it from data
XML and running `-u` leaves the link in place. Likewise `base_user_role` has already flattened the
role's implications into each holder's own groups. To revoke: unlink explicitly (`(3, id)`) in a
migration or hook, then resync holders (`set_groups_from_roles(force=True)`), and verify in
`res_groups_users_rel`.

## 6. Settings that imply a group for every internal user

A settings checkbox that adds a group to `base.group_user.implied_ids` (lots and serial numbers,
multi-currency, variants) changes access for every internal user at once.

- Apply it through the Settings UI. Calling `res.config.settings.execute()` from a script applies
  every field on the settings form, not only the one you meant.
- Verify afterwards that the group is still implied; on `base_user_role` databases a later role
  resync can strip it again.

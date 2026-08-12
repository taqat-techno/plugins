#!/usr/bin/env python3
"""owl_scaffold — generate a correctly-structured Odoo 17-19 OWL application.

Emits the module layout, the three-bundle manifest, the bootstrap chain
(controller -> index template -> main.js -> root component), a store service, a
data service that is the only holder of `orm`, a `useStore()` hook, a loader, a
self-registering first screen, and a test bootstrap.

The shape is derived from how Odoo's own large OWL application is organised, with
the four subsystems that are actively harmful in a v1 left out (records layer,
IndexedDB persistence, service worker, custom router) and a documented migration
path kept open for each.

The generated module is expected to pass `owl_lint.py` with zero findings.

Usage:
    python owl_scaffold.py --name my_console --title "My Console" --route /my/ui \\
        [--dest <addons-dir>] [--dry-run] [--force]

Standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# Templates. Token substitution, not str.format - JS and XML are full of braces.
#   __APP__    technical module name        my_console
#   __TITLE__  human title                  My Console
#   __ROUTE__  url base                     /my/ui
#   __CLASS__  CamelCase prefix             MyConsole
#   __PAGES__  screen registry category     my_console_pages
# --------------------------------------------------------------------------

MANIFEST = '''{
    'name': '__TITLE__',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'summary': 'Standalone OWL application',
    'depends': ['web'],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
    'data': [
        'security/__APP___security.xml',
        'security/ir.model.access.csv',
        'views/__APP___assets_index.xml',
        'views/__APP___config_views.xml',
    ],
    'assets': {
        # 1. FLOOR - the framework layer this app stands on. A second, smaller
        #    app (a customer display, a kiosk view) can reuse this bundle alone.
        '__APP__.base_app': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap_backend'),
            ('include', 'web._assets_core'),
            '__APP__/static/src/utils.js',
        ],
        # 2. THE APP - everything except the boot file. This is the name you
        #    publish as your extension point: satellite addons inject one line
        #    targeting THIS bundle, never assets_prod, or they are invisible to
        #    your unit tests.
        '__APP__._assets_app': [
            'web/static/src/module_loader.js',
            'web/static/lib/owl/owl.js',
            'web/static/lib/owl/odoo_module.js',
            ('include', '__APP__.base_app'),
            '__APP__/static/src/**/*',
            ('remove', '__APP__/static/src/backend/**/*'),
            # main.js mounts the app as an import side effect, so it must load
            # LAST. The glob above sweeps it into the middle; this cancels that
            # and assets_prod re-appends it at the end.
            ('remove', '__APP__/static/src/app/main.js'),
        ],
        # 3. THE ENTRY POINT - what the index template actually calls.
        '__APP__.assets_prod': [
            ('include', '__APP__._assets_app'),
            '__APP__/static/src/app/main.js',
        ],
        # 4. TESTS - take prod, drop the boot file, and let the tests mount the
        #    app themselves. This split is the whole reason for the triple.
        'web.assets_unit_tests_setup': [
            ('include', '__APP__.assets_prod'),
            ('remove', '__APP__/static/src/app/main.js'),
        ],
        'web.assets_unit_tests': ['__APP__/static/tests/unit/**/*'],
        'web.assets_tests': ['__APP__/static/tests/tours/**/*'],
        'web.assets_backend': ['__APP__/static/src/backend/**/*'],
    },
}
'''

CONTROLLER = '''from odoo import http
from odoo.http import request


class __CLASS__Controller(http.Controller):
    """Serves the standalone OWL application document.

    A full OWL app needs its OWN HTML document - not an inherit of the backend
    layout. The response body is empty; the root component owns the DOM.
    """

    @http.route(['__ROUTE__', '__ROUTE__/<int:config_id>'], type='http', auth='user')
    def __APP___ui(self, config_id=None, **kw):
        # Gate BEFORE rendering. A UI check is never authorization - this is the
        # server-side one, and every RPC the app makes is checked again by ACLs
        # and record rules under the calling user.
        if not request.env.user._is_internal():
            return request.not_found()

        config = request.env['__APP__.config'].browse(config_id) if config_id else None
        if config and not config.exists():
            return request.not_found()

        session_info = request.env['ir.http'].session_info()
        response = request.render('__APP__.index', {
            'session_info': session_info,
            '__APP___config_id': config.id if config else False,
        })
        # The document embeds session state, so it must never be cached.
        response.headers['Cache-Control'] = 'no-store'
        return response
'''

INDEX_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <template id="index" name="__TITLE__">&lt;!DOCTYPE html&gt;
        <html>
            <head>
                <title>__TITLE__</title>
                <meta charset="utf-8"/>
                <meta name="viewport"
                      content="width=device-width, initial-scale=1, user-scalable=no"/>
                <script type="text/javascript">
                    // The global `odoo` object is how server state reaches JS before
                    // any RPC happens. Read it directly from a screen if you need
                    // the config id at first render.
                    var odoo = <t t-out="json.dumps({
                        'csrf_token': request.csrf_token(None),
                        '__session_info__': session_info,
                        '__APP___config_id': __APP___config_id,
                        'debug': debug,
                    })"/>;
                    // Short-circuits the webclient menu service that web._assets_core
                    // drags in. Without this the app waits on a menu load it never uses.
                    odoo.loadMenusPromise = Promise.resolve();
                </script>
                <t t-call-assets="__APP__.assets_prod"/>
            </head>
            <!-- EMPTY on purpose. The root component owns the body. -->
            <body class="__APP__"/>
        </html>
    </template>
</odoo>
'''

MAIN_JS = '''/** @odoo-module */
import { mountComponent } from "@web/env";
import { getTemplate } from "@web/core/templates";
import { mount, reactive, whenReady } from "@odoo/owl";
import { Loader } from "@__APP__/app/components/loader/loader";
import { Root } from "@__APP__/app/__APP___app";

// Two independent OWL apps share one document.body.
//
// mountComponent() awaits startServices(), and the data service does its first
// RPC there - so without this the screen is blank for as long as that takes.
// The loader is a throwaway app mounted immediately; the root gets a callback
// to switch it off, and the loader then destroys its OWN app.
const loader = reactive({ isShown: true });

whenReady(() =>
    mount(Loader, document.body, { getTemplate, props: { loader } })
);

(async function startApp() {
    await whenReady();
    await mountComponent(Root, document.body, {
        name: "__TITLE__",
        props: { disableLoader: () => (loader.isShown = false) },
    });
})();
'''

ROOT_JS = '''/** @odoo-module */
import { Component, onMounted } from "@odoo/owl";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { useOwnDebugContext } from "@web/core/debug/debug_context";
import { useStore } from "@__APP__/app/hooks/use_store";
import { Navbar } from "@__APP__/app/components/navbar/navbar";

export class Root extends Component {
    static template = "__APP__.Root";
    static components = { MainComponentsContainer, Navbar };
    static props = { disableLoader: { type: Function, optional: true } };

    setup() {
        // A hook, never an import. Components must not import the store module.
        this.store = useStore();
        useOwnDebugContext();
        onMounted(() => this.props.disableLoader?.());
    }
}
'''

ROOT_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

    <t t-name="__APP__.Root">
        <div class="__APP__ d-flex flex-column vh-100">
            <Navbar/>
            <div class="flex-grow-1 overflow-auto position-relative">
                <!-- The entire screen-switching mechanism. store.page is set by
                     navigate(); the registry decides which component that name
                     maps to. -->
                <t t-if="store.page.component"
                   t-component="store.page.component"
                   t-props="store.page.props"/>
            </div>
        </div>
        <!-- NOT optional: the mount point every dialog, notification and overlay
             service renders into. Omit it and this.dialog.add(...) silently does
             nothing. -->
        <MainComponentsContainer/>
    </t>

</templates>
'''

ROOT_SCSS = '''.__APP__ {
    // Global app chrome only. Component styles live beside their component.
    background-color: var(--o-webclient-background-color, #f9f9f9);
}
'''

USE_STORE_HOOK = '''/** @odoo-module */
import { useService } from "@web/core/utils/hooks";

/**
 * The only sanctioned way a component reaches the store.
 *
 * useService() wraps a reactive service in useState, which is what makes the
 * component re-render when the store changes. Capturing env.services.__APP__
 * directly skips that and the component silently stops updating.
 */
export function useStore() {
    return useService("__APP__");
}
'''

STORE_JS = '''/** @odoo-module */
import { Reactive } from "@web/core/utils/reactive";
import { registry } from "@web/core/registry";

const PAGES = "__PAGES__";

/**
 * Application store: the domain state every screen shares.
 *
 * Extends Reactive so mutations drive renders. It depends on services; no
 * service may depend on it - the graph is strictly one-way.
 */
export class __CLASS__Store extends Reactive {
    constructor(env, deps) {
        super();
        this.env = env;
        this.data = deps.__APP___data;
        this.dialog = deps.dialog;
        this.notification = deps.notification;

        this.pageName = null;
        this.pageProps = {};
        this.ready = this.setup();
    }

    // setup() rather than the constructor, because setup() can be patched by an
    // extending addon and a constructor cannot.
    async setup() {
        this.navigate("Home");
        return this;
    }

    /** Resolved from the registry on read, so a late-registered screen still works. */
    get page() {
        const entry = registry.category(PAGES).get(this.pageName, null);
        return { component: entry && entry.component, props: this.pageProps };
    }

    get pages() {
        return registry.category(PAGES).getEntries();
    }

    navigate(name, props = {}) {
        if (!registry.category(PAGES).contains(name)) {
            throw new Error(
                `Unknown page "${name}". Registered: ` +
                    registry.category(PAGES).getEntries().map(([k]) => k).join(", ")
            );
        }
        this.pageName = name;
        this.pageProps = props;
    }
}

export const __APP___service = {
    dependencies: ["__APP___data", "dialog", "notification"],
    async start(env, deps) {
        // Returning the already-resolved store means no component ever observes
        // a half-loaded one.
        return new __CLASS__Store(env, deps).ready;
    },
};

registry.category("services").add("__APP__", __APP___service);
'''

DATA_JS = '''/** @odoo-module */
import { registry } from "@web/core/registry";

/**
 * The ONLY holder of orm/rpc in this application.
 *
 * Screens never call orm directly - they go through the store or this service.
 * Keeping server access behind one chokepoint is what makes retries, caching,
 * offline queuing or a transport swap a one-file change later.
 */
export class __CLASS__Data {
    constructor(env, deps) {
        this.env = env;
        this.orm = deps.orm;
        this.records = {};      // model name -> Map(id -> record)
        this.ready = this.load();
    }

    async load() {
        // Keep every record access behind an accessor shape like this from day
        // one. A real records layer can drop in behind the same API later.
        return this;
    }

    get(model, id) {
        const bucket = this.records[model];
        return bucket ? bucket.get(id) : undefined;
    }

    all(model) {
        return [...(this.records[model] || new Map()).values()];
    }

    _store(model, rows) {
        const bucket = (this.records[model] = this.records[model] || new Map());
        for (const row of rows) {
            bucket.set(row.id, row);
        }
        return rows;
    }

    /** Read with load=false so relational fields come back as raw ids. */
    async searchRead(model, domain = [], fields = [], options = {}) {
        const rows = await this.orm.searchRead(model, domain, fields, {
            ...options,
            load: false,
        });
        return this._store(model, rows);
    }

    async call(model, method, args = [], kwargs = {}) {
        return this.orm.call(model, method, args, kwargs);
    }
}

export const __APP___data_service = {
    dependencies: ["orm"],
    async start(env, deps) {
        return new __CLASS__Data(env, deps).ready;
    },
};

registry.category("services").add("__APP___data", __APP___data_service);
'''

LOADER_JS = '''/** @odoo-module */
import { Component, onWillDestroy, useState } from "@odoo/owl";

/**
 * Covers the gap between document-ready and services-started.
 *
 * Mounted as its own OWL app, so when it is done it destroys that app rather
 * than trying to unmount itself from a tree it does not belong to.
 */
export class Loader extends Component {
    static template = "__APP__.Loader";
    static props = { loader: Object };

    setup() {
        this.state = useState(this.props.loader);
        this.timeout = null;
        onWillDestroy(() => clearTimeout(this.timeout));
    }

    get hidden() {
        if (!this.state.isShown && !this.timeout) {
            this.timeout = setTimeout(() => this.__owl__.app.destroy(), 1000);
        }
        return !this.state.isShown;
    }
}
'''

LOADER_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

    <t t-name="__APP__.Loader">
        <div class="__APP__-loader position-fixed top-0 start-0 w-100 h-100 d-flex
                    align-items-center justify-content-center"
             t-att-class="{ 'd-none': hidden }"
             style="z-index: 2000; background: var(--o-webclient-background-color, #f9f9f9);">
            <div class="text-center">
                <div class="spinner-border" role="status"/>
                <div class="mt-2">Loading __TITLE__…</div>
            </div>
        </div>
    </t>

</templates>
'''

NAVBAR_JS = '''/** @odoo-module */
import { Component } from "@odoo/owl";
import { useStore } from "@__APP__/app/hooks/use_store";

export class Navbar extends Component {
    static template = "__APP__.Navbar";
    static props = {};

    setup() {
        this.store = useStore();
    }
}
'''

NAVBAR_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

    <t t-name="__APP__.Navbar">
        <nav class="__APP__-navbar d-flex align-items-center gap-3 px-3 py-2 border-bottom">
            <span class="fw-bold">__TITLE__</span>
            <div class="d-flex gap-2">
                <button class="btn btn-sm btn-light"
                        t-foreach="store.pages" t-as="page" t-key="page[0]"
                        t-att-class="{ active: store.pageName === page[0] }"
                        t-on-click="() => store.navigate(page[0])">
                    <t t-esc="page[1].label or page[0]"/>
                </button>
            </div>
        </nav>
    </t>

</templates>
'''

HOME_JS = '''/** @odoo-module */
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useStore } from "@__APP__/app/hooks/use_store";

export class HomeScreen extends Component {
    static template = "__APP__.HomeScreen";
    static props = {};

    setup() {
        this.store = useStore();
    }
}

// Self-registration at MODULE TOP LEVEL. Registering from inside setup() or an
// async callback is silently ignored by any consumer that snapshots the
// category, and the failure looks like an unmatched route.
registry.category("__PAGES__").add("Home", {
    component: HomeScreen,
    label: "Home",
});
'''

HOME_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

    <t t-name="__APP__.HomeScreen">
        <div class="p-4">
            <h1>__TITLE__</h1>
            <p class="text-muted">
                Replace this screen. Register new ones at the bottom of their own
                file with registry.category("__PAGES__").
            </p>
        </div>
    </t>

</templates>
'''

UTILS_JS = '''/** @odoo-module */

// Dependency-free helpers, kept OUTSIDE app/ so a second, smaller app can
// include this file alone without pulling in the whole application bundle.

export function formatIdList(ids) {
    return (ids || []).join(", ");
}
'''

CONFIG_PY = '''from odoo import _, fields, models


class __CLASS__Config(models.Model):
    _name = '__APP__.config'
    _description = '__TITLE__ Configuration'

    name = fields.Char(required=True, default='Default')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)

    def open_ui(self):
        """Backend entry point. Hands off to the standalone app URL.

        target='self' replaces the webclient rather than opening a dialog.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '__ROUTE__/%d' % self.id,
            'target': 'self',
        }

    def name_action_open(self):
        return self.open_ui()
'''

LOAD_MIXIN_PY = '''from odoo import api, models


class __CLASS__LoadMixin(models.AbstractModel):
    """Per-model contract for what the client is allowed to load.

    Inherit this on every model the app loads, and override the two hooks. The
    orchestrator is deliberately tiny - the value is that there is exactly ONE
    place that decides domain and field list per model.
    """

    _name = '__APP__.load.mixin'
    _description = '__TITLE__ Load Mixin'

    @api.model
    def _load_data_domain(self, data, config):
        """Return the domain for this model. `data` holds what earlier models
        already loaded, so the model list is an ordered pipeline, not a set."""
        return []

    @api.model
    def _load_data_fields(self, config):
        """Explicit field list. Never return every field - the payload reaches
        every client with the app open."""
        return ['id']

    @api.model
    def _load_data_search_read(self, data, config):
        domain = self._load_data_domain(data, config)
        if domain is False:
            return []
        # load=False returns raw ids for relational fields instead of
        # (id, display_name) tuples. Omitting it doubles the payload.
        return self.search(domain).read(self._load_data_fields(config), load=False)
'''

SECURITY_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <record id="group___APP___user" model="res.groups">
        <field name="name">__TITLE__ / User</field>
        <field name="category_id" ref="base.module_category_hidden"/>
    </record>

    <record id="group___APP___manager" model="res.groups">
        <field name="name">__TITLE__ / Manager</field>
        <field name="category_id" ref="base.module_category_hidden"/>
        <field name="implied_ids" eval="[(4, ref('group___APP___user'))]"/>
        <field name="users" eval="[(4, ref('base.user_root')), (4, ref('base.user_admin'))]"/>
    </record>

    <record id="__APP___config_company_rule" model="ir.rule">
        <field name="name">__TITLE__ config: company scoped</field>
        <field name="model_id" ref="model___APP___config"/>
        <field name="domain_force">
            ['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]
        </field>
    </record>
</odoo>
'''

ACCESS_CSV = '''id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access___APP___config_user,__APP__.config user,model___APP___config,group___APP___user,1,0,0,0
access___APP___config_manager,__APP__.config manager,model___APP___config,group___APP___manager,1,1,1,1
'''

CONFIG_VIEWS = '''<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <record id="__APP___config_view_form" model="ir.ui.view">
        <field name="model">__APP__.config</field>
        <field name="arch" type="xml">
            <form>
                <header>
                    <button name="open_ui" type="object" string="Open __TITLE__"
                            class="btn-primary"/>
                </header>
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="company_id" groups="base.group_multi_company"/>
                        <field name="active"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="__APP___config_view_list" model="ir.ui.view">
        <field name="model">__APP__.config</field>
        <field name="arch" type="xml">
            <list>
                <field name="name"/>
                <field name="company_id" groups="base.group_multi_company"/>
            </list>
        </field>
    </record>

    <record id="__APP___config_action" model="ir.actions.act_window">
        <field name="name">__TITLE__</field>
        <field name="res_model">__APP__.config</field>
        <field name="view_mode">list,form</field>
    </record>

    <menuitem id="menu___APP___root" name="__TITLE__"
              web_icon="__APP__,static/description/icon.png"
              groups="group___APP___user"/>
    <menuitem id="menu___APP___config" name="Configuration"
              parent="menu___APP___root" action="__APP___config_action"
              groups="group___APP___manager"/>
</odoo>
'''

TEST_UTILS = '''/** @odoo-module */
import { getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Root } from "@__APP__/app/__APP___app";

/**
 * One helper every unit test uses.
 *
 * This is only possible because root state lives in a SERVICE. If the store
 * were held inside a component there would be no seam to reach it from a test.
 */
export async function setup__CLASS__Env() {
    await mountWithCleanup(Root, { props: { disableLoader: () => {} } });
    return getService("__APP__");
}
'''

HOME_TEST = '''/** @odoo-module */
import { expect, test } from "@odoo/hoot";
import { setup__CLASS__Env } from "@__APP__/../tests/unit/utils";

test("the store starts on the Home page", async () => {
    const store = await setup__CLASS__Env();
    expect(store.pageName).toBe("Home");
    expect(store.page.component).toBeTruthy();
});

test("navigating to an unknown page throws with the registered names", async () => {
    const store = await setup__CLASS__Env();
    expect(() => store.navigate("Nope")).toThrow(/Unknown page/);
});
'''

README_MD = '''# __TITLE__

A standalone OWL application served on `__ROUTE__`.

## Structure

| Path | Role |
|---|---|
| `controllers/main.py` | The route. Auth gate, `no-store`, renders the index |
| `views/__APP___assets_index.xml` | The app's own HTML document. Body is empty |
| `static/src/app/main.js` | Boot only. Removed from the private bundle so it loads last |
| `static/src/app/__APP___app.js` | Root component |
| `static/src/app/services/__APP___store.js` | Domain state, registered as service `__APP__` |
| `static/src/app/services/data_service.js` | The **only** holder of `orm` |
| `static/src/app/hooks/use_store.js` | The only sanctioned way a component reaches the store |
| `static/src/app/screens/` | Anything a route can point at; each self-registers |
| `static/src/app/components/` | Everything else. Not routable |

## Layer rules

- Components and screens obtain the store with `useStore()`, never by importing it.
- Screens never call `orm` or `rpc` — they go through the store or the data service.
- Services never import the store. The dependency graph is one-way.
- Models never know about components.
- `static/src/app/` is the app; directory placement routes a file to a bundle.
- Co-locate `.js` + `.xml` + `.scss` per component. `static/src/scss/` is global only.

## Bundles

Three, and the split matters:

- `__APP__.base_app` — framework floor. A second, smaller app can reuse this alone.
- `__APP__._assets_app` — the app minus the boot file. **Publish this name** as your
  extension point; satellite addons inject one line targeting it.
- `__APP__.assets_prod` — the private bundle plus `main.js`, appended last.

## Deliberately not included

Add each only at its signal, not before:

| Not included | Add when |
|---|---|
| Records layer | You hand-write `x.find(i => i.id === id)` in three places, or a relation must be traversable both ways and stay reactive |
| IndexedDB persistence | The app must accept writes with no connection |
| Service worker | The app must *cold start* offline |
| URL router | Users ask for a back button, a deep link, or refresh-in-place |

Migration paths are kept open: record access already goes through
`data.get(model, id)` accessors, and screens already self-register in a registry
category, so adding `route:` later does not mean rewriting registrations.

## Verify

```bash
python <plugin>/scripts/owl/owl_lint.py <path-to-this-module>
```
'''

FILES = [
    ("__init__.py", "from . import controllers\nfrom . import models\n"),
    ("__manifest__.py", MANIFEST),
    ("README.md", README_MD),
    ("controllers/__init__.py", "from . import main\n"),
    ("controllers/main.py", CONTROLLER),
    ("models/__init__.py", "from . import __APP___config\nfrom . import __APP___load_mixin\n"),
    ("models/__APP___config.py", CONFIG_PY),
    ("models/__APP___load_mixin.py", LOAD_MIXIN_PY),
    ("security/__APP___security.xml", SECURITY_XML),
    ("security/ir.model.access.csv", ACCESS_CSV),
    ("views/__APP___assets_index.xml", INDEX_XML),
    ("views/__APP___config_views.xml", CONFIG_VIEWS),
    ("static/src/utils.js", UTILS_JS),
    ("static/src/app/main.js", MAIN_JS),
    ("static/src/app/__APP___app.js", ROOT_JS),
    ("static/src/app/__APP___app.xml", ROOT_XML),
    ("static/src/app/__APP___app.scss", ROOT_SCSS),
    ("static/src/app/hooks/use_store.js", USE_STORE_HOOK),
    ("static/src/app/services/__APP___store.js", STORE_JS),
    ("static/src/app/services/data_service.js", DATA_JS),
    ("static/src/app/components/loader/loader.js", LOADER_JS),
    ("static/src/app/components/loader/loader.xml", LOADER_XML),
    ("static/src/app/components/navbar/navbar.js", NAVBAR_JS),
    ("static/src/app/components/navbar/navbar.xml", NAVBAR_XML),
    ("static/src/app/screens/home_screen/home_screen.js", HOME_JS),
    ("static/src/app/screens/home_screen/home_screen.xml", HOME_XML),
    ("static/tests/unit/utils.js", TEST_UTILS),
    ("static/tests/unit/home_screen.test.js", HOME_TEST),
]


def camel(name: str) -> str:
    return "".join(p.capitalize() for p in re.split(r"[_\-\s]+", name) if p)


def substitute(text: str, app: str, title: str, route: str) -> str:
    return (text
            .replace("__CLASS__", camel(app))
            .replace("__PAGES__", "%s_pages" % app)
            .replace("__TITLE__", title)
            .replace("__ROUTE__", route)
            .replace("__APP__", app))


def build(app: str, title: str, route: str) -> dict:
    return {substitute(rel, app, title, route): substitute(body, app, title, route)
            for rel, body in FILES}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="owl_scaffold",
        description="Generate a correctly-structured Odoo OWL application module.")
    ap.add_argument("--name", required=True,
                    help="technical module name, snake_case (e.g. my_console)")
    ap.add_argument("--title", default="", help="human title (default: derived from --name)")
    ap.add_argument("--route", default="", help="URL base (default: /<name>/ui)")
    ap.add_argument("--dest", default=".", help="addons directory to create the module in")
    ap.add_argument("--dry-run", action="store_true", help="list files without writing")
    ap.add_argument("--force", action="store_true", help="overwrite an existing directory")
    args = ap.parse_args(argv)

    app = args.name.strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", app):
        print("error: --name must be snake_case starting with a letter (got %r)" % app,
              file=sys.stderr)
        return 2
    title = args.title.strip() or camel(app).replace("_", " ")
    route = (args.route.strip() or "/%s/ui" % app).rstrip("/")
    if not route.startswith("/"):
        print("error: --route must start with '/'", file=sys.stderr)
        return 2

    root = Path(args.dest).expanduser() / app
    files = build(app, title, route)

    if args.dry_run:
        print("Would create %d files under %s\n" % (len(files), root))
        for rel in sorted(files):
            print("  %s" % rel)
        return 0

    if root.exists() and not args.force:
        print("error: %s already exists (use --force to overwrite)" % root, file=sys.stderr)
        return 2

    for rel, body in sorted(files.items()):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")

    print("Created %d files under %s\n" % (len(files), root))
    print("Next:")
    print("  1. Install the module, then open Configuration and click 'Open %s'." % title)
    print("     Or go straight to %s" % route)
    print("  2. Verify the bundle split in an odoo shell:")
    print("       env['ir.qweb']._get_asset_links('%s.assets_prod')   # must contain main.js" % app)
    print("       env['ir.qweb']._get_asset_links('%s._assets_app')   # must NOT" % app)
    print("  3. Lint it:")
    print("       python owl_lint.py %s" % root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

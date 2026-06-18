# Credentials — developer guide

n8n-style, **owner-global**, encrypted credentials shared across all of a user's projects/bots.
A flow node references a credential by **id**; secrets never appear in the flow JSON. The engine
resolves the id to plaintext (oauth tokens are refreshed) at runtime over an internal endpoint.

This app is intentionally **registry-driven** so new credential types, auth modes, OAuth
providers, and dynamic option-loaders are added with a few lines and no schema migration.

---

## Data model — ONE table for everything

`models/credential.py :: Credential`
- `owner` (User, required) — the scope. `type_key` (CharField) — points at a registry type.
- `name`, `data_encrypted` (Fernet token of a JSON dict), `deleted_at` (soft delete), timestamps.
- `UniqueConstraint(owner, name) WHERE deleted_at IS NULL`.
- **There is no per-type model.** Every credential — API key, OAuth, AI provider — is one row whose
  shape is defined by its `type_key`'s registry entry. To support a new service you do NOT add a model.

Encryption: `services/crypto.py` (`encrypt(dict)->str`, `decrypt(str)->dict`), key =
`settings.CREDENTIALS_FERNET_KEY` or derived from `SECRET_KEY`. Never log decrypted data.

---

## 1. Add a new credential TYPE  →  `registry.py`

Append one dict to `CREDENTIAL_TYPES`. Types are **purpose-specific** (a service), not generic auth
schemes. Fields: `key`, `label`, `icon` (lucide name), `color` (hex, drives the UI icon), `mode`
(how the engine applies it at runtime), `fields` (user-entered values), and for OAuth `provider` + `scopes`.

```python
{"key":"stripe", "label":"Stripe", "icon":"key", "color":"#635BFF", "mode":"bearer",
 "fields":[{"name":"api_key","label":"Secret key","type":"password","secret":True,"required":True}]}
```
Field `type`: `text|password|number|select|textarea`. `secret:True` ⇒ masked in API output.
That's it — the type appears in the UI card-picker (panel + dashboard) automatically.

## 2. Auth MODES (how the engine applies a credential)

The engine's `applyCredential` (engine repo `handlers/http_request.go`) switches on `mode`:
`apikey` (token+param_name+placement) · `bearer` (Authorization: Bearer token) · `header`
(custom header) · `basic` (base64 user:pass) · `oauth2` (Bearer access_token, refreshed server-side)
· `none` (storage only). A new mode = one `case` there; most services reuse an existing mode.

## 3. Add an OAuth2 provider  →  `oauth_providers.py` + `registry.py`

- Add a provider entry (authorize/token/userinfo URLs, client_id/secret from
  `get_config("oauth_<p>", ...)` / env). Each scope-set is a **separate type** (`mode:"oauth2"`,
  `provider`, `scopes`) — e.g. `google_email` / `google_sheets` / `google_drive`.
- Flow: `views/oauth.py` `start` (returns the consent URL, signed state) → user consents →
  `callback` exchanges the code, `_upsert_credential` stores tokens. `services/oauth.py
  get_valid_access_token(cred)` refreshes on demand. Client id/secret live in the
  `oauth_<provider>` dynamic config (admin), NOT per credential.
- Adding scopes to an existing type requires users to **reconnect** to grant them.

## 4. Add a dynamic option-loader (load-options)  →  `services/options.py`

For node fields whose options come from the 3rd-party API (e.g. "pick a spreadsheet"). Append a
loader `(token, params) -> [{"value","label"}]` to `OPTION_LOADERS`. The panel calls
`POST /api/v1/credentials/options/<resource>/ {credential_id, params}`; the backend resolves the
credential to a token and runs the loader. Existing: `google_spreadsheets`, `google_sheet_tabs`,
`google_sheet_columns`, `google_drive_folders`, `google_drive_files`.

---

## API surface (owner-scoped; request.user)

```
GET    /api/v1/credentials/types/                 # read-only registry (key,label,icon,color,mode,fields,provider,scopes)
GET    POST   /api/v1/credentials/                # list (filter ?type_key=) / create {type_key,name,data}
GET PATCH DELETE /api/v1/credentials/<id>/        # detail (masked) / rename+merge / soft delete
POST   /api/v1/credentials/<id>/test/             # stub
POST   /api/v1/credentials/oauth/<provider>/start/    # {type_key} -> {authorize_url}
GET    /api/v1/credentials/oauth/<provider>/callback/ # Google redirects here (AllowAny)
POST   /api/v1/credentials/options/<resource>/    # {credential_id, params} -> {options:[{value,label}]}
GET    /api/v1/internal/credentials/<id>/         # ENGINE only: X-Internal-Token + X-Project-Id (owner guard) -> decrypted
```

## How the engine consumes a credential (other repos)

- **engine-golang**: a shared `CredentialResolver` (built in `executors/executor.go
  SetCredentialConfig`) is injected into every credential-consuming handler via
  `SetCredentialResolver`. A handler reads `data["credential_id"]`, calls `Resolve(id)`, and uses
  the returned `{type_key, mode, data}`. To make a NEW node use credentials: add the resolver field +
  setter to its handler, store a pointer in the executor, and inject it in `SetCredentialConfig`.
- **bot-constructor-panel**: declare a `credential` field in the node manifest
  (`{"type":"credential","key":"credential_id","credentialType":"<type>"}`) and/or a `dynamic_select`
  field (`{"type":"dynamic_select","resource":"<loader>","dependsOn":[...]}`). See that repo's
  `docs/CREDENTIAL_FIELDS.md`.

## Invariants
- Secrets only ever travel as a credential **id** inside a flow; resolution is server-side.
- Everything is a registry entry — adding a type/mode/provider/loader never needs a DB migration.

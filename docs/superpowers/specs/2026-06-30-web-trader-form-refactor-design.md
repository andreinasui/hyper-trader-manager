# Web Trader Form Refactor Design

## Goal

Unify trader creation and trader settings editing behind one form path so a config-field change is implemented once.

## Current Problems

- `TraderConfigForm.tsx` owns UI, defaults, normalization, validation merging, unit conversion, and submit shaping in one large component.
- Create and edit flows share the component, but route-level logic still diverges.
- Name and description are edited separately in `TraderOverview`, so metadata and config have different save paths.
- Defaults and legacy config normalization live near route/component code instead of one model layer.
- Collapsed advanced sections require component-local deep merge logic to avoid losing values.

## Chosen Approach

Use one canonical form model plus one `TraderForm` UI shell.

`TraderForm` accepts `mode="create" | "edit"`, initial data, submit state, and one `onSubmit` callback. It renders the same metadata and config fields in both modes. Create mode also renders wallet address and private key. Edit mode does not render private key and should treat wallet address as existing account identity.

No field registry or dynamic form framework. The form is complex, but not complex enough to justify building a local form engine.

## Files

Modify:

- `web/src/components/traders/TraderConfigForm.tsx`: rename/rework into `TraderForm.tsx` or keep filename during migration and export `TraderForm`.
- `web/src/lib/schemas/trader-config.ts`: keep Zod schemas, align create/edit types with the canonical form shape.
- `web/src/routes/traders/new.tsx`: become thin create page using `TraderForm` and model payload helper.
- `web/src/routes/traders/[id].tsx`: remove metadata edit state from page, use `TraderForm` for metadata plus config updates.
- `web/src/components/traders/overviews/TraderOverview.tsx`: stop owning editable name/description fields.
- Existing form tests: update around unified behavior.

Add:

- `web/src/components/traders/trader-form-model.ts`: defaults, normalization, validation, and API payload helpers.

Do not add section components in the first pass unless the single form file remains too large after logic moves out. If needed later, split by visible panels only: account, risk, bucket.

## Form Model

`trader-form-model.ts` owns non-UI form behavior:

- `defaultTraderFormValues`: one source for create defaults.
- `normalizeTraderConfig(config)`: fills legacy missing keys such as `bucket_config`.
- `buildInitialTraderForm(mode, trader?)`: creates modular-forms initial values for create or edit.
- `validateTraderForm(mode, values)`: merges partial form values with initial values, then applies the right schema.
- `toCreateTraderRequest(values)`: trims optional metadata and returns the API create payload.
- `toUpdateTraderRequests(values)`: trims optional metadata and returns separate existing API payloads: `{ info, config }`.

The model derives `config.provider_settings.self_account.address` from `wallet_address` before submit. UI should not duplicate that rule.

## UI Behavior

- Create mode shows metadata, wallet address, private key, copy account, network, account type, advanced config, and one submit button.
- Edit mode shows metadata and config in the Configuration tab, with one submit button.
- Edit mode removes the separate name/description save button from Overview.
- Advanced settings can stay collapsed, but hidden values must be preserved by model merge.
- One-option strategy type becomes static text or hidden default, not a select.
- Max leverage toggle remains, but model owns the rule for `null` versus default max leverage.
- Bucket mode remains UI state because it controls visible fields; model owns normalized bucket output.

## Route Behavior

`new.tsx` should only:

- render page chrome;
- render `TraderForm mode="create"`;
- call create mutation with `toCreateTraderRequest(values)`;
- invalidate trader queries and navigate back to `/traders`.

`[id].tsx` should only:

- load trader/detail/status data;
- render overview/logs/configuration tabs;
- render `TraderForm mode="edit"` in configuration;
- call one UI-level update flow with `toUpdateTraderRequests(values)`, using the existing metadata endpoint and config endpoint.

Trader runtime actions remain out of scope for this refactor.

## Testing

Add or update tests at the smallest useful level:

- Model tests for create defaults, edit initial values, legacy config normalization, create payload, edit payload, and hidden-field merge.
- Component tests that create mode shows wallet/private key and edit mode hides private key while showing metadata/config.
- Submit test proving one changed config value goes through the same form path for create and edit.

No broad e2e rewrite in this refactor.

## Ponytail Cuts Included

- Delete duplicated semver/config helper logic when touched.
- Remove the one-option strategy select.
- Avoid field registry, wizard, autosave, and generated form abstractions.
- Keep `@modular-forms/solid`; changing form library is out of scope.

## Non-Goals

- No new form library.
- No dynamic schema-driven field renderer.
- No UI redesign beyond removing duplicate/fragmented form flows.
- No backend API contract changes. Edit submit may call the existing metadata endpoint and config endpoint from one UI submit action.

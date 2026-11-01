# Coding conventions

These guidelines apply throughout this sync provider repository. Match the
existing architecture and the TMDbHelper provider contract when adding or
extending functionality.

## Commit messages

- Prefix every commit subject with an appropriate emoji shortcode, matching the
  existing history (for example, `:bug:` for fixes, `:sparkles:` for new features,
  `:zap:` for improvements, `:bookmark:` for version bumps, and `:robot:` for
  agent instructions).
- Follow the shortcode with a space and a concise description of the change.
- Commit messages are always a single line: the emoji shortcode and the
  description only. Never add a body, bullet points, extended description,
  `Co-Authored-By` or other attribution trailers, or any other lines.

## Agree on the approach before implementation

- Before implementing changes involving item data, database access, or sync,
  inspect the affected data flow, relevant base classes, and callers, including
  the core provider interfaces consumed by the module. Identify which layer and
  class should own each part of the change.
- Present a concise proposed approach and obtain agreement before editing
  implementation files. Name the modules/classes to change, their
  responsibilities, the extension points to use, and an existing implementation
  that demonstrates the relevant pattern.
- Explain how the proposal follows these conventions; proximity alone does not
  make an existing implementation an appropriate reference.
- Raise architectural questions early, with a recommended option and meaningful
  alternatives where applicable.
- Keep implementation within the agreed responsibilities and patterns.
- If new findings require changing the owning layer, shared abstraction, or
  agreed pattern, explain the proposed revision and obtain approval before
  implementing that deviation.

## Responsibilities and boundaries

- The provider class declares identity, capabilities, registered classes,
  authorization, activity retrieval, and provider-owned clients.
- API or library clients own transport, authentication, pagination, and source
  requests.
- Sync classes coordinate retrieval and refresh behavior through the existing
  sync interfaces. Sync item classes map source data into sync records.
- Database classes and getters own persistence and queries. Keep SQL and
  persistence operations out of actions, directory containers, and output
  mappers.
- Action classes own service-specific writes and declare their invalidation
  dependencies through the existing action interfaces.
- Supplier classes expose ratings, statistics, monitored lists, or other
  declared capabilities through their corresponding core interfaces.
- Provider-specific settings, cache handling, mappings, and service behavior
  belong in this module. Shared orchestration and provider-interface definitions
  belong in TMDbHelper core.
- Distinguish source data -> sync records from directory entries -> list-item
  dictionaries. Keep each mapping in its owning layer.
- Prefer the owning layer's existing configuration and extension points. Do not
  place feature logic in shared infrastructure merely because it is reachable
  from the caller.
- Resolve uncertain ownership during approach approval. A coordinated core
  change must be proposed explicitly rather than worked around in the module.

## Organization and reuse

- Prefer hanging indents for continuation lines over vertical alignment with
  the opening delimiter. Follow PEP 8's hanging-indent guidance:
  put no arguments on the first line and indent continuation lines to clearly
  distinguish them from the surrounding code. Use an extra indentation level
  to distinguish continued function parameters from the body.
- Always use explicitly named absolute imports. Relative imports and wildcard
  (`from ... import *`) imports are not permitted.
- Keep a distinct feature in its own appropriately named modules.
- Update provider registrations, route declarations, package exports, and all
  imports when moving or renaming classes or modules. Remove unused imports and
  obsolete references.
- Prefer small subclasses for variations. Override the differing query,
  retrieval, or mapping behavior and inherit shared logic.
- Reuse `jurialmunkey.ftools.cached_property` and `jurialmunkey.parser.try_int`
  where applicable.
- Configure attributes before accessing cached properties. Treat cached results
  as belonging to one configured instance.
- Implement object oriented programming (OOP) practices where practical. Create
  classes with properties. Use abstractions, inheritance, and subclassing.
- Follow EAFP programming principles. Avoid using guards to deal with errors
  arising from unexpected or misconfigured data. Never wallpaper over issues
  or mask the error; investigate the underlying cause.
- Prefer flat structures. Avoid nesting loops. Prefer comprehensions if possible.
- Functions in classes should be simple and have a single purpose. Avoid god
  functions/classes. Break complex code into smaller abstracted parts.
- When using cached properties, prefer a `get_x()` method which returns the data
  into the cached property rather than doing the work directly in the property.

## Changes to shared classes

- Put feature-specific behavior in the appropriate concrete class or subclass.
  Modify a shared base class only when the behavior belongs to all affected
  subclasses; use existing extension points for variations.
- Before proposing a shared-class change, inspect its subclasses, overrides,
  and callers. Explain why the behavior belongs in the shared abstraction and
  how it affects existing consumers as part of approach approval.
- Preserve the shared class's contract. Do not add feature-specific branches to
  shared infrastructure to avoid implementing the appropriate subclass behavior.
- Extend the core interfaces through inheritance. Do not copy their
  implementations into the provider or replace them with parallel abstractions.

## Required inheritance and provider contract

- Read the applicable core base classes, provider documentation, and
  `SyncProviderLoader` validation before changing registered extension classes.
  These define the supported contract.
- Export a zero-argument `Provider` class from the package's `__init__.py` using
  a named absolute import from its `provider.py`.
- `Provider` must inherit
  `tmdbhelper.lib.sync.providers.base.SyncProvider`.
- Registered extension classes must inherit the corresponding core base,
  directly or through an appropriate subclass. Matching method names or being
  callable is not sufficient.

| Registration | Required core base |
| --- | --- |
| `sync_classes` | `tmdbhelper.lib.sync.datatype.DataType` |
| `service_sync_classes` | `tmdbhelper.lib.sync.providers.services.ServiceDataType` |
| `action_classes` and `service_action_classes` | `tmdbhelper.lib.script.sync.item.ItemSync` |
| `getter_classes` | `tmdbhelper.lib.sync.datasync.SyncDataGetter` |
| `scrobbler_class` | `tmdbhelper.lib.monitor.scrobble.ScrobbleRequest` |
| `ratings_classes` | `tmdbhelper.lib.sync.providers.ratings.RatingsSupplier` |
| `imdb_top250_classes` | `tmdbhelper.lib.sync.providers.imdb_top250.IMDbTop250Supplier` |
| `stats_class` | `tmdbhelper.lib.sync.providers.stats.StatsSupplier` |
| `monitor_lists_class` | `tmdbhelper.lib.sync.providers.monitor_lists.MonitorListsSupplier` |
| `directory_item_class` | `tmdbhelper.lib.items.directories.base.basedir_item.BaseDirItem` |

- Implement required abstract methods or inherit working implementations from
  an appropriate subclass. Preserve constructor signatures, return values, and
  lifecycle behavior expected by core callers.
- Implement `Provider.is_authorized()`. Providers registering sync or service
  sync classes must also implement `get_last_activities()`.
- Sync classes and registered class factories must inherit the required base
  and declare a non-empty `method` identifying their cache activity.
- Providers declaring watched support must register `movies_to_watch`,
  `shows_to_watch`, and `shows_in_progress` getters. Each must implement or
  inherit `get_items()` and `get_sync_succeeded()`.
- Scrobblers must return `ScrobbleResult` from `scrobble()`. Those using the
  inherited implementation must implement `get_scrobbler_item()` and
  `send_request(method, payload)`.
- Register only supported capabilities. Preserve the inherited empty or `None`
  defaults for capabilities the provider does not supply.
- Service action names must start with the provider ID and be globally unique.
  List route names must start with `<provider_id>_`. A directory item must target
  a route registered by the provider.
- Preserve the provider and sync context supplied by core. Forward that context
  into nested factories, getters, and snapshots instead of constructing another
  `Provider()` within an operation.
- These inheritance requirements apply to registered extension classes.
  Provider-internal helpers may use their own appropriate abstractions.

## Versioning and compatibility

- Treat these as separate versions:
  - The provider add-on release version in `addon.xml`.
  - The minimum TMDbHelper dependency version in `addon.xml`.
  - The provider contract declared by `Provider.interface_version`.
- Declare `interface_version` explicitly on `Provider`. Use the interface the
  implementation actually satisfies; do not derive it dynamically from the
  installed core or copy the loader's current version.
- Check the loader's supported interface range when changing the contract.
  At the time these instructions were written, the current and minimum
  supported interface versions are both `4`.
- Ordinary provider fixes and features do not require an interface-version
  change when they remain within the existing contract.
- When the provider relies on newly introduced core behavior, raise its minimum
  `plugin.video.themoviedb.helper` dependency to the first release providing all
  required behavior. Do not claim compatibility with an older core.
- Provider changes must not independently redefine the shared interface.
  Propose required core contract changes before implementing dependent changes.
- For coordinated core contract changes, prefer inherited defaults that preserve
  existing provider behavior. A new mandatory requirement without a compatible
  default requires an explicit base-class contract, loader validation, increases
  to both current and minimum interface versions, and an interface-history entry
  in the core provider documentation.
- For a provider release, increment its add-on version using the repository's
  existing version scheme. Do not change the interface version merely to match
  a release version.
- Documentation-only changes do not require a runtime version bump. Do not add
  unrelated version bumps to development changes unless requested or required
  by the release workflow.
- Keep dependency declarations, provider declarations, and compatibility
  documentation consistent.

## Sync, persistence, and failures

- Retrieve and persist synced data through the existing sync and database
  interfaces. Bind query values with SQL placeholders.
- Preserve the distinction between failed or incomplete retrieval and a
  successful empty result.
- Replace cached snapshots only after complete, successful retrieval. Preserve
  existing cached data and activity timestamps when retrieval fails.
- Report sync success only when the requested prerequisites are current or
  successfully refreshed. Access to stale cached items is not evidence of
  successful sync.
- Use the existing invalidation interfaces after successful writes. Declare the
  affected sync types rather than duplicating shared invalidation orchestration.
- Keep provider discovery and construction free of interactive authentication
  or configuration prompts.
- Apply settings migrations through the existing provider migration hook before
  constructing clients that depend on those settings.

## Dates

- Preserve the timestamp format and timezone required by each interface.
  Normalize source timestamps at the appropriate provider boundary.
- Use local calendar boundaries when grouping UTC watch timestamps. Use actual
  calendar months rather than assuming every month has 30 days.
- Reuse existing date conversion and formatting helpers where applicable.
- Keep storage timestamps separate from user-facing date formatting.

## Verification

- Before reporting completion, review the completed implementation diff against
  the approved approach and responsibility boundaries. Check that each change
  belongs to its owning layer and follows the agreed extension points.
- Review mapping direction, provider registrations, routes, imports, package
  exports, and cache configuration order.
- Confirm that registered classes inherit the required bases and satisfy the
  loader's validation and core callers' contracts.
- Confirm that attributes and injected context are configured before cached
  properties are accessed.
- For shared-class changes, review the effect on existing subclasses, overrides,
  and callers, including consumers outside the requested feature.
- Review release, dependency, and interface versions separately. Confirm that
  the declared minimum core provides every interface used by the change.
- Correct architectural violations before reporting completion. If a correction
  requires departing from the approved approach, obtain approval for that
  revision first.
- Check syntax, whitespace, routes, and imports for affected modules. Use
  in-memory compilation when bytecode writes are unavailable.
- For sync changes, verify relevant success, failure, successful-empty,
  pagination, cache-preservation, and invalidation cases.
- For aggregation or date changes, verify meaningful cases: separate movie/TV
  counts, exclusion of parent rows, range boundaries, zero totals, missing
  periods, month ends, year rollover, and leap years.
- Preserve existing behavior unless the requested change calls for altering it.
- Briefly report the architectural review, verification results, and unresolved
  limitations. State which checks ran and distinguish isolated checks from
  testing in Kodi.
- Never write tests in files in the codebase.

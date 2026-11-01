# TMDbHelper Sync - SIMKL

Independent provider addon for TMDbHelper's version 3 provider interface. Requires
TMDbHelper 6.19.3 or later. No changes to TMDbHelper or other providers are needed.

## Features

- Watchlist sync: SIMKL's **Plan to Watch** items.
- Watched history, episode watched state, paused playback, next episodes and aired
  episode counts. On Hold and Dropped shows are excluded from progress lists.
- A SIMKL directory containing your custom lists and their paginated contents.
  SIMKL requires an AUTH V2 token and a PRO or VIP account for custom lists.

This version reads remote data only. It does not register collection, context
actions, scrobbling, list monitoring, ratings or statistics suppliers.

## Install and connect

1. Install the provider ZIP in Kodi and enable the addon.
2. Register an **AUTH V2** application in [SIMKL developer settings](https://simkl.com/settings/developer/).
   Choose **TV, devices & command line**. A client secret is not required.
3. Enter its public client ID in this provider's settings, then choose **Connect
   SIMKL account**. Open the displayed address on another device, enter the code
   and approve read access. Passwords are never entered in Kodi.
4. Choose this provider for Watchlist and/or History/Progress in TMDbHelper's
   provider configuration. The SIMKL directory is independent of those selections.

The addon is discovered after installation. Because it is not in TMDbHelper's
built-in provider catalogue, it cannot be offered for installation while missing;
the normal confirmation for a provider outside that catalogue still applies.

The client ID is public and may be distributed with an application. This initial
module leaves it configurable because no SIMKL app registration has been supplied.
V1 credentials will not work with AUTH V2 or custom lists.

## Authorization and storage

Uses SIMKL's RFC 8628 device grant with `media:read`. Access tokens last seven
days; refresh tokens have a sliding 180-day lifetime. Refreshes are serialized
across Kodi processes and reread the shared token before refreshing. Disconnect
revokes the grant and clears the stored authorization.

Tokens are stored in the addon's private Kodi settings, separate from the source
snapshots. Treat the provider's addon-data folder as private and exclude its
settings from shared backups. Tokens are never included in log messages or URLs.
Each new authorization gets a separate snapshot namespace, including when the
client ID or SIMKL account changes.

The device-specific API uses `/oauth2/device` and the device-code grant at
`/oauth2/token`. PKCE belongs to the separate browser authorization-code grant.

## Sync behavior and limits

Provider-owned `state.db` holds complete source snapshots. An initial sequential
pull seeds movies, TV and anime. Later reads check `/sync/activities`, request
only changed buckets using the previous snapshot's exact `all` timestamp, merge
deltas, and reconcile removals with ID-only snapshots. Failed requests never
replace snapshots or advance watermarks. Large responses split by status on
`max_items`; if an individual bucket still exceeds SIMKL's limits, sync fails
without clearing the previous data.

Episode history requests include full episode rows and watched timestamps.
For legacy watchlist entries without an added-at timestamp, the provider keeps
the local UTC first-seen time; that is not the original date added on SIMKL.
SIMKL may synthesize episode dates from a bulk-completed show's last watch time;
these are not independently recorded episode watch dates. SIMKL does not expose
ordinary replay counts in this response, so watched items use a count of one.
Explicit rewatch-session tracking is outside this version.

Titles without a resolvable TMDb identifier are skipped. Anime uses the API's
episode cross-maps rather than treating absolute numbers as season numbers;
TMDb and TVDB season numbering can still differ. Anime films are resolved through
their IMDb movie identifier because their TMDb reference may identify a parent
TV show. Unmapped anime titles or episodes are omitted rather than assigned
invented identifiers.

Custom lists cache metadata using `custom_lists.lists.all`, contents using each
list's `updated_at`, and auto-list contents for at most one day. The API's
10,000-item paging ceiling is respected. An explicit message explains premium
access errors; they are never cached as successful empty lists.

API references: [device flow](https://api.simkl.org/api-reference/oauth2-device),
[sync](https://api.simkl.org/guides/sync),
[custom lists](https://api.simkl.org/guides/custom-lists),
[anime mapping](https://api.simkl.org/guides/anime).

# lucos_locations
Location tracking service.

Uses [OwnTracks](https://owntracks.org/) to track locations from a smartphone.

## Dependencies

* docker
* docker compose

## Running

`docker compose up --build`

## Environment Variables
The following environment variables are used:

* **OT_USERNAME** - The username for logging into OwnTracks. Retained only for the device/MQTT publish path — the human map-UI login goes through aithne (below).
* **OT_PASSWORD** - The password for logging into OwnTracks. Retained only for the device/MQTT publish path.
* **RECORDER_USERNAME** - The username otrecorder uses for connecting to the message queue
* **RECORDER_PASSWORD** - The password otrecorder uses for connecting to the message queue
* **KEY_LUCOS_AITHNE** - OIDC client secret for the `lucos_locations` client registered with [lucos_aithne](https://github.com/lucas42/lucos_aithne) (linked credential)
* **AITHNE_ORIGIN** - aithne's browser-facing origin. Used for the login redirect and to validate the `iss` claim on the id_token.
* **AITHNE_JWKS_URL** - Address oauth2-proxy fetches aithne's signing keys from. Only needs overriding in development, where it differs from `AITHNE_ORIGIN` (container vs browser reachability).
* **AITHNE_TOKEN_URL** - Address oauth2-proxy calls server-to-server to redeem an auth code for tokens. Only needs overriding in development, for the same reason as `AITHNE_JWKS_URL`.
* **OAUTH2_PROXY_COOKIE_SECRET** - Random secret oauth2-proxy uses to encrypt its session cookie
* **OAUTH2_PROXY_COOKIE_SECURE** - Whether oauth2-proxy's cookie requires HTTPS. Defaults to `true`; set to `false` in development (plain `http://localhost`).

Human map-UI paths (`/map`, `/owntracks/api/`, `/owntracks/ws/`, `/owntracks/view/`, `/owntracks/static/`, `/owntracks/utils/`) require an aithne login holding the `locations:read` scope, enforced by an `oauth2-proxy` sidecar. The device publish path (`/owntracks/pub`) and MQTT (`:8883`) stay on `OT_USERNAME`/`OT_PASSWORD` credential auth, since a phone can't do an interactive OIDC login.

Environment Variables are stored securely in [lucos_creds](https://github.com/lucas42/lucos_creds)
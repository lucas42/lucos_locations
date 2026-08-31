import config from "@/config";
import { log, logLevels } from "@/logging";
import { getApiUrl, getLocationHistoryCount } from "@/util";
import { authState, markSessionExpired } from "@/authState";

const RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;

/**
 * Fetch an API resource.
 *
 * A 401/403 means oauth2-proxy has rejected the request because the
 * session has expired — its body is an HTML sign-in page, not JSON, so we
 * flag it via authState and return null instead of a Response, letting
 * callers skip response.json() rather than throw on that HTML body.
 * See lucas42/lucos_locations#101.
 *
 * @param {String} path API resource path
 * @param {Object} [params] Query parameters
 * @param {Object} [fetchOptions]
 *   fetch() options (merged with config.api.fetchOptions)
 * @returns {Promise<Response|null>} Response returned by the fetch call, or
 *   null if the request failed (network error, or session expired)
 */
const fetchApi = (path, params = {}, fetchOptions = {}) => {
  const url = getApiUrl(path);
  Object.keys(params).forEach((key) => url.searchParams.set(key, params[key]));
  log("HTTP", `GET ${url.href}`);
  return fetch(url.href, {
    ...fetchOptions,
    ...config.api.fetchOptions,
  })
    .then((response) => {
      if (response.status === 401 || response.status === 403) {
        log("HTTP", `GET ${url.href} - Session expired (${response.status})`, logLevels.WARNING);
        markSessionExpired();
        return null;
      }
      return response;
    })
    .catch((error) => {
      if (error.name === "AbortError") {
        log("HTTP", `GET ${url.href} - Request was aborted`, logLevels.WARNING);
      } else {
        log("HTTP", error, logLevels.ERROR);
      }
      return null;
    });
};

/**
 * Get the recorder's version.
 *
 * @returns {Promise<String|null>} Version, or null if the request failed
 */
export const getVersion = async () => {
  const response = await fetchApi("/api/0/version");
  if (!response) return null;
  const json = await response.json();
  const version = json.version;
  log("API", () => `[getVersion] ${version}`);
  return version;
};

/**
 * Get all users.
 *
 * @returns {Promise<User[]>} Array of usernames
 */
export const getUsers = async () => {
  const response = await fetchApi("/api/0/list");
  if (!response) return [];
  const json = await response.json();
  const users = json.results;
  log("API", () => `[getUsers] Fetched ${users.length} users`);
  return users;
};

/**
 * Get all devices for the provided users.
 *
 * @param {User[]} users Array of usernames
 * @returns {Promise<{User: Device[]}>}
 *   Object mapping each username to an array of device names
 */
export const getDevices = async (users) => {
  const devices = {};
  await Promise.all(
    users.map(async (user) => {
      const response = await fetchApi(`/api/0/list`, { user });
      if (!response) {
        devices[user] = [];
        return;
      }
      const json = await response.json();
      const userDevices = json.results;
      devices[user] = userDevices;
    })
  );
  log("API", () => {
    const devicesCount = Object.keys(devices)
      .map((user) => devices[user].length)
      .reduce((a, b) => a + b, 0);
    return (
      `[getDevices] Fetched ${devicesCount} ` +
      `devices for ${users.length} users`
    );
  });
  return devices;
};

/**
 * Get last locations for a specific or all user/device.
 *
 * @param {User} [user] Get last locations of all devices from this user
 * @param {Device} [device] Get last location of specific device
 * @returns {Promise<OTLocation[]>} Array of last location objects
 */
export const getLastLocations = async (user, device) => {
  const params = {};
  if (user) {
    params["user"] = user;
    if (device) {
      params["device"] = device;
    }
  }
  const response = await fetchApi("/api/0/last", params);
  if (!response) return [];
  const json = await response.json();
  const lastLocations = json;
  log(
    "API",
    () => `[getLastLocations] Fetched ${lastLocations.length} last locations`
  );
  return lastLocations;
};

/**
 * Get the location history of a specific user/device.
 *
 * @param {User} user Username
 * @param {Device} device Device name
 * @param {String} start Start date and time in UTC
 * @param {String} end End date and time in UTC
 * @param {Object} [fetchOptions] fetch() options
 * @returns {Promise<OTLocation[]>} Array of location history objects
 */
export const getUserDeviceLocationHistory = async (
  user,
  device,
  start,
  end,
  fetchOptions
) => {
  const response = await fetchApi(
    "/api/0/locations",
    {
      from: start,
      to: end,
      user,
      device,
      format: "json",
    },
    fetchOptions
  );
  if (!response) return [];
  const json = await response.json();
  // We need to manually sort by timestamp, otherwise the line segments may be
  // drawn in the wrong order. The recorder API simply returns entries in the
  // same order in which they are in each *.rec file.
  // See https://github.com/owntracks/frontend/issues/67.
  const userDeviceLocationHistory = json.data.sort((a, b) => a.tst - b.tst);
  log(
    "API",
    () =>
      `[getUserDeviceLocationHistory] Fetched ` +
      `${userDeviceLocationHistory.length} locations for ` +
      `${user}/${device} from ${start} - ${end}`
  );
  return userDeviceLocationHistory;
};

/**
 * Get the location history of multiple devices.
 *
 * @param {{User: Device[]}} devices
 *   Devices of which the history should be fetched
 * @param {String} start Start date and time in UTC
 * @param {String} end End date and time in UTC
 * @param {Object} [fetchOptions] fetch() options
 * @returns {Promise<LocationHistory>} Location history
 */
export const getLocationHistory = async (devices, start, end, fetchOptions) => {
  const locationHistory = {};
  await Promise.all(
    Object.keys(devices).map(async (user) => {
      locationHistory[user] = {};
      await Promise.all(
        devices[user].map(async (device) => {
          locationHistory[user][device] = await getUserDeviceLocationHistory(
            user,
            device,
            start,
            end,
            fetchOptions
          );
        })
      );
    })
  );
  log("API", () => {
    const locationHistoryCount = getLocationHistoryCount(locationHistory);
    return (
      "[getLocationHistory] Fetched " +
      `${locationHistoryCount} locations in total`
    );
  });
  return locationHistory;
};

/**
 * Connect to the WebSocket API, reconnect when necessary and handle received
 * messages.
 *
 * A WS upgrade rejected for an expired session just closes abnormally, with
 * no way to distinguish it from a transient network blip via the close
 * event — so before each reconnect we probe with a plain fetchApi() call
 * instead, which reliably surfaces a 401/403. See lucas42/lucos_locations#101.
 *
 * @param {WebSocketLocationCallback} [callback] Callback for location messages
 * @param {Number} [reconnectDelay] Delay before the next reconnect attempt,
 *   doubling (up to MAX_RECONNECT_DELAY_MS) each time one is needed
 */
export const connectWebsocket = async (callback, reconnectDelay = RECONNECT_DELAY_MS) => {
  let url = getApiUrl("/ws/last");
  url.protocol = url.protocol.replace("http", "ws");
  url = url.href;
  const ws = new WebSocket(url);
  log("WS", `Connecting to ${url}`);
  ws.onopen = () => {
    log("WS", "Connected");
    // Reset backoff once a connection actually succeeds, so a brief blip
    // long after start-up doesn't inherit a delay grown from earlier retries.
    reconnectDelay = RECONNECT_DELAY_MS;
    ws.send("LAST");
  };
  ws.onclose = (event) => {
    if (authState.expired) {
      log("WS", "Session expired - not reconnecting.", logLevels.WARNING);
      return;
    }
    log(
      "WS",
      `Disconnected unexpectedly (reason: ${
        event.reason || "unknown"
      }). Checking session before reconnecting in ${reconnectDelay}ms.`,
      logLevels.WARNING
    );
    setTimeout(async () => {
      // A plain HTTP request reliably surfaces a 401/403, unlike the WS
      // close event above - if the session has expired, this also flags
      // authState so the banner shows instead of us reconnecting forever.
      await getVersion();
      if (authState.expired) return;
      connectWebsocket(callback, Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY_MS));
    }, reconnectDelay);
  };
  ws.onmessage = async (msg) => {
    if (msg.data) {
      try {
        const data = JSON.parse(msg.data);
        if (data._type === "location") {
          log("WS", "Location update received");
          callback && (await callback());
        }
      } catch (err) {
        if (msg.data !== "LAST") {
          log("WS", err, logLevels.ERROR);
        }
      }
    } else {
      log("WS", "Ping");
    }
  };
};

import Vue from "vue";

/**
 * Reactive singleton tracking whether the current session has expired (an
 * API/WS call got a 401/403 from oauth2-proxy). Kept outside Vuex so api.js
 * can flag it without a circular import between api.js and the store.
 *
 * See lucas42/lucos_locations#101.
 */
export const authState = Vue.observable({ expired: false });

export const markSessionExpired = () => {
  authState.expired = true;
};

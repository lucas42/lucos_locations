<template>
  <div v-if="authState.expired" class="session-expired-banner" role="alert">
    {{ $t("Your session has expired.") }}
    <a href="/oauth2/start">{{ $t("Sign in again") }}</a>
  </div>
</template>

<script>
import { authState } from "@/authState";

// Full-navigation link to oauth2-proxy's sign-in path, not a click handler —
// this is the same round trip through aithne that #99 already set up for
// /map, so it correctly returns with a fresh cookie.
export default {
  data() {
    return { authState };
  },
};
</script>

<style scoped>
.session-expired-banner {
  /* Normal flow, not position:fixed - #app is a flex column (see
     _base.scss), so this pushes the header down rather than overlapping
     its controls. */
  flex-shrink: 0;
  padding: 0.75em 1em;
  background: #b91c1c;
  color: #fff;
  text-align: center;
  font-size: 0.95em;
}

.session-expired-banner a {
  color: #fff;
  font-weight: bold;
  text-decoration: underline;
  margin-left: 0.5em;
}
</style>

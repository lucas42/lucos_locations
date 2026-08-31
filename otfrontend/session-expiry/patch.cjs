// Wires SessionExpiredBanner into App.vue and adds its copy to the locale
// files we can vouch for the translation of (en-GB, this deployment's
// locale, and en-US, vue-i18n's fallbackLocale). Other locales fall back to
// the en-US text automatically (formatFallbackMessages: true in i18n.js)
// rather than getting an unverified translation from us.
// See lucas42/lucos_locations#101.
const fs = require("fs");

const appVuePath = "src/App.vue";
let appVue = fs.readFileSync(appVuePath, "utf8");

// Placed before AppHeader so it's the first thing in DOM/tab order while
// shown - a keyboard user shouldn't have to tab through the whole header
// (whose controls are acting on stale data) before reaching "Sign in again".
appVue = appVue.replace(
  '<div id="app">',
  '<div id="app">\n    <SessionExpiredBanner />'
);
appVue = appVue.replace(
  'import LoadingModal from "@/components/modals/LoadingModal.vue";',
  'import LoadingModal from "@/components/modals/LoadingModal.vue";\nimport SessionExpiredBanner from "@/components/SessionExpiredBanner.vue";'
);
appVue = appVue.replace(
  "components: { AppHeader, InformationModal, LoadingModal },",
  "components: { AppHeader, InformationModal, LoadingModal, SessionExpiredBanner },"
);
fs.writeFileSync(appVuePath, appVue);

for (const localePath of ["src/locales/en-GB.json", "src/locales/en-US.json"]) {
  const messages = JSON.parse(fs.readFileSync(localePath, "utf8"));
  messages["Your session has expired."] = "Your session has expired.";
  messages["Sign in again"] = "Sign in again";
  fs.writeFileSync(localePath, JSON.stringify(messages, null, 2) + "\n");
}

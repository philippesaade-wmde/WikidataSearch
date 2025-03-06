import './assets/tailwind.css'

import { createApp } from 'vue'
import { createI18n } from 'vue-i18n'
import App from './App.vue'
import router from './router'

const i18n = createI18n({
  locale: window.navigator.language,
  fallbackLocale: 'de',
  messages: {
    en: {
      'chat-prompt': 'Message WikidataChat...',
      'no-response-message':
        'Sorry, but no valid response was returned for your question. Please try rephrasing it.',
      source: 'Source',
      'enter-api-secret': "Enter your API secret"
    },
    de: {
      'chat-prompt': 'Schreib WikidataChat...',
      'no-response-message':
        'Leider wurde auf Ihre Frage keine gültige Antwort zurückgegeben. Bitte versuchen Sie es umzuformulieren.',
      source: 'Quelle',
      'enter-api-secret': "API Passwort eingeben"
    }
  }
})

const app = createApp(App)

app.use(i18n)
app.use(router)

app.mount('#app')

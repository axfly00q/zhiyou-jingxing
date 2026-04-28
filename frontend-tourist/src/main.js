import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import Home from './views/Home.vue'
import Preference from './views/Preference.vue'
import Chat from './views/Chat.vue'
import './styles.css'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: Home },
    { path: '/preference', component: Preference },
    { path: '/chat', component: Chat }
  ]
})

createApp(App).use(createPinia()).use(router).mount('#app')

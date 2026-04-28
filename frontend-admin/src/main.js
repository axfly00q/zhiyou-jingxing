import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import Login from './views/Login.vue'
import Layout from './views/Layout.vue'
import Avatars from './views/Avatars.vue'
import Knowledge from './views/Knowledge.vue'
import Suggestions from './views/Suggestions.vue'
import './styles.css'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/login', component: Login },
    { path: '/', component: Layout, children: [
      { path: '', redirect: '/avatars' },
      { path: 'avatars', component: Avatars },
      { path: 'knowledge', component: Knowledge },
      { path: 'suggestions', component: Suggestions }
    ]}
  ]
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (!token && to.path !== '/login') return '/login'
})

createApp(App).use(router).mount('#app')

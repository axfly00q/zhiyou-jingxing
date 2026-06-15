import { createRouter, createWebHashHistory } from 'vue-router'
import Layout from '../views/admin/Layout.vue'

// 游客端
import TouristHome from '../views/tourist/Home.vue'
import TouristPreference from '../views/tourist/Preference.vue'
import TouristChat from '../views/tourist/Chat.vue'

// 景区管理端
import AdminAvatars from '../views/admin/Avatars.vue'
import AdminKnowledge from '../views/admin/Knowledge.vue'
import AdminSuggestions from '../views/admin/Suggestions.vue'
import AdminAnalytics from '../views/admin/Analytics.vue'

// 统一登录与大屏
import Login from '../views/Login.vue' // 全新设计的统一登录页
import Dashboard from '../views/dashboard/Dashboard.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/login', component: Login },
    // 游客端路由
    { path: '/tourist', component: TouristHome },
    { path: '/tourist/preference', component: TouristPreference },
    { path: '/tourist/chat', component: TouristChat },
    // 大屏路由
    { path: '/dashboard', component: Dashboard },
    // 景区管理端路由
    { 
      path: '/admin', 
      component: Layout, 
      children: [
        { path: '', redirect: '/admin/avatars' },
        { path: 'avatars', component: AdminAvatars },
        { path: 'knowledge', component: AdminKnowledge },
        { path: 'suggestions', component: AdminSuggestions },
        { path: 'analytics', component: AdminAnalytics }
      ]
    },
    // 默认重定向到登录页
    { path: '/:pathMatch(.*)*', redirect: '/login' }
  ]
})

// 简单的路由守卫（可根据后续需求增强）
router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  const role = localStorage.getItem('role') // 'tourist' 或 'admin'
  if (!token && to.path !== '/login') {
    return '/login'
  }
})

export default router

<template>
  <div class="overlay">
    <div class="card">
      <div class="badge-icon">🏆</div>
      <h2 class="badge-name">{{ badge?.badge_name || '成就解锁' }}</h2>
      <p class="badge-type">{{ typeLabel }}</p>
      <p class="badge-tip">恭喜您解锁了新成就！</p>
      <button class="close-btn" @click="$emit('close')">收好了</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  badge: Object,
})
defineEmits(['close'])

const TYPE_LABELS = {
  route_complete: '全程打卡达人',
  quiz_master: '知识问答达人',
}
const typeLabel = computed(() => TYPE_LABELS[props.badge?.badge_type] || '成就')
</script>

<style scoped>
.overlay {
  position: fixed; inset: 0; z-index: 1100;
  background: rgba(0,0,0,0.75);
  display: flex; align-items: center; justify-content: center;
}
.card {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border: 2px solid rgba(255,200,50,0.6);
  border-radius: 24px;
  padding: 40px 32px;
  max-width: 340px; width: 90%;
  display: flex; flex-direction: column; align-items: center;
  gap: 12px;
  animation: popIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  box-shadow: 0 0 40px rgba(255,200,50,0.3);
}
@keyframes popIn {
  0% { transform: scale(0.5); opacity: 0; }
  60% { transform: scale(1.1); }
  100% { transform: scale(1); opacity: 1; }
}
.badge-icon {
  font-size: 80px;
  filter: drop-shadow(0 0 20px rgba(255,200,50,0.8));
  animation: glow 1.5s ease-in-out infinite alternate;
}
@keyframes glow {
  from { filter: drop-shadow(0 0 10px rgba(255,200,50,0.6)); }
  to   { filter: drop-shadow(0 0 30px rgba(255,220,80,1)); }
}
.badge-name {
  font-size: 22px; font-weight: 800;
  color: #ffd700;
  text-align: center;
  text-shadow: 0 0 10px rgba(255,215,0,0.5);
  margin: 0;
}
.badge-type { font-size: 14px; color: #aaa; margin: 0; }
.badge-tip { font-size: 15px; color: #ccc; margin: 0; text-align: center; }
.close-btn {
  margin-top: 12px;
  padding: 12px 40px;
  background: linear-gradient(90deg, #f7b731, #ffd700);
  color: #1a1a2e;
  border: none; border-radius: 999px;
  font-size: 17px; font-weight: 700;
  cursor: pointer;
  transition: transform 0.1s;
}
.close-btn:active { transform: scale(0.97); }
</style>

<template>
  <div class="overlay" @click.self="$emit('done')">
    <div class="card">
      <h2 class="title">游览结束，您的感受</h2>
      <p class="sub">{{ parkDisplayName }} · 共游 {{ elapsedMinutes }} 分钟</p>

      <!-- 星级 -->
      <div class="stars">
        <span
          v-for="n in 5" :key="n"
          class="star"
          :class="{ active: n <= rating }"
          @click="rating = n"
        >★</span>
      </div>
      <p class="star-label">{{ ratingLabel }}</p>

      <!-- 标签 chips -->
      <div class="tags">
        <button
          v-for="tag in allTags" :key="tag"
          class="tag-chip"
          :class="{ selected: selectedTags.includes(tag) }"
          @click="toggleTag(tag)"
        >{{ tag }}</button>
      </div>

      <!-- 文字评价 -->
      <textarea
        v-model="comment"
        placeholder="写下您的感受（可选）"
        class="comment-box"
        rows="3"
        maxlength="200"
      />

      <button class="submit-btn" :disabled="submitting" @click="submit">
        {{ submitting ? '提交中…' : '提交评价' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { submitReview } from '../api.js'

const props = defineProps({
  sessionId: String,
  parkCode: String,
  visitedSpots: Array,
  elapsedMinutes: { type: Number, default: 0 },
})
const emit = defineEmits(['done'])

const PARK_NAMES = { zhuozhengyuan: '拙政园', liuyuan: '留园' }
const parkDisplayName = computed(() => PARK_NAMES[props.parkCode] || props.parkCode || '园林')

const rating = ref(5)
const ratingLabels = ['', '很差', '较差', '一般', '还不错', '非常满意']
const ratingLabel = computed(() => ratingLabels[rating.value] || '')
const allTags = ['讲解很棒', '路线合理', '回答准确', '互动体验好', '路线不合理', '等待太久', '内容单调']
const selectedTags = ref([])
const comment = ref('')
const submitting = ref(false)

function toggleTag(tag) {
  const idx = selectedTags.value.indexOf(tag)
  if (idx === -1) selectedTags.value.push(tag)
  else selectedTags.value.splice(idx, 1)
}

async function submit() {
  submitting.value = true
  try {
    await submitReview({
      session_id: props.sessionId,
      park_code: props.parkCode,
      rating: rating.value,
      tags: selectedTags.value,
      comment: comment.value.trim() || null,
    })
  } catch (e) {
    console.warn('submitReview failed', e)
  } finally {
    submitting.value = false
    emit('done')
  }
}
</script>

<style scoped>
.overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.65);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.card {
  background: #fff;
  border-radius: 20px;
  padding: 28px 24px;
  width: 100%; max-width: 480px;
  display: flex; flex-direction: column; align-items: center;
  gap: 14px;
  animation: slideUp 0.3s ease;
}
@keyframes slideUp {
  from { transform: translateY(40px); opacity: 0; }
  to   { transform: translateY(0);    opacity: 1; }
}
.title { font-size: 20px; font-weight: 700; color: #222; margin: 0; }
.sub { font-size: 14px; color: #888; margin: 0; }
.stars { display: flex; gap: 10px; }
.star { font-size: 38px; color: #ddd; cursor: pointer; transition: color 0.15s, transform 0.1s; }
.star.active { color: #ffc107; }
.star:hover { transform: scale(1.15); }
.star-label { font-size: 15px; color: #555; height: 20px; margin: 0; }
.tags { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; }
.tag-chip {
  padding: 7px 14px;
  border-radius: 999px;
  border: 1px solid #d0d7e3;
  background: #f5f7fb;
  color: #555;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
}
.tag-chip.selected { background: #2c7be5; color: #fff; border-color: #2c7be5; }
.comment-box {
  width: 100%; box-sizing: border-box;
  border: 1px solid #ddd; border-radius: 10px;
  padding: 10px 12px; font-size: 15px;
  font-family: inherit; outline: none; resize: none;
}
.comment-box:focus { border-color: #2c7be5; }
.submit-btn {
  width: 100%;
  padding: 14px;
  background: #2c7be5; color: #fff;
  border: none; border-radius: 12px;
  font-size: 17px; font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.submit-btn:disabled { background: #a8c0e8; cursor: not-allowed; }
.submit-btn:not(:disabled):active { background: #1a63c5; }
</style>

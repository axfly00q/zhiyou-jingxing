<template>
  <div class="overlay">
    <div class="card">
      <!-- 结果屏 -->
      <template v-if="finished">
        <div class="result-icon">{{ score >= 4 ? '🎉' : score >= 2 ? '👍' : '💡' }}</div>
        <h2 class="result-title">答题完成！</h2>
        <p class="result-score">{{ score }} / {{ questions.length }} 答对</p>
        <p class="result-tip">{{ resultTip }}</p>
        <div class="result-btns">
          <button class="btn primary" @click="emit('complete', score)">继续</button>
        </div>
      </template>

      <!-- 答题屏 -->
      <template v-else>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: (currentIdx / questions.length * 100) + '%' }" />
        </div>
        <p class="progress-text">{{ currentIdx + 1 }} / {{ questions.length }}</p>

        <h3 class="question">{{ current.q }}</h3>

        <div class="options">
          <button
            v-for="(opt, i) in current.options" :key="i"
            class="option"
            :class="answered ? (i === current.answer ? 'correct' : (i === chosen ? 'wrong' : '')) : ''"
            :disabled="answered"
            @click="choose(i)"
          >{{ opt }}</button>
        </div>

        <div v-if="answered && current.fact" class="fact-box">
          <span class="fact-icon">📚</span> {{ current.fact }}
        </div>

        <div class="action-row">
          <button v-if="!answered" class="btn ghost" @click="skipQuestion">跳过</button>
          <button v-if="answered" class="btn primary" @click="next">{{ isLast ? '查看结果' : '下一题' }}</button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { unlockBadge } from '../api.js'

const props = defineProps({
  spots: { type: Array, default: () => [] },
  sessionId: String,
  parkCode: String,
})
const emit = defineEmits(['complete', 'skip'])

// 从所有景点 quiz 里随机抽 5 题
function pickQuestions(spots) {
  const all = []
  for (const spot of spots) {
    if (spot.quiz && spot.quiz.length) {
      for (const q of spot.quiz) {
        all.push({ ...q, spotName: spot.name })
      }
    }
  }
  // shuffle
  for (let i = all.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [all[i], all[j]] = [all[j], all[i]]
  }
  return all.slice(0, 5)
}

const questions = ref([])
const currentIdx = ref(0)
const answered = ref(false)
const chosen = ref(-1)
const score = ref(0)
const finished = ref(false)

onMounted(() => {
  questions.value = pickQuestions(props.spots)
  if (questions.value.length === 0) {
    emit('skip')
  }
})

const current = computed(() => questions.value[currentIdx.value] || {})
const isLast = computed(() => currentIdx.value === questions.value.length - 1)

const resultTip = computed(() => {
  if (score.value >= 4) return '太棒了！您是真正的园林知识达人！'
  if (score.value >= 2) return '不错！继续探索更多园林知识吧。'
  return '没关系，游览过程中慢慢体会，知识会越来越多的！'
})

function choose(i) {
  if (answered.value) return
  chosen.value = i
  answered.value = true
  if (i === current.value.answer) score.value++
}

function skipQuestion() {
  answered.value = false
  chosen.value = -1
  next()
}

async function next() {
  if (isLast.value) {
    finished.value = true
    // 4/5 以上解锁 quiz_master 徽章
    if (score.value >= 4 && props.sessionId) {
      try {
        await unlockBadge(props.sessionId, props.parkCode, 'quiz_master')
      } catch (e) {
        console.warn('unlock quiz badge failed', e)
      }
    }
  } else {
    currentIdx.value++
    answered.value = false
    chosen.value = -1
  }
}
</script>

<style scoped>
.overlay {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(0,0,0,0.7);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.card {
  background: #fff;
  border-radius: 20px;
  padding: 24px 20px;
  width: 100%; max-width: 500px;
  display: flex; flex-direction: column; gap: 14px;
  animation: slideUp 0.3s ease;
  max-height: 90vh; overflow-y: auto;
}
@keyframes slideUp {
  from { transform: translateY(40px); opacity: 0; }
  to   { transform: translateY(0);    opacity: 1; }
}
.progress-bar {
  height: 6px; background: #eee; border-radius: 3px; overflow: hidden;
}
.progress-fill { height: 100%; background: #2c7be5; transition: width 0.3s; }
.progress-text { font-size: 13px; color: #999; text-align: right; margin: 0; }
.question { font-size: 18px; font-weight: 600; color: #222; line-height: 1.5; margin: 0; }
.options { display: flex; flex-direction: column; gap: 10px; }
.option {
  padding: 13px 16px;
  border: 1.5px solid #ddd;
  border-radius: 12px;
  background: #fff;
  font-size: 16px; text-align: left;
  cursor: pointer; transition: all 0.15s;
}
.option:not(:disabled):hover { border-color: #2c7be5; background: #f0f7ff; }
.option.correct { background: #e8f8f0; border-color: #27ae60; color: #27ae60; }
.option.wrong   { background: #fef0f0; border-color: #e74c3c; color: #e74c3c; }
.option:disabled { cursor: default; }
.fact-box {
  background: #f0f7ff;
  border-left: 3px solid #2c7be5;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px; color: #444; line-height: 1.55;
}
.fact-icon { margin-right: 4px; }
.action-row { display: flex; justify-content: flex-end; gap: 10px; }
.btn {
  padding: 11px 24px; border-radius: 10px; border: none;
  font-size: 16px; font-weight: 600; cursor: pointer;
}
.btn.primary { background: #2c7be5; color: #fff; }
.btn.ghost { background: #fff; color: #999; border: 1px solid #ddd; }
/* 结果屏 */
.result-icon { font-size: 72px; text-align: center; }
.result-title { font-size: 22px; font-weight: 700; text-align: center; margin: 0; color: #222; }
.result-score { font-size: 36px; font-weight: 800; text-align: center; color: #2c7be5; margin: 0; }
.result-tip { font-size: 15px; color: #666; text-align: center; margin: 0; }
.result-btns { display: flex; justify-content: center; }
.result-btns .btn { padding: 13px 50px; }
</style>

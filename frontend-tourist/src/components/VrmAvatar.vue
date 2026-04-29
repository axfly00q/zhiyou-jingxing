<template>
  <div class="vrm-stage" ref="root">
    <canvas ref="canvas"></canvas>
    <div v-if="status !== 'ready'" class="vrm-overlay">
      <div class="circle">{{ statusLabel }}</div>
      <p v-if="status === 'error'">{{ errorMsg }}</p>
      <p v-else-if="status === 'empty'">请在管理后台上传 VRM 模型</p>
      <p v-else>正在加载数字人模型…</p>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import {
  VRMLoaderPlugin,
  VRMUtils,
} from '@pixiv/three-vrm'
import {
  VRMAnimationLoaderPlugin,
  createVRMAnimationClip,
} from '@pixiv/three-vrm-animation'

import { LipSyncAnalyzer } from '../lib/lipSync.js'
import {
  applyEmotion,
  applyVowels,
  stepEmotion,
  MotionController,
} from '../lib/expressionMap.js'

const props = defineProps({
  modelUrl: { type: String, default: '' },
  audioUrl: { type: String, default: '' },
  emotion: { type: String, default: 'neutral' },
  motion: { type: String, default: 'idle' },
  // 名称 → vrma url 列表，例如 { idle: '/static/avatars/x/motions/idle.vrma' }
  motions: { type: Object, default: () => ({}) },
})

const root = ref(null)
const canvas = ref(null)
const status = ref('loading') // loading | ready | empty | error
const errorMsg = ref('')
const statusLabel = ref('数字人')

let renderer = null
let scene = null
let camera = null
let clock = null
let rafId = 0
let resizeObs = null

let currentVrm = null
let mixer = null
let motionCtl = null
const clipMap = {}

const lipSync = new LipSyncAnalyzer()
let audioEl = null

// ---------- three.js 场景 ----------
function initScene() {
  const c = canvas.value
  const w = root.value.clientWidth || 320
  const h = root.value.clientHeight || 480

  renderer = new THREE.WebGLRenderer({ canvas: c, antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.setSize(w, h, false)
  renderer.outputColorSpace = THREE.SRGBColorSpace

  scene = new THREE.Scene()
  scene.background = null

  camera = new THREE.PerspectiveCamera(24, w / h, 0.1, 20)
  // 竖屏构图：相机略后退避免「截脖子」，初始 lookAt 胸口偏上
  camera.position.set(0, 1.35, 1.6)
  camera.lookAt(0, 1.35, 0)

  const dir = new THREE.DirectionalLight(0xffffff, 1.2)
  dir.position.set(1, 2, 1)
  scene.add(dir)
  scene.add(new THREE.AmbientLight(0xffffff, 0.55))

  clock = new THREE.Clock()

  resizeObs = new ResizeObserver(() => onResize())
  resizeObs.observe(root.value)
}

function onResize() {
  if (!renderer || !root.value) return
  const w = root.value.clientWidth
  const h = root.value.clientHeight
  if (w === 0 || h === 0) return
  renderer.setSize(w, h, false)
  const aspect = w / h
  camera.aspect = aspect
  // 窄竖屏（aspect<0.8）再后退一点，保证半身可见
  const z = aspect < 0.8 ? 1.6 + (0.8 - aspect) * 1.2 : 1.6
  camera.position.z = z
  camera.updateProjectionMatrix()
}

function disposeVrm() {
  if (!currentVrm) return
  try { VRMUtils.deepDispose(currentVrm.scene) } catch (_) {}
  scene.remove(currentVrm.scene)
  currentVrm = null
  mixer = null
  motionCtl = null
  for (const k of Object.keys(clipMap)) delete clipMap[k]
}

// ---------- 加载 VRM ----------
async function loadVrm(url) {
  if (!url) {
    status.value = 'empty'
    statusLabel.value = '未配置'
    disposeVrm()
    return
  }
  status.value = 'loading'
  statusLabel.value = '加载中'
  disposeVrm()
  try {
    const loader = new GLTFLoader()
    loader.register((parser) => new VRMLoaderPlugin(parser))
    loader.register((parser) => new VRMAnimationLoaderPlugin(parser))
    const gltf = await loader.loadAsync(url)
    const vrm = gltf.userData.vrm
    if (!vrm) throw new Error('not a valid VRM file')
    VRMUtils.removeUnnecessaryVertices(gltf.scene)
    VRMUtils.combineSkeletons(gltf.scene)
    // VRM 1.0 默认面向 +Z（朝相机）；VRM 0.x 默认面向 -Z（背朝相机），需要转 180°
    if (vrm.meta?.metaVersion === '0') {
      vrm.scene.rotation.y = Math.PI
    } else {
      vrm.scene.rotation.y = 0
    }
    scene.add(vrm.scene)
    currentVrm = vrm
    mixer = new THREE.AnimationMixer(vrm.scene)
    motionCtl = new MotionController(mixer, {})
    status.value = 'ready'
    statusLabel.value = ''

    // 异步加载预制动作（失败不阻塞主流程）
    await loadMotions(props.motions)
    // 启动默认动作
    motionCtl.play(props.motion || 'idle')
    // 应用初始情绪
    applyEmotion(vrm, props.emotion)
  } catch (e) {
    console.error('[VrmAvatar] load failed', e)
    status.value = 'error'
    statusLabel.value = '!'
    errorMsg.value = e.message || String(e)
  }
}

async function loadMotions(motionsMap) {
  if (!motionsMap) return
  const loader = new GLTFLoader()
  loader.register((parser) => new VRMAnimationLoaderPlugin(parser))
  for (const [name, url] of Object.entries(motionsMap)) {
    if (!url) continue
    try {
      const gltf = await loader.loadAsync(url)
      const animations = gltf.userData.vrmAnimations || []
      if (!animations.length || !currentVrm) continue
      const clip = createVRMAnimationClip(animations[0], currentVrm)
      if (clip) clipMap[name] = clip
    } catch (e) {
      console.warn(`[VrmAvatar] motion '${name}' load failed:`, e)
    }
  }
  if (motionCtl) motionCtl.setClips(clipMap)
}

// ---------- 渲染循环 ----------
function tick() {
  rafId = requestAnimationFrame(tick)
  const dt = clock ? clock.getDelta() : 0
  if (mixer) mixer.update(dt)
  if (currentVrm) {
    // 嘴型 + 表情
    if (audioEl && !audioEl.paused) {
      applyVowels(currentVrm, lipSync.read())
    } else {
      applyVowels(currentVrm, null)
    }
    stepEmotion(currentVrm)
    currentVrm.update(dt)
  }
  if (renderer && scene && camera) renderer.render(scene, camera)
}

// ---------- 音频驱动 ----------
function attachAudio(url) {
  // 销毁旧元素
  if (audioEl) {
    try { audioEl.pause() } catch (_) {}
    lipSync.detach()
    audioEl = null
  }
  if (!url) return
  audioEl = new Audio()
  audioEl.crossOrigin = 'anonymous'
  audioEl.src = url
  audioEl.addEventListener('canplay', async () => {
    lipSync.attach(audioEl)
    await lipSync.resume()
    try { await audioEl.play() } catch (e) { console.warn('audio play blocked:', e) }
  }, { once: true })
  audioEl.addEventListener('ended', () => {
    applyVowels(currentVrm, null)
  })
}

defineExpose({
  /** 外部可以主动停止当前播报。 */
  stop() {
    if (audioEl) { try { audioEl.pause() } catch (_) {} }
    applyVowels(currentVrm, null)
  },
})

// ---------- 生命周期 ----------
onMounted(() => {
  initScene()
  tick()
  if (props.modelUrl) loadVrm(props.modelUrl)
  if (props.audioUrl) attachAudio(props.audioUrl)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(rafId)
  if (resizeObs) try { resizeObs.disconnect() } catch (_) {}
  if (audioEl) { try { audioEl.pause() } catch (_) {} }
  lipSync.detach()
  disposeVrm()
  if (renderer) try { renderer.dispose() } catch (_) {}
  renderer = null
  scene = null
  camera = null
})

watch(() => props.modelUrl, (url) => loadVrm(url))
watch(() => props.audioUrl, (url) => attachAudio(url))
watch(() => props.emotion, (e) => { if (currentVrm) applyEmotion(currentVrm, e) })
watch(() => props.motion, (m) => { if (motionCtl) motionCtl.play(m || 'idle') })
watch(() => props.motions, async (m) => {
  if (!currentVrm) return
  await loadMotions(m)
  if (motionCtl) motionCtl.play(props.motion || 'idle')
}, { deep: true })
</script>

<style scoped>
.vrm-stage {
  position: relative;
  width: 100%;
  height: 100%;
  background: linear-gradient(180deg, #1f2233 0%, #2a2e44 100%);
  overflow: hidden;
}
.vrm-stage canvas { display: block; width: 100%; height: 100%; }
.vrm-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #cdd2e4;
  pointer-events: none;
  font-size: 13px;
  text-align: center;
}
.circle {
  width: 110px; height: 110px; border-radius: 50%;
  background: linear-gradient(135deg, #2c7be5, #6f42c1);
  color: #fff; display: flex; align-items: center; justify-content: center;
  margin-bottom: 12px; font-size: 16px;
}
</style>

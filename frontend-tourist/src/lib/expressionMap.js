/**
 * 表情/动作映射工具：
 *  - applyEmotion(vrm, emotion)：把后端语义情绪映射到 VRM 标准 BlendShape，并平滑过渡
 *  - applyVowels(vrm, weights)：把 lipSync 输出的 5 元音权重写到嘴型 BlendShape
 *  - playMotion(mixer, clipMap, name, options)：动作 crossFade 切换
 *
 * VRM 0 与 VRM 1 的 expression 名称略有不同；这里使用 ExpressionManager 的
 * 标准短名（happy/sad/angry/surprised/aa/ih/ou/ee/oh），three-vrm 会自动适配。
 */

import * as THREE from 'three'

const EMOTION_TO_VRM = {
  neutral: { happy: 0, sad: 0, angry: 0, surprised: 0 },
  joy: { happy: 1, sad: 0, angry: 0, surprised: 0 },
  sorrow: { happy: 0, sad: 1, angry: 0, surprised: 0 },
  angry: { happy: 0, sad: 0, angry: 1, surprised: 0 },
  surprised: { happy: 0, sad: 0, angry: 0, surprised: 1 },
}

const EMO_LERP = 0.12 // 表情过渡速度（每帧逼近目标的比例）

/** 内部状态：每个 vrm 对应一份当前表情值，用于平滑插值。 */
const _state = new WeakMap()

function _ensureState(vrm) {
  let s = _state.get(vrm)
  if (!s) {
    s = {
      current: { happy: 0, sad: 0, angry: 0, surprised: 0 },
      target: { happy: 0, sad: 0, angry: 0, surprised: 0 },
    }
    _state.set(vrm, s)
  }
  return s
}

/** 设定情绪目标。每帧 update() 时调 stepEmotion 让其平滑逼近。 */
export function applyEmotion(vrm, emotion) {
  if (!vrm || !vrm.expressionManager) return
  const s = _ensureState(vrm)
  const tgt = EMOTION_TO_VRM[emotion] || EMOTION_TO_VRM.neutral
  s.target = { ...tgt }
}

/** 在每帧 update 里调用，推进表情插值并写入 expressionManager。 */
export function stepEmotion(vrm) {
  if (!vrm || !vrm.expressionManager) return
  const s = _ensureState(vrm)
  for (const k of Object.keys(s.current)) {
    s.current[k] += (s.target[k] - s.current[k]) * EMO_LERP
    try { vrm.expressionManager.setValue(k, s.current[k]) } catch (_) {}
  }
}

/** 把 5 元音权重写入嘴型；weights 缺省时清零。 */
export function applyVowels(vrm, weights) {
  if (!vrm || !vrm.expressionManager) return
  const w = weights || { aa: 0, ih: 0, ou: 0, ee: 0, oh: 0 }
  for (const k of ['aa', 'ih', 'ou', 'ee', 'oh']) {
    try { vrm.expressionManager.setValue(k, Math.max(0, Math.min(1, w[k] || 0))) } catch (_) {}
  }
}

/**
 * 动作播放器：管理 AnimationMixer 上的 clip 切换。
 * clipMap: { name -> THREE.AnimationClip }
 */
export class MotionController {
  constructor(mixer, clipMap) {
    this.mixer = mixer
    this.clips = clipMap || {}
    /** @type {THREE.AnimationAction | null} */
    this.current = null
    this.currentName = ''
  }

  setClips(clipMap) {
    this.clips = clipMap || {}
  }

  /** 切到指定动作；若不存在则保持当前。 */
  play(name, { fade = 0.3, loop = true } = {}) {
    if (!this.mixer || !name || name === this.currentName) return
    const clip = this.clips[name]
    if (!clip) return
    const next = this.mixer.clipAction(clip)
    next.reset()
    next.setLoop(loop ? THREE.LoopRepeat : THREE.LoopOnce, Infinity)
    next.clampWhenFinished = !loop
    next.enabled = true
    next.fadeIn(fade).play()
    if (this.current && this.current !== next) {
      this.current.fadeOut(fade)
    }
    this.current = next
    this.currentName = name
  }
}

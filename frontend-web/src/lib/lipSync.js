/**
 * 嘴型同步分析器：从 HTMLAudioElement 实时取频谱 → 5 元音 (A/I/U/E/O) 权重。
 *
 * 算法（轻量、近似但足够"看起来在说话"）：
 *  1. AudioContext + AnalyserNode（FFT 1024）→ 频域幅度
 *  2. 计算总能量 (RMS)，作为"开口程度"基础信号
 *  3. 把 0~4kHz 划分为 5 个共振峰带，按各带能量比分配 5 元音权重
 *  4. 对结果做时间平滑（指数滑动平均），避免抖动
 *
 * 用法：
 *   const ls = new LipSyncAnalyzer()
 *   ls.attach(audioElement)
 *   const w = ls.read()  // { aa, ih, ou, ee, oh, mouthOpen } 范围 0~1
 *   ls.detach()
 */

const FFT_SIZE = 1024
const SMOOTH = 0.35 // 时间平滑系数（越大越柔；过大会让嘴型迟缓）
// 每元音的频段权重（粗略对应共振峰位置，单位 Hz）
const VOWEL_BANDS = {
  aa: { f1: [600, 1100], f2: [1000, 1500], gain: 1.0 },
  ih: { f1: [200, 500], f2: [2000, 3000], gain: 0.9 },
  ou: { f1: [250, 500], f2: [600, 1000], gain: 0.9 },
  ee: { f1: [300, 600], f2: [1800, 2600], gain: 0.9 },
  oh: { f1: [400, 700], f2: [800, 1100], gain: 1.0 },
}

export class LipSyncAnalyzer {
  constructor() {
    /** @type {AudioContext | null} */
    this.ctx = null
    /** @type {AnalyserNode | null} */
    this.analyser = null
    /** @type {Uint8Array | null} */
    this.freq = null
    /** @type {MediaElementAudioSourceNode | null} */
    this.source = null
    /** @type {HTMLAudioElement | null} */
    this.el = null
    this.smoothed = { aa: 0, ih: 0, ou: 0, ee: 0, oh: 0, mouthOpen: 0 }
    this._sampleRate = 48000
  }

  /** 绑定音频元素（同一元素多次 attach 会复用 source）。 */
  attach(audioEl) {
    if (!audioEl) return
    if (this.el === audioEl && this.ctx) return
    this.detach()
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext
      if (!Ctx) return
      this.ctx = new Ctx()
      this._sampleRate = this.ctx.sampleRate
      this.source = this.ctx.createMediaElementSource(audioEl)
      this.analyser = this.ctx.createAnalyser()
      this.analyser.fftSize = FFT_SIZE
      this.analyser.smoothingTimeConstant = 0.4
      this.freq = new Uint8Array(this.analyser.frequencyBinCount)
      // 串联：source → analyser → destination（保证还能听到声音）
      this.source.connect(this.analyser)
      this.analyser.connect(this.ctx.destination)
      this.el = audioEl
    } catch (e) {
      // 同一 audio 元素不能创建第二个 MediaElementSource，遇到这种情况直接放弃
      console.warn('[lipSync] attach failed:', e)
      this.detach()
    }
  }

  detach() {
    try { this.source && this.source.disconnect() } catch (_) {}
    try { this.analyser && this.analyser.disconnect() } catch (_) {}
    try { this.ctx && this.ctx.close() } catch (_) {}
    this.ctx = null
    this.analyser = null
    this.source = null
    this.freq = null
    this.el = null
    this.smoothed = { aa: 0, ih: 0, ou: 0, ee: 0, oh: 0, mouthOpen: 0 }
  }

  /** 把音频上下文恢复运行（受浏览器自动播放限制影响时调用）。 */
  async resume() {
    if (this.ctx && this.ctx.state === 'suspended') {
      try { await this.ctx.resume() } catch (_) {}
    }
  }

  /** 读取当前帧的元音权重与张嘴量。无音频时返回全零。 */
  read() {
    if (!this.analyser || !this.freq) return { ...this.smoothed }
    this.analyser.getByteFrequencyData(this.freq)

    // 1) 总能量 → 张嘴量
    let sum = 0
    for (let i = 0; i < this.freq.length; i++) sum += this.freq[i]
    const avg = sum / this.freq.length / 255 // 0~1
    const mouthOpen = Math.min(1, avg * 2.2)

    // 2) 各元音频带能量
    const binHz = this._sampleRate / FFT_SIZE
    const raw = { aa: 0, ih: 0, ou: 0, ee: 0, oh: 0 }
    for (const [name, band] of Object.entries(VOWEL_BANDS)) {
      raw[name] = (this._bandEnergy(band.f1, binHz) + this._bandEnergy(band.f2, binHz)) * band.gain
    }
    // 归一化到主导元音（取最大者，其它按比例）
    const maxRaw = Math.max(raw.aa, raw.ih, raw.ou, raw.ee, raw.oh, 1e-6)
    const target = {
      aa: (raw.aa / maxRaw) * mouthOpen,
      ih: (raw.ih / maxRaw) * mouthOpen,
      ou: (raw.ou / maxRaw) * mouthOpen,
      ee: (raw.ee / maxRaw) * mouthOpen,
      oh: (raw.oh / maxRaw) * mouthOpen,
      mouthOpen,
    }

    // 3) 时间平滑
    for (const k of Object.keys(target)) {
      this.smoothed[k] = this.smoothed[k] * SMOOTH + target[k] * (1 - SMOOTH)
    }
    return { ...this.smoothed }
  }

  _bandEnergy(range, binHz) {
    if (!this.freq) return 0
    const lo = Math.max(0, Math.floor(range[0] / binHz))
    const hi = Math.min(this.freq.length - 1, Math.ceil(range[1] / binHz))
    if (hi <= lo) return 0
    let s = 0
    for (let i = lo; i <= hi; i++) s += this.freq[i]
    return s / (hi - lo + 1) / 255 // 归一化 0~1
  }
}

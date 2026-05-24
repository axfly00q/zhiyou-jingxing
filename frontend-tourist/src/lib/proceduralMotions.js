/**
 * 程序化生成数字人动作 clip（无需 .vrma 素材文件）。
 *
 * 用法：
 *   import { buildClips } from './proceduralMotions'
 *   const clips = buildClips(vrm)   // { idle, wave, explain, think, nod, shake }
 *   motionCtl.setClips(clips)
 *   motionCtl.play('wave')
 *
 * 原理：
 *   - 通过 vrm.humanoid.getNormalizedBoneNode(name) 拿到归一化骨骼节点
 *     （normalized 姿态下所有骨骼旋转都为 0，方向语义稳定，跨模型一致）
 *   - 对每根需要动的骨骼写 QuaternionKeyframeTrack
 *   - 用 THREE.AnimationClip 打包，丢给 AnimationMixer 即可
 *
 * 坐标系约定（VRM Normalized，A-pose 起始）：
 *   - rotation.z 正：右手系下手臂向 **内侧抬起**（贴向身体）
 *     -> 想让手垂下，左臂 z=+1.25 / 右臂 z=-1.25
 *   - rotation.x 正：骨骼向前折（spine 前倾、肘关节屈曲方向因左右镜像不同）
 *   - rotation.y 正：水平转动（head 摇头）
 */

import * as THREE from 'three'

// ---------- 工具 ----------

/** Euler -> Quaternion 数组（4 浮点）。order 默认 'XYZ'。 */
function eulerToQuatArr(x, y, z, order = 'XYZ') {
  const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(x, y, z, order))
  return [q.x, q.y, q.z, q.w]
}

/**
 * 为一根骨骼按关键帧表生成 QuaternionKeyframeTrack。
 *  vrm       : 当前 VRM 实例
 *  boneName  : VRM Humanoid 标准名（如 'leftUpperArm'）
 *  frames    : [{ t: 时间秒, e: [x,y,z] 欧拉角 }, ...]
 *  返回 null 表示该骨骼不存在 / 跳过。
 */
function trackForBone(vrm, boneName, frames) {
  const node = vrm.humanoid?.getNormalizedBoneNode(boneName)
  if (!node) return null
  const times = []
  const values = []
  for (const f of frames) {
    times.push(f.t)
    values.push(...eulerToQuatArr(f.e[0], f.e[1], f.e[2]))
  }
  // 注意：路径要用节点真实 name；同名节点不会冲突，因为 mixer 是绑到 vrm.scene
  return new THREE.QuaternionKeyframeTrack(
    `${node.name}.quaternion`,
    times,
    values,
  )
}

/** 把若干 track 组装为 AnimationClip；自动过滤空 track。 */
function makeClip(name, duration, tracks) {
  const clean = tracks.filter(Boolean)
  if (clean.length === 0) return null
  return new THREE.AnimationClip(name, duration, clean)
}

// ---------- 基础姿态 ----------

// rest（站立）状态各骨骼的"默认"姿态。idle/think 等动作以此为基线做扰动。
const REST = {
  leftUpperArm:  [0, 0,  1.25],
  rightUpperArm: [0, 0, -1.25],
  leftLowerArm:  [0, -0.15,  0.1],
  rightLowerArm: [0,  0.15, -0.1],
  spine: [0, 0, 0],
  chest: [0, 0, 0],
  neck:  [0, 0, 0],
  head:  [0, 0, 0],
}

// ---------- 各动作 ----------

/** idle：呼吸 + 肩部微沉 + 头部缓慢左右看。循环 4s。 */
function buildIdle(vrm) {
  const D = 4.0
  const tracks = []
  // 呼吸：胸腔在 0/2/4 秒微微抬起
  tracks.push(trackForBone(vrm, 'chest', [
    { t: 0,   e: [0, 0, 0] },
    { t: 2.0, e: [-0.04, 0, 0] }, // 胸口微抬
    { t: D,   e: [0, 0, 0] },
  ]))
  // spine 极轻微摆
  tracks.push(trackForBone(vrm, 'spine', [
    { t: 0,   e: [0, 0,  0.01] },
    { t: 2.0, e: [0, 0, -0.01] },
    { t: D,   e: [0, 0,  0.01] },
  ]))
  // 头部环视
  tracks.push(trackForBone(vrm, 'head', [
    { t: 0,   e: [0,  0.08, 0] },
    { t: 1.5, e: [-0.03, 0, 0] },
    { t: 3.0, e: [0, -0.08, 0] },
    { t: D,   e: [0,  0.08, 0] },
  ]))
  // 手臂维持下垂
  tracks.push(trackForBone(vrm, 'leftUpperArm',  [{ t: 0, e: REST.leftUpperArm },  { t: D, e: REST.leftUpperArm }]))
  tracks.push(trackForBone(vrm, 'rightUpperArm', [{ t: 0, e: REST.rightUpperArm }, { t: D, e: REST.rightUpperArm }]))
  tracks.push(trackForBone(vrm, 'leftLowerArm',  [{ t: 0, e: REST.leftLowerArm },  { t: D, e: REST.leftLowerArm }]))
  tracks.push(trackForBone(vrm, 'rightLowerArm', [{ t: 0, e: REST.rightLowerArm }, { t: D, e: REST.rightLowerArm }]))
  return makeClip('idle', D, tracks)
}

/** wave：右手举起挥手 2 次，2.4s。 */
function buildWave(vrm) {
  const D = 2.4
  const tracks = []
  // 右上臂抬到斜上方（z 从 -1.25 → -0.2，向上举）
  tracks.push(trackForBone(vrm, 'rightUpperArm', [
    { t: 0,   e: REST.rightUpperArm },
    { t: 0.4, e: [-0.3, -0.2, -0.4] },
    { t: 2.0, e: [-0.3, -0.2, -0.4] },
    { t: D,   e: REST.rightUpperArm },
  ]))
  // 右小臂屈起，加挥动
  tracks.push(trackForBone(vrm, 'rightLowerArm', [
    { t: 0,   e: REST.rightLowerArm },
    { t: 0.4, e: [0, 0.4, -1.2] },
    { t: 0.8, e: [0, 1.0, -1.2] },
    { t: 1.2, e: [0, 0.4, -1.2] },
    { t: 1.6, e: [0, 1.0, -1.2] },
    { t: 2.0, e: [0, 0.4, -1.2] },
    { t: D,   e: REST.rightLowerArm },
  ]))
  // 头略向举起的手方向偏
  tracks.push(trackForBone(vrm, 'head', [
    { t: 0,   e: [0, 0, 0] },
    { t: 0.6, e: [0, -0.15, 0] },
    { t: 1.8, e: [0, -0.15, 0] },
    { t: D,   e: [0, 0, 0] },
  ]))
  // 左侧保持
  tracks.push(trackForBone(vrm, 'leftUpperArm',  [{ t: 0, e: REST.leftUpperArm },  { t: D, e: REST.leftUpperArm }]))
  tracks.push(trackForBone(vrm, 'leftLowerArm',  [{ t: 0, e: REST.leftLowerArm },  { t: D, e: REST.leftLowerArm }]))
  return makeClip('wave', D, tracks)
}

/** explain：双手在身前小幅"摊开-收回"，配合身体微转。3s。 */
function buildExplain(vrm) {
  const D = 3.0
  const tracks = []
  tracks.push(trackForBone(vrm, 'rightUpperArm', [
    { t: 0,   e: REST.rightUpperArm },
    { t: 1.0, e: [-0.5,  0.3, -0.6] }, // 抬到身前
    { t: 2.0, e: [-0.5, -0.1, -0.6] }, // 摊开
    { t: D,   e: REST.rightUpperArm },
  ]))
  tracks.push(trackForBone(vrm, 'rightLowerArm', [
    { t: 0,   e: REST.rightLowerArm },
    { t: 1.0, e: [0, 0.6, -0.8] },
    { t: 2.0, e: [0, 0.2, -0.8] },
    { t: D,   e: REST.rightLowerArm },
  ]))
  tracks.push(trackForBone(vrm, 'leftUpperArm', [
    { t: 0,   e: REST.leftUpperArm },
    { t: 1.0, e: [-0.5, -0.3,  0.6] },
    { t: 2.0, e: [-0.5,  0.1,  0.6] },
    { t: D,   e: REST.leftUpperArm },
  ]))
  tracks.push(trackForBone(vrm, 'leftLowerArm', [
    { t: 0,   e: REST.leftLowerArm },
    { t: 1.0, e: [0, -0.6,  0.8] },
    { t: 2.0, e: [0, -0.2,  0.8] },
    { t: D,   e: REST.leftLowerArm },
  ]))
  tracks.push(trackForBone(vrm, 'spine', [
    { t: 0,   e: [0, 0, 0] },
    { t: 1.5, e: [-0.04, 0.04, 0] },
    { t: D,   e: [0, 0, 0] },
  ]))
  return makeClip('explain', D, tracks)
}

/** think：右手托腮 + 头微侧。2.4s。 */
function buildThink(vrm) {
  const D = 2.4
  const tracks = []
  // 右上臂略抬
  tracks.push(trackForBone(vrm, 'rightUpperArm', [
    { t: 0,   e: REST.rightUpperArm },
    { t: 0.6, e: [-0.2, 0.1, -0.7] },
    { t: 1.8, e: [-0.2, 0.1, -0.7] },
    { t: D,   e: REST.rightUpperArm },
  ]))
  // 右小臂屈到下巴附近
  tracks.push(trackForBone(vrm, 'rightLowerArm', [
    { t: 0,   e: REST.rightLowerArm },
    { t: 0.6, e: [0, 1.6, -1.6] },
    { t: 1.8, e: [0, 1.6, -1.6] },
    { t: D,   e: REST.rightLowerArm },
  ]))
  // 头侧偏 + 上抬
  tracks.push(trackForBone(vrm, 'head', [
    { t: 0,   e: [0, 0, 0] },
    { t: 0.6, e: [-0.08, 0.1, 0.12] },
    { t: 1.8, e: [-0.08, 0.1, 0.12] },
    { t: D,   e: [0, 0, 0] },
  ]))
  // 左侧保持
  tracks.push(trackForBone(vrm, 'leftUpperArm',  [{ t: 0, e: REST.leftUpperArm },  { t: D, e: REST.leftUpperArm }]))
  tracks.push(trackForBone(vrm, 'leftLowerArm',  [{ t: 0, e: REST.leftLowerArm },  { t: D, e: REST.leftLowerArm }]))
  return makeClip('think', D, tracks)
}

/** nod：点头 2 次，1.2s。 */
function buildNod(vrm) {
  const D = 1.2
  const tracks = []
  tracks.push(trackForBone(vrm, 'head', [
    { t: 0,   e: [0, 0, 0] },
    { t: 0.2, e: [0.18, 0, 0] },
    { t: 0.4, e: [0, 0, 0] },
    { t: 0.6, e: [0.18, 0, 0] },
    { t: 0.8, e: [0, 0, 0] },
    { t: D,   e: [0, 0, 0] },
  ]))
  return makeClip('nod', D, tracks)
}

/** shake：摇头 2 次，1.4s。 */
function buildShake(vrm) {
  const D = 1.4
  const tracks = []
  tracks.push(trackForBone(vrm, 'head', [
    { t: 0,   e: [0,  0, 0] },
    { t: 0.25, e: [0, -0.25, 0] },
    { t: 0.55, e: [0,  0.25, 0] },
    { t: 0.85, e: [0, -0.25, 0] },
    { t: 1.15, e: [0,  0.10, 0] },
    { t: D,    e: [0,  0, 0] },
  ]))
  return makeClip('shake', D, tracks)
}

/** 总入口：返回 { [name]: AnimationClip }，自动过滤空 clip。 */
export function buildClips(vrm) {
  const all = {
    idle:    buildIdle(vrm),
    wave:    buildWave(vrm),
    explain: buildExplain(vrm),
    think:   buildThink(vrm),
    nod:     buildNod(vrm),
    shake:   buildShake(vrm),
  }
  const out = {}
  for (const [k, v] of Object.entries(all)) {
    if (v) out[k] = v
  }
  return out
}

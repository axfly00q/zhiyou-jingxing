import re

with open('src/views/tourist/Chat.vue', 'r', encoding='utf-8') as f:
    content = f.read()

# We need to replace everything from "if (!resp.ok) throw new Error" ... down to "async function startRec()"
# Wait, let's find the boundaries.
start_idx = content.find("if (!resp.ok) throw new Error")
end_idx = content.find("async function startRec()")

if start_idx != -1 and end_idx != -1:
    before = content[:start_idx]
    after = content[end_idx:]

    replacement = """if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let sseBuffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      sseBuffer += decoder.decode(value, { stream: true })
      const lines = sseBuffer.split('\\n')
      sseBuffer = lines.pop()           // 保留未完整的行

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        let evt
        try { evt = JSON.parse(line.slice(6)) } catch { continue }

        if (evt.type === 'token') {
          messages.value[msgIdx].content += evt.text
          nextTick(() => { msgBox.value && (msgBox.value.scrollTop = msgBox.value.scrollHeight) })
        } else if (evt.type === 'done') {
          currentEmotion.value = evt.emotion || 'neutral'
          currentMotion.value = evt.motion || avatar.default_motion || 'idle'
          if (evt.new_route) {
            routeSpots.value = evt.new_route.spots || []
            routeTotalMinutes.value = evt.new_route.total_minutes || 0
            currentSpotIdx.value = 0
            sessionStorage.setItem('route', JSON.stringify(evt.new_route))
          }
          if (evt.audio_url) {
            const sep = evt.audio_url.includes('?') ? '&' : '?'
            currentAudioUrl.value = evt.audio_url + sep + 't=' + Date.now()
          } else {
            currentAudioUrl.value = ''
            if (synth && messages.value[msgIdx].content) {
              const utt = new SpeechSynthesisUtterance(messages.value[msgIdx].content)
              utt.lang = 'zh-CN';
              utt.onend = resetMotion;
              utt.onerror = resetMotion;
              synth.cancel(); synth.speak(utt)
            } else {
              setTimeout(resetMotion, 4000)
            }
          }
        }
      }
    }
    setTimeout(_pollPref, 1000)
  } catch (e) {
    if (!messages.value[msgIdx]?.content) {
      messages.value[msgIdx] = { role: 'assistant', content: '抱歉，服务暂时不可用。', citations: [] }
    }
  } finally {
    loading.value = false
  }
}

// B2: 打卡处理
async function handleCheckin(spotCode) {
  if (loading.value) return
  loading.value = true
  try {
    const r = await chatCheckin({
      session_id: sessionId.value,
      spot_code: spotCode,
      park_code: parkCode,
      avatar_code: avatar.code || undefined,
      route_context: buildRouteContext(),
    })
    // 展示景点介绍
    push('assistant', r.narrative)
    currentEmotion.value = r.emotion || 'joy'
    currentMotion.value = r.motion || 'wave'
    if (r.audio_url) {
      currentAudioUrl.value = r.audio_url + (r.audio_url.includes('?') ? '&' : '?') + 't=' + Date.now()
    } else {
      currentAudioUrl.value = ''
      if (synth && r.narrative) {
        const utt = new SpeechSynthesisUtterance(r.narrative)
        utt.lang = 'zh-CN'
        utt.onend = resetMotion
        utt.onerror = resetMotion
        synth.cancel()
        synth.speak(utt)
      } else {
        setTimeout(resetMotion, 4000)
      }
    }
    // 推进进度
    if (currentSpotIdx.value < routeSpots.value.length) {
      currentSpotIdx.value += 1
    }
    // 处理成就徽章
    if (r.badge) {
      pendingBadge.value = r.badge
      showBadge.value = true
    }
    // 提示下一站
    if (r.next_spot_name) {
      const walkTip = r.next_walk_minutes ? `，步行约 ${r.next_walk_minutes} 分钟` : ''
      push('assistant', `→ 下一站：**${r.next_spot_name}**${walkTip}`)
    } else if (currentSpotIdx.value >= routeSpots.value.length) {
      push('assistant', '🎉 路线全部完成！您已游遍所有景点，希望本次游览令您尽兴而归！')
    }
  } catch (e) {
    push('assistant', '打卡失败，请稍后重试。')
  } finally {
    loading.value = false
  }
}

function sendPreset(q) {
  if (loading.value) return
  input.value = q
  send()
}

"""

    with open('src/views/tourist/Chat.vue', 'w', encoding='utf-8') as f:
        f.write(before + replacement + after)
    print("Fixed Chat.vue")
else:
    print(f"Could not find boundaries! start={start_idx}, end={end_idx}")

const fs = require('fs');
const file = 'src/views/tourist/Chat.vue';
let content = fs.readFileSync(file, 'utf8');
const styleIdx = content.indexOf('<style scoped>');

if (styleIdx > -1) {
  const newStyle = `<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Serif+SC:wght@400;700;900&display=swap');
.serif-font { font-family: 'Noto Serif SC', 'Songti SC', 'STSong', serif; }

.layout { display: flex; flex-direction: row; width: 100%; height: 100vh; height: 100dvh; background: #05080c; overflow: hidden; font-family: 'Inter', system-ui, sans-serif; }

.avatar-pane { position: relative; flex: 0 0 45%; background-image: url('/images/lingshan_bg.png'); background-size: cover; background-position: center; overflow: hidden; }
.avatar-pane::before { content: ''; position: absolute; inset: 0; background: rgba(5, 8, 12, 0.4); z-index: 0; }

.vrm-fill { position: absolute; inset: 0; z-index: 1; }
.top-bar { position: absolute; top: env(safe-area-inset-top, 0); left: 0; right: 0; padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; color: #fff; z-index: 2; pointer-events: none; }
.top-bar .title { font-family: 'Noto Serif SC', serif; font-size: clamp(18px, 3.2vw, 28px); letter-spacing: 1px; text-shadow: 0 2px 4px rgba(0,0,0,0.8); }
.top-bar-right { display: flex; align-items: center; gap: 10px; pointer-events: auto; }
.top-bar .back { pointer-events: auto; color: #eab308; text-decoration: none; font-size: clamp(13px, 2vw, 18px); background: rgba(255,255,255,0.08); padding: 8px 14px; border-radius: 999px; backdrop-filter: blur(8px); border: 1px solid rgba(234, 179, 8, 0.3); }
.end-tour-btn { pointer-events: auto; background: linear-gradient(135deg, #eab308 0%, #ca8a04 100%); color: #000; font-weight: 600; border: none; padding: 8px 14px; border-radius: 999px; font-size: clamp(13px, 2vw, 18px); cursor: pointer; backdrop-filter: blur(8px); }

.interrupt-btn { position: absolute; right: 20px; bottom: 20px; width: clamp(56px, 8vw, 88px); height: clamp(56px, 8vw, 88px); border-radius: 50%; border: 1px solid rgba(255,255,255,0.2); background: rgba(255,255,255,0.1); color: #fff; font-size: clamp(20px, 3.5vw, 32px); cursor: pointer; backdrop-filter: blur(8px); z-index: 2; }

.chat-pane { flex: 1 1 55%; min-height: 0; display: flex; flex-direction: column; background: rgba(10, 15, 25, 0.85); backdrop-filter: blur(24px); border-left: 1px solid rgba(255,255,255,0.05); padding-bottom: env(safe-area-inset-bottom, 0); color: #e5e7eb; }

.route-map-container { flex: 0 0 auto; display: flex; flex-direction: column; border-bottom: 1px solid rgba(255,255,255,0.05); overflow-y: auto; }
.messages { flex: 1; min-height: 0; overflow-y: auto; padding: 24px; -webkit-overflow-scrolling: touch; }
.msg { margin: 12px 0; display: flex; }
.msg.user { justify-content: flex-end; }
.bubble { max-width: 82%; padding: 14px 18px; border-radius: 18px; line-height: 1.6; white-space: pre-wrap; font-size: clamp(14px, 2.6vw, 16px); backdrop-filter: blur(12px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
.msg.user .bubble { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); border-bottom-right-radius: 4px; }
.msg.assistant .bubble { background: rgba(255,255,255,0.05); color: #e5e7eb; border: 1px solid rgba(255,255,255,0.1); border-bottom-left-radius: 4px; }
.cites { font-size: clamp(11px, 1.8vw, 13px); color: #9ca3af; margin-top: 8px; }

.presets { display: flex; gap: 12px; padding: 12px 24px; overflow-x: auto; scroll-snap-type: x mandatory; -ms-overflow-style: none; scrollbar-width: none; border-top: 1px solid rgba(255,255,255,0.05); }
.presets::-webkit-scrollbar { display: none; }
.map-section { flex: 0 0 auto; border-bottom: 1px solid rgba(255,255,255,0.05); }
.map-toggle { display: flex; justify-content: space-between; align-items: center; padding: 10px 24px; cursor: pointer; font-size: 14px; color: #d1d5db; background: rgba(255,255,255,0.02); }
.map-arrow { color: #9ca3af; font-size: 11px; }
.chip { flex: 0 0 auto; scroll-snap-align: start; padding: 8px 16px; border: 1px solid rgba(234, 179, 8, 0.3); background: rgba(234, 179, 8, 0.1); color: #eab308; border-radius: 999px; font-size: clamp(13px, 2.2vw, 15px); cursor: pointer; white-space: nowrap; transition: all 0.3s; }
.chip:hover { background: rgba(234, 179, 8, 0.2); }

.input-bar { flex: 0 0 auto; padding: 16px 24px 24px; display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: stretch; }
textarea { resize: none; border: 1px solid rgba(255,255,255,0.1); border-radius: 16px; padding: 14px; font-size: clamp(14px, 2.2vw, 16px); font-family: inherit; outline: none; background: rgba(0,0,0,0.3); color: #fff; transition: border-color 0.3s; }
textarea:focus { border-color: #10b981; }
.btn-col { display: flex; flex-direction: column; gap: 8px; }
.btn { border: none; border-radius: 12px; padding: 0 16px; min-width: clamp(64px, 8vw, 96px); min-height: 44px; font-size: clamp(13px, 2vw, 15px); font-weight: 500; cursor: pointer; transition: all 0.3s; }
.btn.primary { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
.btn.primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn.primary:not(:disabled):hover { background: rgba(16, 185, 129, 0.25); }
.btn.ghost { background: transparent; color: #eab308; border: 1px solid rgba(234, 179, 8, 0.3); }
.btn.ghost:active { background: rgba(234, 179, 8, 0.1); }

@media (max-width: 1024px) and (orientation: portrait) { .layout { flex-direction: column; } .avatar-pane { flex: 0 0 50vh; } .chat-pane { flex: 1 1 50vh; border-left: none; border-top: 1px solid rgba(255,255,255,0.05); } }
</style>
`;
  fs.writeFileSync(file, content.substring(0, styleIdx) + newStyle, 'utf8');
  console.log('Chat.vue CSS updated successfully!');
} else {
  console.log('Could not find style tag.');
}

/**
 * NovaTech 智能客服 SDK（浮窗版）
 *
 * 用法：在任意网页引入本文件后，一行代码启动：
 *   <script src="https://你的域名/novatech-chat.js"></script>
 *   <script>
 *     NovatechChat.init({ apiBase: 'http://localhost:8010', title: '星澜数码客服' });
 *   </script>
 *
 * 特性：
 * - 页面右下角悬浮气泡，点击展开聊天窗口
 * - 消息走 /chat 接口（支持多轮 session）
 * - 零依赖（纯原生 JS + CSS），适配任何站点
 */
(function (global) {
  'use strict';

  const DEFAULTS = {
    apiBase: '',
    title: '智能客服',
    subtitle: '星澜数码 NovaTech',
    bubbleText: '💬',
    accent: '#2563eb',
    initialMessage: '您好，这里是星澜数码智能客服，可以咨询产品参数、订单物流、退款售后～',
    sessionId: 'sdk-' + Math.random().toString(36).slice(2, 10),
  };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function init(options) {
    const cfg = Object.assign({}, DEFAULTS, options || {});

    // ---- 注入样式 ----
    const style = document.createElement('style');
    style.textContent = [
      '#novatech-sdk-wrap{position:fixed;right:24px;bottom:24px;z-index:2147483000;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}',
      '#novatech-sdk-bubble{width:56px;height:56px;border-radius:50%;background:' + cfg.accent + ';color:#fff;font-size:24px;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.25);border:none;transition:transform .15s}',
      '#novatech-sdk-bubble:hover{transform:scale(1.08)}',
      '#novatech-sdk-panel{position:fixed;right:24px;bottom:92px;width:360px;max-width:calc(100vw - 32px);height:520px;max-height:calc(100vh - 120px);background:#fff;border-radius:14px;box-shadow:0 12px 40px rgba(15,23,42,.28);display:none;flex-direction:column;overflow:hidden;border:1px solid #e6e8ee}',
      '#novatech-sdk-panel.open{display:flex}',
      '#novatech-sdk-head{background:' + cfg.accent + ';color:#fff;padding:14px 16px;display:flex;justify-content:space-between;align-items:center}',
      '#novatech-sdk-head-title{font-weight:600;font-size:14px}',
      '#novatech-sdk-head-sub{font-size:11px;opacity:.85;margin-top:2px}',
      '#novatech-sdk-close{cursor:pointer;opacity:.8;font-size:18px;background:none;border:none;color:#fff}',
      '#novatech-sdk-body{flex:1;overflow-y:auto;padding:14px;background:#f4f6fa;display:flex;flex-direction:column;gap:10px}',
      '#novatech-sdk-msg{max-width:82%;padding:9px 12px;border-radius:12px;font-size:13px;line-height:1.55;white-space:pre-wrap;word-break:break-word}',
      '.nsdk-user{align-self:flex-end;background:' + cfg.accent + ';color:#fff;border-bottom-right-radius:4px}',
      '.nsdk-agent{align-self:flex-start;background:#fff;color:#1f2937;border:1px solid #e6e8ee;border-bottom-left-radius:4px}',
      '#novatech-sdk-inputbar{display:flex;gap:8px;padding:10px 12px;border-top:1px solid #e6e8ee;background:#fff}',
      '#novatech-sdk-input{flex:1;border:1px solid #e6e8ee;border-radius:8px;padding:9px 11px;font-size:13px;outline:none}',
      '#novatech-sdk-send{background:' + cfg.accent + ';color:#fff;border:none;border-radius:8px;padding:0 16px;font-size:13px;cursor:pointer}',
    ].join('\n');
    document.head.appendChild(style);

    // ---- 构建 DOM ----
    const wrap = document.createElement('div');
    wrap.id = 'novatech-sdk-wrap';
    wrap.innerHTML =
      '<button id="novatech-sdk-bubble" title="在线客服">' + esc(cfg.bubbleText) + '</button>' +
      '<div id="novatech-sdk-panel">' +
      '  <div id="novatech-sdk-head">' +
      '    <div><div id="novatech-sdk-head-title">' + esc(cfg.title) + '</div><div id="novatech-sdk-head-sub">' + esc(cfg.subtitle) + '</div></div>' +
      '    <button id="novatech-sdk-close">✕</button>' +
      '  </div>' +
      '  <div id="novatech-sdk-body"></div>' +
      '  <div id="novatech-sdk-inputbar">' +
      '    <input id="novatech-sdk-input" placeholder="请输入您的问题…" />' +
      '    <button id="novatech-sdk-send">发送</button>' +
      '  </div>' +
      '</div>';
    document.body.appendChild(wrap);

    const body = wrap.querySelector('#novatech-sdk-body');
    const input = wrap.querySelector('#novatech-sdk-input');
    const bubble = wrap.querySelector('#novatech-sdk-bubble');
    const panel = wrap.querySelector('#novatech-sdk-panel');
    let opened = false;

    function appendMsg(role, text) {
      const div = document.createElement('div');
      div.className = 'nsdk-msg ' + (role === 'user' ? 'nsdk-user' : 'nsdk-agent');
      div.textContent = text;
      body.appendChild(div);
      body.scrollTop = body.scrollHeight;
    }

    async function send() {
      const text = input.value.trim();
      if (!text) return;
      input.value = '';
      appendMsg('user', text);
      appendMsg('agent', '正在思考…');
      try {
        const resp = await fetch(cfg.apiBase + '/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, platform: 'novatech', session_id: cfg.sessionId }),
        });
        const data = await resp.json();
        const last = body.lastElementChild;
        if (last && last.textContent === '正在思考…') last.remove();
        appendMsg('agent', data.answer || '抱歉，暂时无法回答，已为您转人工。');
      } catch (e) {
        const last = body.lastElementChild;
        if (last && last.textContent === '正在思考…') last.remove();
        appendMsg('agent', '网络异常，请确认客服服务已启动。');
      }
    }

    bubble.addEventListener('click', function () {
      opened = !opened;
      panel.classList.toggle('open', opened);
      if (opened && !body.children.length) {
        appendMsg('agent', cfg.initialMessage);
      }
    });
    wrap.querySelector('#novatech-sdk-close').addEventListener('click', function () {
      opened = false;
      panel.classList.remove('open');
    });
    wrap.querySelector('#novatech-sdk-send').addEventListener('click', send);
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter') send(); });
  }

  global.NovatechChat = { init: init };
})(window);

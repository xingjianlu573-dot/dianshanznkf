const API_URL = window.AGENT_API_URL || 'http://127.0.0.1:8010';

const demoPrompts = [
  'Air100 和 Studio200 怎么选？',
  'Watch30 防水吗？支持 iPhone 吗？',
  '我的订单 SO20260912001 物流到哪了？',
  '我想退货，订单 SO20260930004 怎么退款？',
  '你们一般多久发货？运费多少？',
  '这质量也太差了，我要投诉，转人工！',
];

const intentLabels = {
  PRE_SALE: '售前咨询 · RAG',
  RAG: 'RAG 知识库',
  ORDER_STATUS: '售后 · 订单接口',
  REFUND: '售后 · 退款流程',
  ESCALATE: '升级人工',
};

const chat = document.querySelector('#chat');
const composer = document.querySelector('#composer');
const input = document.querySelector('#message-input');
const prompts = document.querySelector('#prompts');
const error = document.querySelector('#error');

function esc(s) {
  return String(s ?? '').replace(/[&<>"]/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;',
  }[c]));
}

function ticketCard(t) {
  if (!t) return '';
  const pClass = t.priority.startsWith('P0') ? 'p0' : t.priority.startsWith('P1') ? 'p1' : 'p2';
  return `
    <div class="ticket">
      <div class="ticket-head">
        <span class="ticket-id">工单 ${esc(t.ticket_id)}</span>
        <span class="priority ${pClass}">${esc(t.priority)}</span>
      </div>
      <table>
        <tr><td>问题分类</td><td>${esc(t.category)}</td></tr>
        <tr><td>处理建议</td><td>${esc(t.suggested_action)}</td></tr>
        ${t.order_id ? `<tr><td>关联订单</td><td>${esc(t.order_id)}</td></tr>` : ''}
        <tr><td>状态</td><td>${esc(t.status)} · ${esc(t.created_at)}</td></tr>
      </table>
    </div>`;
}

function createMessage({ role, text, intent, toolResult, sources, ticket }) {
  const isUser = role === 'user';
  const article = document.createElement('article');
  article.className = `message ${isUser ? 'message-user' : 'message-agent'}`;

  const header = document.createElement('div');
  header.className = 'message-header';
  const label = document.createElement('span');
  label.textContent = isUser ? '客户' : '客服 Agent';
  header.appendChild(label);
  if (intent) {
    const badge = document.createElement('span');
    badge.className = `intent intent-${intent.toLowerCase()}`;
    badge.textContent = `${intentLabels[intent] || intent}`;
    header.appendChild(badge);
  }
  article.appendChild(header);

  const para = document.createElement('p');
  para.textContent = text;
  article.appendChild(para);

  if (ticket) {
    const wrap = document.createElement('div');
    wrap.innerHTML = ticketCard(ticket);
    article.appendChild(wrap.firstElementChild);
  }

  if (toolResult && Object.keys(toolResult).length) {
    const d = document.createElement('details');
    d.innerHTML = `<summary>调用接口返回</summary><pre>${esc(JSON.stringify(toolResult, null, 2))}</pre>`;
    article.appendChild(d);
  }

  if (sources && sources.length) {
    const d = document.createElement('details');
    const src = sources.map(s => `<section><strong>${esc(s.file_name)}</strong><p>${esc(s.text)}</p></section>`).join('');
    d.innerHTML = `<summary>知识库引用（${sources.length}）</summary>${src}`;
    article.appendChild(d);
  }

  chat.appendChild(article);
  chat.scrollTop = chat.scrollHeight;
}

function setLoading(v) {
  composer.querySelector('button').disabled = v;
  input.disabled = v;
  document.querySelectorAll('.quick button').forEach(b => b.disabled = v);
}

async function sendMessage(text) {
  text = (text || '').trim();
  if (!text) return;
  input.value = '';
  error.textContent = '';
  createMessage({ role: 'user', text });
  setLoading(true);

  const typing = document.createElement('div');
  typing.className = 'typing';
  typing.textContent = '路由中：意图识别 → 工具调用 / RAG 检索…';
  chat.appendChild(typing);

  try {
    const resp = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, platform: 'novatech' }),
    });
    const data = await resp.json();
    typing.remove();
    if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
    createMessage({
      role: 'agent',
      text: data.answer,
      intent: data.intent,
      toolResult: data.tool_result,
      sources: data.sources,
      ticket: data.ticket,
    });
  } catch (e) {
    typing.remove();
    error.textContent = e.message;
    createMessage({ role: 'agent', text: '后端未启动，请先运行 uvicorn api:app --port 8000' });
  } finally {
    setLoading(false);
    input.focus();
  }
}

demoPrompts.forEach(p => {
  const b = document.createElement('button');
  b.type = 'button';
  b.textContent = p;
  b.addEventListener('click', () => sendMessage(p));
  prompts.appendChild(b);
});

composer.addEventListener('submit', e => { e.preventDefault(); sendMessage(input.value); });

createMessage({ role: 'agent', text: '您好，这里是星澜数码智能客服。可以咨询产品参数、订单物流、退款售后，我会自动为您生成工单。' });
setLoading(false);

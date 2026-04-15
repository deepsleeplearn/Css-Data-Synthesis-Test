let selectedScenario = null;
let currentSessionId = null;
let currentSlotKeys = [];
let nextRoundIndex = 1;
let sessionClosed = true;
let reviewPending = false;
let authenticatedUser = null;

const authGate = document.getElementById('auth-gate');
const appShell = document.getElementById('app-shell');
const authError = document.getElementById('auth-error');
const loginForm = document.getElementById('login-form');
const loginUsername = document.getElementById('login-username');
const loginPassword = document.getElementById('login-password');
const loginButton = document.getElementById('login-btn');
const authUserName = document.getElementById('auth-user-name');
const authUserMeta = document.getElementById('auth-user-meta');
const reviewModal = document.getElementById('review-modal');
const reviewSummary = document.getElementById('review-summary');
const reviewErrorFields = document.getElementById('review-error-fields');
const failedFlowStageSelect = document.getElementById('failed-flow-stage');
const reviewNotes = document.getElementById('review-notes');
const reviewPersistCheckbox = document.getElementById('review-persist-to-db');
const reviewSubmitButton = document.getElementById('review-submit-btn');

function terminalPlaceholderHtml() {
    return `
        <div class="terminal-empty">
            <p>登录并启动会话后，这里会按 CLI 方式逐行输出会话内容。</p>
            <p>第一轮由你先输入用户话术，客服不会预先发开场白。</p>
        </div>
    `;
}

function appendTerminalLine(text, tone = 'system') {
    const output = document.getElementById('terminal-output');
    const empty = output.querySelector('.terminal-empty');
    if (empty) empty.remove();

    const line = document.createElement('div');
    line.className = `terminal-line ${tone}`;
    line.textContent = text;
    output.appendChild(line);
    output.scrollTop = output.scrollHeight;
}

function setSessionStatus(status) {
    const badge = document.getElementById('session-status');
    badge.textContent = status;
    badge.className = `status-badge ${status}`;
}

function setNextRound(roundIndex) {
    nextRoundIndex = roundIndex || 1;
    document.getElementById('round-indicator').textContent = `下一轮: ${currentSessionId ? nextRoundIndex : '-'}`;
    document.getElementById('command-prompt').textContent = `[${nextRoundIndex}] 用户:`;
}

function setSessionIdIndicator(sessionId) {
    document.getElementById('session-id-indicator').textContent = `Session ID: ${sessionId || '-'}`;
}

function updateInputAvailability(enabled) {
    const input = document.getElementById('user-input');
    const button = document.getElementById('send-btn');
    const endButton = document.getElementById('end-session-btn');
    const canInteract = enabled && !reviewPending && Boolean(authenticatedUser);
    input.disabled = !canInteract;
    button.disabled = !canInteract;
    endButton.disabled = !currentSessionId || sessionClosed || !authenticatedUser;
    if (canInteract) input.focus();
}

function resetReviewState() {
    reviewPending = false;
    reviewModal.classList.add('hidden');
    reviewModal.setAttribute('aria-hidden', 'true');
    document.querySelectorAll('input[name="review-correctness"]').forEach((input) => {
        input.checked = false;
    });
    reviewErrorFields.classList.add('hidden');
    failedFlowStageSelect.innerHTML = '<option value="">请选择出错流程</option>';
    failedFlowStageSelect.value = '';
    reviewNotes.value = '';
    reviewSubmitButton.disabled = false;
}

function selectedCorrectnessValue() {
    return document.querySelector('input[name="review-correctness"]:checked')?.value || '';
}

function syncReviewErrorFields() {
    const isIncorrect = selectedCorrectnessValue() === 'incorrect';
    reviewErrorFields.classList.toggle('hidden', !isIncorrect);
}

function openReviewModal(data) {
    if (!data.review_required || !currentSessionId) return;
    reviewPending = true;
    reviewSummary.textContent = data.status === 'completed'
        ? `会话已正常结束。Session ID: ${currentSessionId}。请标记当前测试流程是否正确。`
        : `会话已结束。Session ID: ${currentSessionId}。请标记当前测试流程是否正确，并在有问题时指出出错流程。`;
    failedFlowStageSelect.innerHTML = '<option value="">请选择出错流程</option>';
    (data.review_options || []).forEach((option) => {
        const element = document.createElement('option');
        element.value = option.key;
        element.textContent = option.label;
        failedFlowStageSelect.appendChild(element);
    });
    reviewPersistCheckbox.checked = Boolean(data.persist_to_db_default);
    reviewModal.classList.remove('hidden');
    reviewModal.setAttribute('aria-hidden', 'false');
    syncReviewErrorFields();
}

function updateScenarioHeader(scenario) {
    const title = document.getElementById('current-scenario-title');
    if (!scenario) {
        title.textContent = '请选择场景并启动会话';
        return;
    }
    title.textContent = `${scenario.scenario_id} | ${scenario.product.brand} ${scenario.product.model}`;
}

function updateInspector(slots = {}, state = {}) {
    const slotsCont = document.getElementById('slots-container');
    const stateCont = document.getElementById('state-container');

    if (currentSlotKeys.length === 0) {
        slotsCont.innerHTML = '<p class="terminal-hint">会话开始后显示</p>';
    } else {
        slotsCont.innerHTML = '';
        currentSlotKeys.forEach((slot) => {
            const value = slots[slot] || '';
            const item = document.createElement('div');
            item.className = 'data-item';
            item.innerHTML = `
                <span class="data-key">${slot}</span>
                <span class="data-value ${value ? 'filled' : ''}">${value || '-'}</span>
            `;
            slotsCont.appendChild(item);
        });
    }

    const visibleStateEntries = Object.entries(state).filter(([, value]) => {
        if (value === null || value === false || value === 0 || value === '') return false;
        if (Array.isArray(value) && value.length === 0) return false;
        return true;
    });

    if (visibleStateEntries.length === 0) {
        stateCont.innerHTML = '<p class="terminal-hint">当前没有活跃运行时状态</p>';
        return;
    }

    stateCont.innerHTML = '';
    visibleStateEntries.forEach(([key, value]) => {
        const item = document.createElement('div');
        item.className = 'data-item state-item';
        item.innerHTML = `
            <span class="data-key">${key}</span>
            <span class="data-value mono">${JSON.stringify(value)}</span>
        `;
        stateCont.appendChild(item);
    });
}

function setAuthError(message = '') {
    authError.textContent = message;
    authError.classList.toggle('hidden', !message);
}

function resetWorkspace() {
    selectedScenario = null;
    currentSessionId = null;
    currentSlotKeys = [];
    sessionClosed = true;
    resetReviewState();
    updateScenarioHeader(null);
    updateInspector({}, {});
    setSessionStatus('idle');
    setSessionIdIndicator('');
    setNextRound(1);
    updateInputAvailability(false);
    document.getElementById('scenario-list').innerHTML = '<div class="terminal-hint">登录后显示场景列表</div>';
    document.getElementById('terminal-output').innerHTML = terminalPlaceholderHtml();
    document.querySelectorAll('.scenario-item').forEach((item) => item.classList.remove('active'));
}

function applyAuthenticatedState(user) {
    authenticatedUser = user;
    authUserName.textContent = user.display_name || user.username;
    authUserMeta.textContent = `备案账号：${user.username}`;
    authGate.classList.add('hidden');
    appShell.classList.remove('hidden');
    setAuthError('');
}

function applyLoggedOutState(message = '') {
    authenticatedUser = null;
    authUserName.textContent = '未登录';
    authUserMeta.textContent = '只有备案账号可访问测试台。';
    appShell.classList.add('hidden');
    authGate.classList.remove('hidden');
    loginPassword.value = '';
    setAuthError(message);
    resetWorkspace();
}

async function safeJson(response) {
    try {
        return await response.json();
    } catch (error) {
        return {};
    }
}

async function apiFetch(url, options = {}) {
    const response = await fetch(url, options);
    const data = await safeJson(response);
    if (response.status === 401) {
        applyLoggedOutState(data.detail || '登录状态已失效，请重新登录。');
        throw new Error(data.detail || '请先登录');
    }
    if (!response.ok) {
        throw new Error(data.detail || '请求失败');
    }
    return data;
}

async function loadScenarios() {
    const list = document.getElementById('scenario-list');
    list.innerHTML = '<div class="terminal-hint">加载中...</div>';
    try {
        const scenarios = await apiFetch('/api/scenarios');
        list.innerHTML = '';

        scenarios.forEach((scenario, index) => {
            const item = document.createElement('button');
            item.type = 'button';
            item.className = 'scenario-item';
            item.innerHTML = `
                <span class="scenario-title">${scenario.product}</span>
                <span class="scenario-meta">${scenario.id}</span>
                <span class="scenario-meta">${scenario.request} | max_turns=${scenario.max_turns}</span>
                <span class="scenario-issue">${scenario.issue}</span>
            `;
            item.onclick = () => selectScenario(scenarios[index], item);
            list.appendChild(item);
        });
    } catch (error) {
        if (authenticatedUser) {
            list.innerHTML = `<div class="terminal-hint error">${error.message}</div>`;
        }
    }
}

function selectScenario(scenario, element) {
    selectedScenario = scenario;
    document.querySelectorAll('.scenario-item').forEach((item) => item.classList.remove('active'));
    element.classList.add('active');
    updateScenarioHeader({
        scenario_id: scenario.id,
        product: { brand: scenario.product.split(' ')[0] || scenario.product, model: scenario.product.replace(/^[^ ]+\s*/, '') },
    });
}

async function checkAuth() {
    resetWorkspace();
    const response = await fetch('/api/auth/me');
    const data = await safeJson(response);
    if (!response.ok) {
        applyLoggedOutState('');
        return;
    }

    applyAuthenticatedState(data.user);
    await loadScenarios();
}

async function login(event) {
    event.preventDefault();
    const username = loginUsername.value.trim();
    const password = loginPassword.value;
    if (!username || !password) {
        setAuthError('请输入账号和密码。');
        return;
    }

    loginButton.disabled = true;
    setAuthError('');
    try {
        const data = await apiFetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        applyAuthenticatedState(data.user);
        loginPassword.value = '';
        await loadScenarios();
    } catch (error) {
        if (!authenticatedUser) {
            setAuthError(error.message);
        }
    } finally {
        loginButton.disabled = false;
    }
}

async function logout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
    } finally {
        applyLoggedOutState('');
    }
}

async function submitReview() {
    if (!currentSessionId) return;

    const correctness = selectedCorrectnessValue();
    if (!correctness) {
        appendTerminalLine('[系统错误] 请先选择本次流程是否正确。', 'error');
        return;
    }

    const isCorrect = correctness === 'correct';
    const failedFlowStage = failedFlowStageSelect.value;
    if (!isCorrect && !failedFlowStage) {
        appendTerminalLine('[系统错误] 流程错误时必须选择出错流程。', 'error');
        return;
    }

    reviewSubmitButton.disabled = true;
    try {
        const data = await apiFetch('/api/session/review', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                is_correct: isCorrect,
                failed_flow_stage: failedFlowStage,
                notes: reviewNotes.value,
                persist_to_db: reviewPersistCheckbox.checked,
            }),
        });

        appendTerminalLine(
            data.persisted_to_db
                ? `[系统] 评审已提交，session_id=${data.session_id}，username=${data.username}，数据已写入 SQLite：${data.db_path}`
                : `[系统] 评审已提交，session_id=${data.session_id}，username=${data.username}，本次数据未写入 SQLite。`,
            'system',
        );
        resetReviewState();
        updateInputAvailability(false);
    } catch (error) {
        reviewSubmitButton.disabled = false;
        appendTerminalLine(`[系统错误] ${error.message}`, 'error');
    }
}

async function startSession() {
    if (reviewPending) {
        appendTerminalLine('请先完成上一条测试记录的评审。', 'error');
        return;
    }
    if (!selectedScenario) {
        appendTerminalLine('请先在左侧选择一个场景。', 'error');
        return;
    }

    const maxRoundsRaw = document.getElementById('max-rounds').value.trim();
    const payload = {
        scenario_id: selectedScenario.id,
        auto_generate_hidden_settings: document.getElementById('auto-hidden-settings').checked,
        known_address: document.getElementById('known-address').value,
        persist_to_db: document.getElementById('persist-to-db').checked,
    };
    if (maxRoundsRaw) {
        payload.max_rounds = Number(maxRoundsRaw);
    }

    const output = document.getElementById('terminal-output');
    output.innerHTML = '';
    appendTerminalLine('正在初始化手工测试会话...', 'system');
    updateInputAvailability(false);

    try {
        const data = await apiFetch('/api/session/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        currentSessionId = data.session_id;
        currentSlotKeys = Object.keys(data.collected_slots || {});
        sessionClosed = false;
        resetReviewState();

        output.innerHTML = '';
        data.initial_lines.forEach((line) => appendTerminalLine(line, 'system'));
        appendTerminalLine(`[系统] 当前会话 session_id: ${data.session_id}`, 'system');
        setSessionStatus(data.status);
        setSessionIdIndicator(data.session_id);
        setNextRound(data.next_round_index);
        updateScenarioHeader(data.scenario);
        updateInspector(data.collected_slots, data.runtime_state);
        updateInputAvailability(true);
    } catch (error) {
        currentSessionId = null;
        currentSlotKeys = [];
        sessionClosed = true;
        resetReviewState();
        setSessionStatus('error');
        setSessionIdIndicator('');
        setNextRound(1);
        updateInspector({}, {});
        appendTerminalLine(`[系统错误] ${error.message}`, 'error');
    }
}

async function forceEndSession() {
    if (!currentSessionId || sessionClosed) return;

    try {
        const data = await apiFetch('/api/session/respond', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: currentSessionId, text: '/quit' }),
        });

        appendTerminalLine('[系统] 已手动强制结束会话', 'system');
        (data.output_lines || []).forEach((line) => appendTerminalLine(line, 'system'));
        setSessionStatus(data.status);
        setNextRound(data.next_round_index);
        updateInspector(data.collected_slots, data.runtime_state);
        sessionClosed = Boolean(data.session_closed);
        updateInputAvailability(!sessionClosed);
        if (sessionClosed) openReviewModal(data);
    } catch (error) {
        appendTerminalLine(`[系统错误] ${error.message}`, 'error');
    }
}

async function sendMessage() {
    const input = document.getElementById('user-input');
    const rawText = input.value;
    const text = rawText.trim();
    if (!text || !currentSessionId || sessionClosed) return;

    input.value = '';
    appendTerminalLine(`[${nextRoundIndex}] 用户: ${text}`, 'user');

    try {
        const data = await apiFetch('/api/session/respond', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: currentSessionId, text: rawText }),
        });

        if (data.service_turn) {
            appendTerminalLine(
                `[${data.service_turn.round_label}] ${data.service_turn.speaker}: ${data.service_turn.text}`,
                'service',
            );
        }

        (data.output_lines || []).forEach((line) => appendTerminalLine(line, 'system'));

        setSessionStatus(data.status);
        setNextRound(data.next_round_index);
        updateInspector(data.collected_slots, data.runtime_state);

        sessionClosed = Boolean(data.session_closed);
        updateInputAvailability(!sessionClosed);
        if (sessionClosed) openReviewModal(data);
    } catch (error) {
        appendTerminalLine(`[系统错误] ${error.message}`, 'error');
    }
}

loginForm.addEventListener('submit', login);
document.getElementById('logout-btn').onclick = logout;
document.getElementById('start-session-btn').onclick = startSession;
document.getElementById('end-session-btn').onclick = forceEndSession;
document.getElementById('send-btn').onclick = sendMessage;
document.getElementById('review-submit-btn').onclick = submitReview;
document.querySelectorAll('input[name="review-correctness"]').forEach((input) => {
    input.addEventListener('change', syncReviewErrorFields);
});
document.getElementById('user-input').addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault();
        sendMessage();
    }
});

setSessionStatus('idle');
setSessionIdIndicator('');
setNextRound(1);
resetReviewState();
checkAuth();

let selectedScenario = null;
let currentSessionId = null;
let currentSlotKeys = [];
let nextRoundIndex = 1;
let sessionClosed = true;
let sessionBusy = false;
let sessionReviewLocked = false;
let sessionTerminalEntries = [];
let reviewPending = false;
let reviewAvailable = false;
let reviewContext = null;
let authenticatedUser = null;

const authGate = document.getElementById('auth-gate');
const appShell = document.getElementById('app-shell');
const authError = document.getElementById('auth-error');
const loginForm = document.getElementById('login-form');
const loginUsername = document.getElementById('login-username');
const loginPassword = document.getElementById('login-password');
const loginPasswordToggle = document.getElementById('login-password-toggle');
const loginPasswordToggleLabel = document.getElementById('login-password-toggle-label');
const loginButton = document.getElementById('login-btn');
const authUserName = document.getElementById('auth-user-name');
const authUserMeta = document.getElementById('auth-user-meta');
const reviewModal = document.getElementById('review-modal');
const reviewCloseButton = document.getElementById('review-close-btn');
const reviewToggleButton = document.getElementById('review-toggle-btn');
const reviewSummary = document.getElementById('review-summary');
const reviewErrorFields = document.getElementById('review-error-fields');
const failedFlowStageSelect = document.getElementById('failed-flow-stage');
const reviewNotes = document.getElementById('review-notes');
const reviewPersistCheckbox = document.getElementById('review-persist-to-db');
const reviewSubmitButton = document.getElementById('review-submit-btn');
const terminalScrollRegion = document.getElementById('terminal-scroll-region');
const terminalOutput = document.getElementById('terminal-output');
const sessionContextPanel = document.getElementById('session-context-panel');
const sessionContextTitle = document.getElementById('session-context-title');
const sessionContextMode = document.getElementById('session-context-mode');
const sessionContextSummary = document.getElementById('session-context-summary');
const sessionCustomerContainer = document.getElementById('session-customer-container');
const sessionRequestContainer = document.getElementById('session-request-container');
const sessionHiddenContextContainer = document.getElementById('session-hidden-context-container');
const sessionContextDetails = Array.from(document.querySelectorAll('.context-group'));
const PERSONA_HIDDEN_CONTEXT_FIELDS = [
    ['gender', '性别'],
    ['emotion', '当前情绪'],
    ['urgency', '紧急程度'],
    ['prior_attempts', '过往尝试'],
    ['special_constraints', '特殊约束'],
    ['current_call_contactable', '当前来电可联系'],
    ['contact_phone_owner', '联系电话归属'],
    ['contact_phone_owner_spoken_label', '联系电话口语表达'],
];

function appendTerminalLine(text, tone = 'system') {
    const line = document.createElement('div');
    line.className = `terminal-line ${tone}`;
    line.textContent = text;
    terminalOutput.appendChild(line);
    terminalScrollRegion.scrollTop = terminalScrollRegion.scrollHeight;
}

function clearElement(element) {
    if (element) element.innerHTML = '';
}

function appendContextItem(container, key, value) {
    if (!container) return;
    const item = document.createElement('div');
    item.className = 'context-item';

    const keyNode = document.createElement('span');
    keyNode.className = 'context-item-key';
    keyNode.textContent = key;

    const valueNode = document.createElement('span');
    valueNode.className = 'context-item-value';
    const normalized = value === null || value === undefined ? '' : String(value).trim();
    valueNode.textContent = normalized || '-';
    if (!normalized) valueNode.classList.add('is-empty');

    item.appendChild(keyNode);
    item.appendChild(valueNode);
    container.appendChild(item);
}

function appendSummaryChip(container, label, value) {
    if (!container) return;
    const chip = document.createElement('div');
    chip.className = 'context-summary-chip';
    chip.innerHTML = `<strong>${label}</strong><span>${value}</span>`;
    container.appendChild(chip);
}

function updateSessionContextDensity() {
    if (!sessionContextPanel || sessionContextPanel.classList.contains('hidden')) return;
    const hasOpenGroup = sessionContextDetails.some((detail) => detail.open);
    sessionContextPanel.classList.toggle('is-compact', !hasOpenGroup);
}

function updateSessionContext(scenario, sessionConfig = {}) {
    if (!scenario || !sessionConfig.auto_generate_hidden_settings) {
        sessionContextPanel.classList.add('hidden');
        sessionContextPanel.classList.remove('is-compact');
        sessionContextTitle.textContent = '本次会话设定';
        sessionContextMode.textContent = !scenario ? '未开始' : '未启用';
        clearElement(sessionContextSummary);
        clearElement(sessionCustomerContainer);
        clearElement(sessionRequestContainer);
        clearElement(sessionHiddenContextContainer);
        return;
    }

    sessionContextPanel.classList.remove('hidden');
    sessionContextTitle.textContent = `${scenario.scenario_id} 的会话设定`;
    sessionContextMode.textContent = sessionConfig.auto_generate_hidden_settings
        ? '已启用自动生成隐藏设定'
        : '使用原始/兜底设定';

    clearElement(sessionContextSummary);
    clearElement(sessionCustomerContainer);
    clearElement(sessionRequestContainer);
    clearElement(sessionHiddenContextContainer);

    const customer = scenario.customer || {};
    const request = scenario.request || {};
    const hiddenContext = scenario.hidden_context || {};

    appendSummaryChip(sessionContextSummary, '场景', scenario.scenario_id || '-');
    appendSummaryChip(sessionContextSummary, '诉求类型', request.request_type || '-');
    appendSummaryChip(
        sessionContextSummary,
        '已知地址',
        sessionConfig.known_address ? '前端指定核对地址' : '未指定',
    );

    [
        ['full_name', customer.full_name],
        ['surname', customer.surname],
        ['phone', customer.phone],
        ['address', customer.address],
        ['persona', customer.persona],
        ['speech_style', customer.speech_style],
    ].forEach(([key, value]) => appendContextItem(sessionCustomerContainer, key, value));

    [
        ['request_type', request.request_type],
        ['issue', request.issue],
        ['desired_resolution', request.desired_resolution],
        ['availability', request.availability],
    ].forEach(([key, value]) => appendContextItem(sessionRequestContainer, key, value));

    const visiblePersonaFields = PERSONA_HIDDEN_CONTEXT_FIELDS
        .map(([key, label]) => [label, hiddenContext[key]])
        .filter(([, value]) => {
            if (value === null || value === undefined) return false;
            if (typeof value === 'string') return value.trim() !== '';
            return true;
        });

    if (!visiblePersonaFields.length) {
        appendContextItem(sessionHiddenContextContainer, '人设信息', '');
        return;
    }

    visiblePersonaFields.forEach(([label, value]) => {
        const renderedValue = typeof value === 'string' ? value : JSON.stringify(value);
        appendContextItem(sessionHiddenContextContainer, label, renderedValue);
    });
    updateSessionContextDensity();
}

function renderTerminalEntries(entries = []) {
    terminalOutput.innerHTML = '';
    entries.forEach((entry) => {
        const line = document.createElement('div');
        line.className = `terminal-line ${entry.tone || 'system'}`;

        if (entry.entry_type === 'turn') {
            const contentText = `[${entry.round_label}] ${entry.speaker}: ${entry.text}`;
            const canRewind = entry.tone === 'user'
                && Boolean(currentSessionId)
                && !sessionBusy
                && !sessionReviewLocked
                && Number(entry.round_index) > 0;
            if (entry.tone === 'user') {
                const trigger = document.createElement('button');
                trigger.type = 'button';
                trigger.className = 'terminal-turn-trigger';
                trigger.textContent = contentText;
                trigger.title = '删除该用户行及其下方所有内容';
                trigger.dataset.roundIndex = String(entry.round_index || '');
                trigger.dataset.restoreCheckpointIndex = String(
                    Number.isFinite(Number(entry.restore_checkpoint_index))
                        ? Number(entry.restore_checkpoint_index)
                        : Math.max(Number(entry.round_index || 0) - 1, 0),
                );
                trigger.dataset.rewindEnabled = canRewind ? 'true' : 'false';
                trigger.classList.toggle('is-disabled', !canRewind);
                line.classList.add('rewindable');
                line.appendChild(trigger);
            } else {
                line.textContent = contentText;
            }
        } else {
            line.textContent = entry.text || '';
        }

        terminalOutput.appendChild(line);
    });
    terminalScrollRegion.scrollTop = terminalScrollRegion.scrollHeight;
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
    const canInteract = enabled
        && !sessionBusy
        && !reviewPending
        && !isReviewModalVisible()
        && Boolean(authenticatedUser)
        && !sessionReviewLocked;
    input.disabled = !canInteract;
    button.disabled = !canInteract;
    endButton.disabled = !currentSessionId || sessionClosed || !authenticatedUser || sessionBusy || sessionReviewLocked;
    if (canInteract) input.focus();
}

function isReviewModalVisible() {
    return !reviewModal.classList.contains('hidden');
}

function hideReviewModal() {
    reviewModal.classList.add('hidden');
    reviewModal.setAttribute('aria-hidden', 'true');
}

function showReviewModal() {
    reviewModal.classList.remove('hidden');
    reviewModal.setAttribute('aria-hidden', 'false');
}

function updateReviewToggleButton() {
    const shouldShow = reviewAvailable && !isReviewModalVisible();
    reviewToggleButton.classList.toggle('hidden', !shouldShow);
    reviewToggleButton.disabled = !shouldShow;
}

function setSessionBusyState(busy) {
    sessionBusy = busy;
    updateInputAvailability(!sessionClosed);
    renderTerminalEntries(sessionTerminalEntries);
}

function resetReviewState() {
    reviewPending = false;
    reviewAvailable = false;
    reviewContext = null;
    hideReviewModal();
    document.querySelectorAll('input[name="review-correctness"]').forEach((input) => {
        input.checked = false;
    });
    reviewErrorFields.classList.add('hidden');
    failedFlowStageSelect.innerHTML = '<option value="">请选择出错流程</option>';
    failedFlowStageSelect.value = '';
    reviewNotes.value = '';
    reviewSubmitButton.disabled = false;
    reviewCloseButton.disabled = false;
    updateReviewToggleButton();
}

function selectedCorrectnessValue() {
    return document.querySelector('input[name="review-correctness"]:checked')?.value || '';
}

function syncReviewErrorFields() {
    const isIncorrect = selectedCorrectnessValue() === 'incorrect';
    reviewErrorFields.classList.toggle('hidden', !isIncorrect);
}

function openReviewModal(data, { blocking = true } = {}) {
    if (!data.review_required || !currentSessionId) return;
    reviewPending = blocking;
    reviewAvailable = true;
    reviewContext = data;
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
    showReviewModal();
    syncReviewErrorFields();
    updateReviewToggleButton();
}

function prepareOptionalReview(data) {
    if (!data.review_required || !currentSessionId) return;
    reviewPending = false;
    reviewAvailable = true;
    reviewContext = data;
    updateReviewToggleButton();
}

function applySessionView(data) {
    if (!data || !data.session_id) return;

    currentSessionId = data.session_id;
    currentSlotKeys = Object.keys(data.collected_slots || {});
    sessionClosed = Boolean(data.session_closed);
    sessionTerminalEntries = Array.isArray(data.terminal_entries) ? data.terminal_entries : [];
    sessionReviewLocked = false;

    setSessionStatus(data.status || 'active');
    setSessionIdIndicator(data.session_id);
    setNextRound(data.next_round_index);
    updateScenarioHeader(data.scenario);
    updateSessionContext(data.scenario, data.session_config || {});
    updateInspector(data.collected_slots, data.runtime_state);
    renderTerminalEntries(sessionTerminalEntries);

    if (sessionClosed) {
        resetReviewState();
        if (data.status === 'transferred') {
            prepareOptionalReview(data);
        } else {
            openReviewModal(data);
        }
    } else {
        resetReviewState();
    }

    updateInputAvailability(!sessionClosed);
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
    sessionBusy = false;
    sessionReviewLocked = false;
    sessionTerminalEntries = [];
    resetReviewState();
    updateScenarioHeader(null);
    updateSessionContext(null, {});
    updateInspector({}, {});
    setSessionStatus('idle');
    setSessionIdIndicator('');
    setNextRound(1);
    updateInputAvailability(false);
    document.getElementById('scenario-list').innerHTML = '<div class="terminal-hint">登录后显示场景列表</div>';
    document.getElementById('terminal-output').innerHTML = '';
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
    setPasswordVisibility(false);
    loginPassword.value = '';
    setAuthError(message);
    resetWorkspace();
}

function setPasswordVisibility(visible) {
    loginPassword.type = visible ? 'text' : 'password';
    loginPasswordToggle.classList.toggle('is-visible', visible);
    loginPasswordToggleLabel.textContent = visible ? '隐藏' : '显示';
    loginPasswordToggle.setAttribute('aria-pressed', visible ? 'true' : 'false');
    loginPasswordToggle.setAttribute('aria-label', visible ? '隐藏密码' : '显示密码');
    loginPasswordToggle.title = visible ? '隐藏密码' : '显示密码';
}

function togglePasswordVisibility() {
    setPasswordVisibility(loginPassword.type === 'password');
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
        setPasswordVisibility(false);
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
    reviewCloseButton.disabled = true;
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
        sessionReviewLocked = true;
        resetReviewState();
        updateInputAvailability(false);
        renderTerminalEntries(sessionTerminalEntries);
    } catch (error) {
        reviewSubmitButton.disabled = false;
        reviewCloseButton.disabled = false;
        appendTerminalLine(`[系统错误] ${error.message}`, 'error');
    }
}

function dismissReview() {
    if (!reviewAvailable) {
        hideReviewModal();
        updateReviewToggleButton();
        return;
    }

    hideReviewModal();
    updateReviewToggleButton();
    appendTerminalLine(
        reviewPending
            ? '[系统] 已关闭评审窗口，可点击“打开评审”继续提交。'
            : '[系统] 已关闭评审窗口，如需提交可点击“打开评审”。',
        'system',
    );
}

function reopenReviewModal() {
    if (!reviewAvailable || !reviewContext) return;
    openReviewModal(reviewContext, { blocking: reviewPending });
}

async function startSession() {
    if (reviewPending) {
        appendTerminalLine('请先完成上一条测试记录的评审；如已关闭弹窗，可点击“打开评审”继续。', 'error');
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
    sessionBusy = true;
    updateInputAvailability(false);
    let errorMessage = '';

    try {
        const data = await apiFetch('/api/session/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        applySessionView(data);
    } catch (error) {
        currentSessionId = null;
        currentSlotKeys = [];
        sessionClosed = true;
        sessionTerminalEntries = [];
        sessionReviewLocked = false;
        resetReviewState();
        setSessionStatus('error');
        setSessionIdIndicator('');
        setNextRound(1);
        updateInspector({}, {});
        errorMessage = error.message;
    } finally {
        setSessionBusyState(false);
        if (errorMessage) {
            appendTerminalLine(`[系统错误] ${errorMessage}`, 'error');
        }
    }
}

async function forceEndSession() {
    if (!currentSessionId || sessionClosed) return;

    setSessionBusyState(true);
    let errorMessage = '';
    try {
        const data = await apiFetch('/api/session/respond', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: currentSessionId, text: '/quit' }),
        });
        applySessionView(data);
    } catch (error) {
        errorMessage = error.message;
    } finally {
        setSessionBusyState(false);
        if (errorMessage) {
            appendTerminalLine(`[系统错误] ${errorMessage}`, 'error');
        }
    }
}

async function sendMessage() {
    const input = document.getElementById('user-input');
    const rawText = input.value;
    const text = rawText.trim();
    if (!text || !currentSessionId || sessionClosed) return;

    input.value = '';
    setSessionBusyState(true);
    let errorMessage = '';
    try {
        const data = await apiFetch('/api/session/respond', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: currentSessionId, text: rawText }),
        });
        applySessionView(data);
    } catch (error) {
        errorMessage = error.message;
    } finally {
        setSessionBusyState(false);
        if (errorMessage) {
            appendTerminalLine(`[系统错误] ${errorMessage}`, 'error');
        }
    }
}

async function rewindFromUserRound(roundIndex, restoreCheckpointIndex) {
    if (!currentSessionId || sessionBusy || sessionReviewLocked || roundIndex < 1) return;

    setSessionBusyState(true);
    let errorMessage = '';
    try {
        const data = await apiFetch('/api/session/rewind', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                clicked_user_round_index: roundIndex,
                restore_checkpoint_index: restoreCheckpointIndex,
            }),
        });
        applySessionView(data);
    } catch (error) {
        errorMessage = error.message;
        if (errorMessage.includes('评审已提交')) {
            sessionReviewLocked = true;
        }
    } finally {
        setSessionBusyState(false);
        if (sessionReviewLocked) {
            renderTerminalEntries(sessionTerminalEntries);
            updateInputAvailability(false);
        }
        if (errorMessage) {
            appendTerminalLine(`[系统错误] ${errorMessage}`, 'error');
        }
    }
}

loginForm.addEventListener('submit', login);
loginPasswordToggle.addEventListener('click', togglePasswordVisibility);
document.getElementById('logout-btn').onclick = logout;
document.getElementById('start-session-btn').onclick = startSession;
document.getElementById('end-session-btn').onclick = forceEndSession;
document.getElementById('send-btn').onclick = sendMessage;
document.getElementById('review-submit-btn').onclick = submitReview;
document.getElementById('review-close-btn').onclick = dismissReview;
document.getElementById('review-toggle-btn').onclick = reopenReviewModal;
document.querySelectorAll('input[name="review-correctness"]').forEach((input) => {
    input.addEventListener('change', syncReviewErrorFields);
});
terminalOutput.addEventListener('click', (event) => {
    const button = event.target.closest('.terminal-turn-trigger');
    if (!button) return;
    event.preventDefault();
    if (button.dataset.rewindEnabled !== 'true') return;
    const roundIndex = Number(button.dataset.roundIndex || '0');
    const restoreCheckpointIndex = Number(button.dataset.restoreCheckpointIndex || '-1');
    if (!roundIndex) return;
    rewindFromUserRound(roundIndex, restoreCheckpointIndex);
});

sessionContextDetails.forEach((detail) => {
    detail.addEventListener('toggle', updateSessionContextDensity);
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
setPasswordVisibility(false);
checkAuth();

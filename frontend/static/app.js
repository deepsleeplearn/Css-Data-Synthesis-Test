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
let sessionStartedAt = '';
let sessionEndedAt = '';
let sessionTimerInterval = null;
let autoKnownAddressValue = '';
let autoCallStartTimeValue = '';
let faultIssueReferenceCategories = null;
let magnifierPressTimer = null;
let magnifierPointerId = null;
let magnifierActive = false;
let magnifierStartPoint = null;
let magnifierLastPoint = null;
let magnifierCloneNode = null;
let magnifierSuppressClickUntil = 0;
let cursorTrailAnimationId = null;
let cursorTrailVisible = false;
let cursorTrailTarget = { x: -320, y: -320 };
let cursorTrailPosition = { x: -320, y: -320 };
let cursorTrailInitialized = false;
let cursorTrailPoints = [];
let cursorTrailLastTimestamp = 0;
let sessionIdCopyFeedbackTimer = null;
let chatMessages = [];
let chatLatestMessageId = 0;
let chatPollTimer = null;
let chatPollInFlight = false;
let chatUnreadCount = 0;
let chatStateInitialized = false;
let chatSnapshotRevision = 0;
let chatStoragePath = '';
let chatWindowState = null;
let chatDragState = null;
let chatResizeObserver = null;
let chatOnlineUserCount = 0;
let chatOnlineUsersCache = [];
let chatOnlineDrawerOpen = false;
let chatOnlineDrawerPosition = null;
let chatAdminEnabled = false;
let chatMentionState = null;
let chatMentionOptions = [];
let chatMentionActiveIndex = 0;
let chatMentionAlertActive = false;
let chatLauncherDragState = null;
let chatLauncherSuppressClickUntil = 0;
let chatLatestSelfMessageId = 0;
let chatReadReceiptOpenMessageId = 0;
let chatReadReceiptMembers = [];
let chatMessageHoldTimer = null;
let chatMessageHoldPointerId = null;
let chatMessageHoldStartPoint = null;
let chatMessageHoldMessageId = 0;
let chatContextMenuMessageId = 0;
let sessionInputHistory = [];
let sessionInputHistoryIndex = -1;
let sessionInputDraft = '';
let terminalTurnMenuState = null;

const authGate = document.getElementById('auth-gate');
const appShell = document.getElementById('app-shell');
const authError = document.getElementById('auth-error');
const loginForm = document.getElementById('login-form');
const loginUsername = document.getElementById('login-username');
const loginPassword = document.getElementById('login-password');
const loginPasswordToggle = document.getElementById('login-password-toggle');
const loginPasswordToggleLabel = document.getElementById('login-password-toggle-label');
const loginButton = document.getElementById('login-btn');
const startSessionButton = document.getElementById('start-session-btn');
const authUserName = document.getElementById('auth-user-name');
const authUserMeta = document.getElementById('auth-user-meta');
const knownAddressInput = document.getElementById('known-address');
const generateKnownAddressButton = document.getElementById('generate-known-address-btn');
const clearKnownAddressButton = document.getElementById('clear-known-address-btn');
const callStartTimeInput = document.getElementById('call-start-time');
const generateCallStartTimeButton = document.getElementById('generate-call-start-time-btn');
const callStartTimeError = document.getElementById('call-start-time-error');
const useSessionStartTimeCheckbox = document.getElementById('use-session-start-time');
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
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-btn');
const addressSlotsContainer = document.getElementById('address-slots-container');
const sessionContextPanel = document.getElementById('session-context-panel');
const sessionContextTitle = document.getElementById('session-context-title');
const sessionContextMode = document.getElementById('session-context-mode');
const sessionContextSummary = document.getElementById('session-context-summary');
const sessionCustomerContainer = document.getElementById('session-customer-container');
const sessionRequestContainer = document.getElementById('session-request-container');
const sessionHiddenContextContainer = document.getElementById('session-hidden-context-container');
const sessionContextDetails = Array.from(document.querySelectorAll('.context-group'));
const sessionTimerPanel = document.getElementById('session-timer-panel');
const sessionStartedAtNode = document.getElementById('session-started-at');
const sessionElapsedTimeNode = document.getElementById('session-elapsed-time');
const sessionEndedAtNode = document.getElementById('session-ended-at');
const sessionIdCopyButton = document.getElementById('session-id-copy-btn');
const issueReferencePopover = document.getElementById('issue-reference-popover');
const issueReferenceList = document.getElementById('issue-reference-list');
const issueReferenceCloseButton = document.getElementById('issue-reference-close-btn');
const cursorTrailCanvas = document.getElementById('cursor-trail-canvas');
const cursorTrailContext = cursorTrailCanvas?.getContext('2d');
const textMagnifier = document.getElementById('text-magnifier');
const textMagnifierViewport = document.getElementById('text-magnifier-viewport');
const chatLauncher = document.getElementById('chat-launcher');
const chatLauncherOnline = document.getElementById('chat-launcher-online');
const chatLauncherUnread = document.getElementById('chat-launcher-unread');
const chatMentionDropdown = document.getElementById('chat-mention-dropdown');
const chatMessageMenu = document.getElementById('chat-message-menu');
const chatRecallButton = document.getElementById('chat-recall-btn');
const terminalTurnMenu = document.getElementById('terminal-turn-menu');
const terminalToggleAddressIeButton = document.getElementById('terminal-toggle-address-ie-btn');
const chatWindow = document.getElementById('chat-window');
const chatWindowHeader = document.getElementById('chat-window-header');
const chatHideButton = document.getElementById('chat-hide-btn');
const chatOnlineCount = document.getElementById('chat-online-count');
const chatOnlinePreview = document.getElementById('chat-online-preview');
const chatOnlineUsers = document.getElementById('chat-online-users');
const chatStorageStatus = document.getElementById('chat-storage-status');
const chatAdminControls = document.getElementById('chat-admin-controls');
const chatClearHistoryCheckbox = document.getElementById('chat-clear-history-checkbox');
const chatClearHistoryButton = document.getElementById('chat-clear-history-btn');
const chatAdminStatus = document.getElementById('chat-admin-status');
const chatMessageList = document.getElementById('chat-message-list');
const chatInput = document.getElementById('chat-input');
const chatSendButton = document.getElementById('chat-send-btn');
const chatSendStatus = document.getElementById('chat-send-status');
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
const ADDRESS_SLOT_FIELDS = [
    ['address_slot_province', '省'],
    ['address_slot_city', '市'],
    ['address_slot_district', '区/县'],
    ['address_slot_town', '街道/乡镇'],
    ['address_slot_road', '道路'],
    ['address_slot_community', '小区/社区/学校/医院/酒店'],
    ['address_slot_landmark', '补充定位点'],
    ['address_slot_building', '楼栋'],
    ['address_slot_unit', '单元'],
    ['address_slot_floor', '楼层'],
    ['address_slot_room', '房间'],
];

const ISSUE_REFERENCE_TRIGGER_PATTERN = /请问.*空气能.*现在是出现了什么问题/;
const MAGNIFIER_LONG_PRESS_MS = 350;
const MAGNIFIER_MOVE_TOLERANCE = 10;
const MAGNIFIER_SCALE = 1.75;
const MAGNIFIER_OFFSET = 24;
const CURSOR_TRAIL_EASE = 0.16;
const CURSOR_TRAIL_SETTLE_DISTANCE = 0.8;
const CURSOR_TRAIL_POINT_SPACING = 5;
const CURSOR_TRAIL_MAX_POINTS = 24;
const CHAT_POLL_INTERVAL_MS = 4000;
const CHAT_WINDOW_STORAGE_KEY = 'frontend-chat-window-preferences';
const CHAT_MIN_WIDTH = 320;
const CHAT_MIN_HEIGHT = 352;
const CHAT_VIEWPORT_MARGIN = 12;
const CHAT_UNREAD_CAP = 99;
const CHAT_MESSAGE_HOLD_MS = 420;
const CHAT_MESSAGE_HOLD_MOVE_TOLERANCE = 10;
const CHAT_MENTION_OPTION_LIMIT = 12;
const SESSION_INPUT_HISTORY_LIMIT = 50;
const DEFAULT_DOCUMENT_TITLE = document.title;
const CHAT_FAVICON_SIZE = 64;

function formatDisplayTimestamp(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hour = String(date.getHours()).padStart(2, '0');
    const minute = String(date.getMinutes()).padStart(2, '0');
    const second = String(date.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
}

function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
}

function safeLocalStorageGet(key) {
    try {
        return window.localStorage.getItem(key);
    } catch (error) {
        return null;
    }
}

function safeLocalStorageSet(key, value) {
    try {
        window.localStorage.setItem(key, value);
    } catch (error) {
        // Ignore localStorage failures such as private mode restrictions.
    }
}

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function loadChatWindowState() {
    const fallback = { visible: true, width: 384, height: 544, left: null, top: null, launcher_left: null, launcher_top: null };
    const raw = safeLocalStorageGet(CHAT_WINDOW_STORAGE_KEY);
    if (!raw) return fallback;
    try {
        const parsed = JSON.parse(raw);
        return {
            visible: parsed.visible !== false,
            width: Number(parsed.width) || fallback.width,
            height: Number(parsed.height) || fallback.height,
            left: Number.isFinite(Number(parsed.left)) ? Number(parsed.left) : null,
            top: Number.isFinite(Number(parsed.top)) ? Number(parsed.top) : null,
            launcher_left: Number.isFinite(Number(parsed.launcher_left)) ? Number(parsed.launcher_left) : null,
            launcher_top: Number.isFinite(Number(parsed.launcher_top)) ? Number(parsed.launcher_top) : null,
        };
    } catch (error) {
        return fallback;
    }
}

function persistChatWindowState() {
    if (!chatWindowState) return;
    safeLocalStorageSet(CHAT_WINDOW_STORAGE_KEY, JSON.stringify(chatWindowState));
}

function clearChatMentionDropdown() {
    chatMentionState = null;
    chatMentionOptions = [];
    chatMentionActiveIndex = 0;
    chatMentionDropdown.innerHTML = '';
    chatMentionDropdown.classList.add('hidden');
    chatMentionDropdown.setAttribute('aria-hidden', 'true');
}

function getChatViewportBounds() {
    return {
        width: Math.max(window.innerWidth, CHAT_MIN_WIDTH + (CHAT_VIEWPORT_MARGIN * 2)),
        height: Math.max(window.innerHeight, CHAT_MIN_HEIGHT + (CHAT_VIEWPORT_MARGIN * 2)),
    };
}

function resolveChatWindowRect() {
    const bounds = getChatViewportBounds();
    const maxWidth = Math.max(bounds.width - (CHAT_VIEWPORT_MARGIN * 2), CHAT_MIN_WIDTH);
    const maxHeight = Math.max(bounds.height - (CHAT_VIEWPORT_MARGIN * 2), CHAT_MIN_HEIGHT);
    const width = clamp(Number(chatWindowState?.width) || 384, CHAT_MIN_WIDTH, maxWidth);
    const height = clamp(Number(chatWindowState?.height) || 544, CHAT_MIN_HEIGHT, maxHeight);
    const defaultLeft = bounds.width - width - 24;
    const defaultTop = Math.max(84, bounds.height - height - 24);
    const maxLeft = Math.max(CHAT_VIEWPORT_MARGIN, bounds.width - width - CHAT_VIEWPORT_MARGIN);
    const maxTop = Math.max(CHAT_VIEWPORT_MARGIN, bounds.height - height - CHAT_VIEWPORT_MARGIN);
    const left = clamp(
        Number.isFinite(chatWindowState?.left) ? Number(chatWindowState.left) : defaultLeft,
        CHAT_VIEWPORT_MARGIN,
        maxLeft,
    );
    const top = clamp(
        Number.isFinite(chatWindowState?.top) ? Number(chatWindowState.top) : defaultTop,
        CHAT_VIEWPORT_MARGIN,
        maxTop,
    );
    return { width, height, left, top };
}

function applyChatWindowRect() {
    if (!chatWindow || !chatWindowState) return;
    const rect = resolveChatWindowRect();
    chatWindow.style.width = `${rect.width}px`;
    chatWindow.style.height = `${rect.height}px`;
    chatWindow.style.left = `${rect.left}px`;
    chatWindow.style.top = `${rect.top}px`;
    chatWindowState = { ...chatWindowState, ...rect };
}

function syncChatWindowStateFromDom() {
    if (!chatWindow || !chatWindowState) return;
    const bounds = getChatViewportBounds();
    const width = clamp(chatWindow.offsetWidth || chatWindowState.width, CHAT_MIN_WIDTH, bounds.width - (CHAT_VIEWPORT_MARGIN * 2));
    const height = clamp(chatWindow.offsetHeight || chatWindowState.height, CHAT_MIN_HEIGHT, bounds.height - (CHAT_VIEWPORT_MARGIN * 2));
    const maxLeft = Math.max(CHAT_VIEWPORT_MARGIN, bounds.width - width - CHAT_VIEWPORT_MARGIN);
    const maxTop = Math.max(CHAT_VIEWPORT_MARGIN, bounds.height - height - CHAT_VIEWPORT_MARGIN);
    const left = clamp(parseFloat(chatWindow.style.left) || 0, CHAT_VIEWPORT_MARGIN, maxLeft);
    const top = clamp(parseFloat(chatWindow.style.top) || 0, CHAT_VIEWPORT_MARGIN, maxTop);
    chatWindowState = {
        ...chatWindowState,
        width,
        height,
        left,
        top,
    };
    chatWindow.style.width = `${width}px`;
    chatWindow.style.height = `${height}px`;
    chatWindow.style.left = `${left}px`;
    chatWindow.style.top = `${top}px`;
}

function updateChatLauncher() {
    const authenticated = Boolean(authenticatedUser);
    const visible = authenticated && chatWindowState?.visible !== false;
    chatLauncher.classList.toggle('hidden', !authenticated || visible);
    chatLauncher.setAttribute('aria-expanded', visible ? 'true' : 'false');
    chatLauncher.classList.toggle('is-mention-alert', !visible && chatMentionAlertActive);
    chatLauncherOnline.textContent = `${chatOnlineUserCount} 人在线`;
    chatLauncherUnread.textContent = chatUnreadCount > CHAT_UNREAD_CAP ? '99+' : String(chatUnreadCount);
    chatLauncherUnread.classList.toggle('hidden', chatUnreadCount < 1);
    updateChatPageIndicator();
}

function ensureChatFaviconLink() {
    const existing = document.querySelector('link[rel~="icon"]');
    if (existing instanceof HTMLLinkElement) {
        return existing;
    }
    const link = document.createElement('link');
    link.rel = 'icon';
    link.type = 'image/png';
    document.head.appendChild(link);
    return link;
}

function drawRoundedRect(context, x, y, width, height, radius) {
    const normalizedRadius = Math.max(0, Math.min(Number(radius || 0), width / 2, height / 2));
    context.beginPath();
    context.moveTo(x + normalizedRadius, y);
    context.lineTo(x + width - normalizedRadius, y);
    context.quadraticCurveTo(x + width, y, x + width, y + normalizedRadius);
    context.lineTo(x + width, y + height - normalizedRadius);
    context.quadraticCurveTo(x + width, y + height, x + width - normalizedRadius, y + height);
    context.lineTo(x + normalizedRadius, y + height);
    context.quadraticCurveTo(x, y + height, x, y + height - normalizedRadius);
    context.lineTo(x, y + normalizedRadius);
    context.quadraticCurveTo(x, y, x + normalizedRadius, y);
    context.closePath();
}

function buildChatFaviconDataUrl(unreadCount = 0) {
    const canvas = document.createElement('canvas');
    canvas.width = CHAT_FAVICON_SIZE;
    canvas.height = CHAT_FAVICON_SIZE;
    const context = canvas.getContext('2d');
    if (!context) return '';

    context.clearRect(0, 0, CHAT_FAVICON_SIZE, CHAT_FAVICON_SIZE);

    context.fillStyle = '#14324b';
    drawRoundedRect(context, 4, 4, CHAT_FAVICON_SIZE - 8, CHAT_FAVICON_SIZE - 8, 16);
    context.fill();

    context.fillStyle = '#2a7fff';
    drawRoundedRect(context, 10, 10, CHAT_FAVICON_SIZE - 20, CHAT_FAVICON_SIZE - 20, 12);
    context.fill();

    context.fillStyle = '#f4f7fb';
    context.font = 'bold 28px sans-serif';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText('群', CHAT_FAVICON_SIZE / 2, CHAT_FAVICON_SIZE / 2);

    if (unreadCount > 0) {
        const badgeText = unreadCount > CHAT_UNREAD_CAP ? '99+' : String(unreadCount);
        const badgeRadius = badgeText.length > 2 ? 18 : 16;
        const badgeCenterX = CHAT_FAVICON_SIZE - badgeRadius - 2;
        const badgeCenterY = badgeRadius + 2;

        context.fillStyle = '#ef4444';
        context.beginPath();
        context.arc(badgeCenterX, badgeCenterY, badgeRadius, 0, Math.PI * 2);
        context.fill();

        context.fillStyle = '#ffffff';
        context.font = `bold ${badgeText.length > 2 ? 15 : 18}px sans-serif`;
        context.textAlign = 'center';
        context.textBaseline = 'middle';
        context.fillText(badgeText, badgeCenterX, badgeCenterY + 1);
    }

    return canvas.toDataURL('image/png');
}

function updateChatPageIndicator() {
    const unreadCount = Math.max(Number(chatUnreadCount || 0), 0);
    const titlePrefix = unreadCount > 0
        ? `(${unreadCount > CHAT_UNREAD_CAP ? '99+' : unreadCount}) `
        : '';
    const titleLabel = chatMentionAlertActive ? '群聊有人@你' : '群聊新消息';
    document.title = unreadCount > 0
        ? `${titlePrefix}${titleLabel} - ${DEFAULT_DOCUMENT_TITLE}`
        : DEFAULT_DOCUMENT_TITLE;

    const faviconLink = ensureChatFaviconLink();
    const faviconUrl = buildChatFaviconDataUrl(unreadCount);
    if (faviconLink && faviconUrl) {
        faviconLink.href = faviconUrl;
    }
}

function resolveChatLauncherRect() {
    const bounds = getChatViewportBounds();
    const launcherWidth = Math.max(chatLauncher.offsetWidth || 172, 120);
    const launcherHeight = Math.max(chatLauncher.offsetHeight || 50, 40);
    const maxLeft = Math.max(CHAT_VIEWPORT_MARGIN, bounds.width - launcherWidth - CHAT_VIEWPORT_MARGIN);
    const maxTop = Math.max(CHAT_VIEWPORT_MARGIN, bounds.height - launcherHeight - CHAT_VIEWPORT_MARGIN);
    const hasStoredPosition = Number.isFinite(chatWindowState?.launcher_left) && Number.isFinite(chatWindowState?.launcher_top);
    const left = hasStoredPosition
        ? clamp(Number(chatWindowState.launcher_left), CHAT_VIEWPORT_MARGIN, maxLeft)
        : null;
    const top = hasStoredPosition
        ? clamp(Number(chatWindowState.launcher_top), CHAT_VIEWPORT_MARGIN, maxTop)
        : null;
    return { left, top };
}

function applyChatLauncherRect() {
    if (!chatLauncher || chatLauncher.classList.contains('hidden')) return;
    const rect = resolveChatLauncherRect();
    if (rect.left === null || rect.top === null) {
        chatLauncher.style.left = '';
        chatLauncher.style.top = '';
        chatLauncher.style.right = '';
        chatLauncher.style.bottom = '';
        return;
    }
    chatLauncher.style.left = `${rect.left}px`;
    chatLauncher.style.top = `${rect.top}px`;
    chatLauncher.style.right = 'auto';
    chatLauncher.style.bottom = 'auto';
    chatWindowState.launcher_left = rect.left;
    chatWindowState.launcher_top = rect.top;
}

function syncChatLauncherStateFromDom() {
    if (!chatLauncher || chatLauncher.classList.contains('hidden') || !chatWindowState) return;
    const bounds = getChatViewportBounds();
    const width = Math.max(chatLauncher.offsetWidth || 172, 120);
    const height = Math.max(chatLauncher.offsetHeight || 50, 40);
    const maxLeft = Math.max(CHAT_VIEWPORT_MARGIN, bounds.width - width - CHAT_VIEWPORT_MARGIN);
    const maxTop = Math.max(CHAT_VIEWPORT_MARGIN, bounds.height - height - CHAT_VIEWPORT_MARGIN);
    chatWindowState.launcher_left = clamp(parseFloat(chatLauncher.style.left) || 0, CHAT_VIEWPORT_MARGIN, maxLeft);
    chatWindowState.launcher_top = clamp(parseFloat(chatLauncher.style.top) || 0, CHAT_VIEWPORT_MARGIN, maxTop);
    chatLauncher.style.left = `${chatWindowState.launcher_left}px`;
    chatLauncher.style.top = `${chatWindowState.launcher_top}px`;
}

function setChatWindowVisibility(visible, { persist = true, scrollToBottom = false } = {}) {
    if (!chatWindowState) {
        chatWindowState = loadChatWindowState();
    }
    chatWindowState.visible = Boolean(visible);
    const shouldShow = Boolean(authenticatedUser) && Boolean(visible);
    chatWindow.classList.toggle('hidden', !shouldShow);
    chatWindow.setAttribute('aria-hidden', shouldShow ? 'false' : 'true');
    if (shouldShow) {
        applyChatWindowRect();
        if (scrollToBottom) {
            window.requestAnimationFrame(() => {
                chatMessageList.scrollTop = chatMessageList.scrollHeight;
            });
        }
        chatUnreadCount = 0;
        chatMentionAlertActive = false;
        clearChatMentionDropdown();
    } else {
        setChatOnlineDrawerOpen(false);
    }
    if (persist) persistChatWindowState();
    updateChatLauncher();
    if (!shouldShow) {
        window.requestAnimationFrame(() => {
            applyChatLauncherRect();
        });
    }
    if (authenticatedUser) {
        refreshChatState({ forceScroll: shouldShow }).catch(() => {});
    }
}

function resizeCursorTrailCanvas() {
    if (!cursorTrailCanvas || !cursorTrailContext) return;
    const dpr = window.devicePixelRatio || 1;
    const width = Math.max(Math.floor(window.innerWidth * dpr), 1);
    const height = Math.max(Math.floor(window.innerHeight * dpr), 1);
    if (cursorTrailCanvas.width === width && cursorTrailCanvas.height === height) return;
    cursorTrailCanvas.width = width;
    cursorTrailCanvas.height = height;
    cursorTrailContext.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function ensureCursorTrailAnimation() {
    if (cursorTrailAnimationId !== null || !cursorTrailContext) return;
    cursorTrailAnimationId = window.requestAnimationFrame(renderCursorTrailFrame);
}

function drawCursorTrail(now) {
    if (!cursorTrailContext || !cursorTrailCanvas) return;
    resizeCursorTrailCanvas();
    cursorTrailContext.clearRect(0, 0, window.innerWidth, window.innerHeight);
    if (cursorTrailPoints.length < 2) return;

    cursorTrailContext.lineCap = 'round';
    cursorTrailContext.lineJoin = 'round';

    for (let index = 1; index < cursorTrailPoints.length; index += 1) {
        const previous = cursorTrailPoints[index - 1];
        const current = cursorTrailPoints[index];
        const progress = index / (cursorTrailPoints.length - 1);
        const alphaBase = (1 - progress) * current.life;
        if (alphaBase <= 0.02) continue;

        const palettes = [
            { width: 4.2, alpha: 0.42, hueShift: 0 },
            { width: 2.4, alpha: 0.72, hueShift: 52 },
            { width: 1.2, alpha: 0.96, hueShift: 124 },
        ];

        palettes.forEach((palette, layerIndex) => {
            const hue = (now * 0.05 + current.hue + palette.hueShift + (index * 9)) % 360;
            cursorTrailContext.strokeStyle = `hsla(${hue}, 98%, ${layerIndex === 2 ? 78 : 68}%, ${alphaBase * palette.alpha})`;
            cursorTrailContext.lineWidth = palette.width * (1 - (progress * 0.45));
            cursorTrailContext.beginPath();
            cursorTrailContext.moveTo(previous.x, previous.y);
            cursorTrailContext.lineTo(current.x, current.y);
            cursorTrailContext.stroke();
        });
    }
}

function renderCursorTrailFrame(timestamp) {
    cursorTrailAnimationId = null;
    const delta = cursorTrailLastTimestamp ? Math.min(timestamp - cursorTrailLastTimestamp, 32) : 16;
    cursorTrailLastTimestamp = timestamp;

    const moveAxis = (current, target) => current + ((target - current) * CURSOR_TRAIL_EASE);
    cursorTrailPosition = {
        x: moveAxis(cursorTrailPosition.x, cursorTrailTarget.x),
        y: moveAxis(cursorTrailPosition.y, cursorTrailTarget.y),
    };

    const lastPoint = cursorTrailPoints[cursorTrailPoints.length - 1];
    if (
        cursorTrailVisible
        && (!lastPoint || Math.hypot(cursorTrailPosition.x - lastPoint.x, cursorTrailPosition.y - lastPoint.y) >= CURSOR_TRAIL_POINT_SPACING)
    ) {
        cursorTrailPoints.push({
            x: cursorTrailPosition.x,
            y: cursorTrailPosition.y,
            life: 1,
            hue: (timestamp * 0.03) % 360,
        });
    }

    const decay = cursorTrailVisible ? 0.045 : 0.09;
    cursorTrailPoints = cursorTrailPoints
        .map((point) => ({ ...point, life: point.life - (decay * (delta / 16)) }))
        .filter((point) => point.life > 0.02)
        .slice(-CURSOR_TRAIL_MAX_POINTS);

    drawCursorTrail(timestamp);

    const distance = Math.hypot(
        cursorTrailTarget.x - cursorTrailPosition.x,
        cursorTrailTarget.y - cursorTrailPosition.y,
    );
    if (cursorTrailVisible || cursorTrailPoints.length > 0 || distance > CURSOR_TRAIL_SETTLE_DISTANCE) {
        ensureCursorTrailAnimation();
    }
}

function updateCursorGlow(event) {
    cursorTrailTarget = { x: event.clientX, y: event.clientY };
    if (!cursorTrailInitialized) {
        cursorTrailPosition = { ...cursorTrailTarget };
        cursorTrailInitialized = true;
    }
    cursorTrailVisible = true;
    ensureCursorTrailAnimation();
}

function hideCursorGlow() {
    cursorTrailVisible = false;
    ensureCursorTrailAnimation();
}

function generateMockCallStartTime() {
    const base = new Date();
    const offsetDays = Math.floor(Math.random() * 14);
    base.setDate(base.getDate() - offsetDays);
    base.setHours(
        Math.floor(Math.random() * 24),
        Math.floor(Math.random() * 60),
        Math.floor(Math.random() * 60),
        0,
    );
    return formatDisplayTimestamp(base);
}

function appendTerminalLine(text, tone = 'system') {
    const normalizedText = String(text || '');
    if (currentSessionId) {
        sessionTerminalEntries.push({
            entry_type: 'message',
            tone,
            text: normalizedText,
        });
        renderTerminalEntries(sessionTerminalEntries);
        return;
    }
    const line = document.createElement('div');
    line.className = `terminal-line ${tone}`;
    line.textContent = normalizedText;
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

function shouldOfferIssueReference(entry) {
    if (!entry || entry.entry_type !== 'turn') return false;
    if (entry.tone !== 'service') return false;
    return ISSUE_REFERENCE_TRIGGER_PATTERN.test(String(entry.text || '').trim());
}

async function loadFaultIssueReferenceCategories() {
    if (Array.isArray(faultIssueReferenceCategories)) return faultIssueReferenceCategories;
    const data = await apiFetch('/api/reference/fault-issue-categories');
    faultIssueReferenceCategories = Array.isArray(data.categories) ? data.categories : [];
    return faultIssueReferenceCategories;
}

function hideIssueReferencePopover() {
    issueReferencePopover.classList.add('hidden');
    issueReferencePopover.setAttribute('aria-hidden', 'true');
    issueReferencePopover.style.left = '';
    issueReferencePopover.style.top = '';
}

function closeTerminalTurnMenu() {
    terminalTurnMenuState = null;
    terminalTurnMenu.classList.add('hidden');
    terminalTurnMenu.setAttribute('aria-hidden', 'true');
    terminalTurnMenu.style.left = '';
    terminalTurnMenu.style.top = '';
}

function openTerminalTurnMenu({ roundIndex, hasAddressIeDisplay, clientX, clientY }) {
    if (!terminalTurnMenu || !terminalToggleAddressIeButton) return;
    terminalTurnMenuState = {
        roundIndex: Number(roundIndex || 0),
        hasAddressIeDisplay: Boolean(hasAddressIeDisplay),
    };
    terminalToggleAddressIeButton.textContent = hasAddressIeDisplay
        ? '移除 function_call 与 observation'
        : '插入 function_call 与 observation';
    terminalTurnMenu.style.left = `${Math.max(16, Math.min(clientX, window.innerWidth - 252))}px`;
    terminalTurnMenu.style.top = `${Math.max(16, Math.min(clientY, window.innerHeight - 72))}px`;
    terminalTurnMenu.classList.remove('hidden');
    terminalTurnMenu.setAttribute('aria-hidden', 'false');
}

function handleDocumentScroll(event) {
    const scrollTarget = event.target;
    if (scrollTarget instanceof Element && scrollTarget.closest('#issue-reference-popover')) {
        return;
    }
    hideIssueReferencePopover();
    closeTerminalTurnMenu();
    if (magnifierActive && magnifierLastPoint) {
        syncTextMagnifierClone(magnifierLastPoint.x, magnifierLastPoint.y);
    }
}

function renderIssueReferenceList(categories) {
    issueReferenceList.innerHTML = '';
    categories.forEach((category) => {
        const item = document.createElement('div');
        item.className = 'issue-reference-item';
        item.textContent = category;
        issueReferenceList.appendChild(item);
    });
}

async function openIssueReferencePopover(anchorElement) {
    try {
        const categories = await loadFaultIssueReferenceCategories();
        renderIssueReferenceList(categories);
        const rect = anchorElement.getBoundingClientRect();
        const estimatedWidth = Math.min(352, window.innerWidth - 32);
        const desiredLeft = Math.min(rect.right + 12, window.innerWidth - estimatedWidth - 16);
        const top = Math.min(rect.top, window.innerHeight - 320);
        issueReferencePopover.style.left = `${Math.max(16, desiredLeft)}px`;
        issueReferencePopover.style.top = `${Math.max(16, top)}px`;
        issueReferencePopover.classList.remove('hidden');
        issueReferencePopover.setAttribute('aria-hidden', 'false');
    } catch (error) {
        appendTerminalLine(`[系统错误] 加载报修问题参考失败：${error.message}`, 'error');
    }
}

function parseDisplayTimestamp(value) {
    const normalized = String(value || '').trim();
    if (!normalized) return null;
    const match = normalized.match(
        /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})$/,
    );
    if (!match) return null;
    const [, year, month, day, hour, minute, second] = match;
    return new Date(
        Number(year),
        Number(month) - 1,
        Number(day),
        Number(hour),
        Number(minute),
        Number(second),
    );
}

function prefillMockCallStartTime(force = false) {
    const currentValue = callStartTimeInput.value.trim();
    if (!force && currentValue && currentValue !== autoCallStartTimeValue) return;
    autoCallStartTimeValue = generateMockCallStartTime();
    callStartTimeInput.value = autoCallStartTimeValue;
}

function isCallStartTimeValid() {
    if (useSessionStartTimeCheckbox.checked) return true;
    return Boolean(parseDisplayTimestamp(callStartTimeInput.value.trim()));
}

function updateCallStartTimeValidationState() {
    const valid = isCallStartTimeValid();
    const useSessionTime = useSessionStartTimeCheckbox.checked;
    callStartTimeInput.disabled = useSessionTime;
    callStartTimeError.classList.toggle('hidden', valid);
    return valid;
}

function updateStartSessionButtonState() {
    const canStart = Boolean(authenticatedUser)
        && Boolean(selectedScenario)
        && !sessionBusy
        && !reviewPending
        && !isReviewModalVisible()
        && isCallStartTimeValid();
    startSessionButton.disabled = !canStart;
}

function sanitizeCloneElementIds(root) {
    if (!root) return;
    if (root.id) root.removeAttribute('id');
    root.querySelectorAll('[id]').forEach((element) => element.removeAttribute('id'));
}

function syncCloneScrollState(sourceRoot, cloneRoot) {
    if (!sourceRoot || !cloneRoot) return;
    const sourceElements = [sourceRoot, ...sourceRoot.querySelectorAll('*')];
    const cloneElements = [cloneRoot, ...cloneRoot.querySelectorAll('*')];
    const total = Math.min(sourceElements.length, cloneElements.length);
    for (let index = 0; index < total; index += 1) {
        cloneElements[index].scrollTop = sourceElements[index].scrollTop;
        cloneElements[index].scrollLeft = sourceElements[index].scrollLeft;
    }
}

function removeNodesFromClone(root, selectors) {
    if (!root) return;
    selectors.forEach((selector) => {
        root.querySelectorAll(selector).forEach((node) => node.remove());
    });
}

function clearMagnifierPressTimer() {
    if (magnifierPressTimer !== null) {
        window.clearTimeout(magnifierPressTimer);
        magnifierPressTimer = null;
    }
}

function teardownTextMagnifierClone() {
    if (magnifierCloneNode && magnifierCloneNode.parentNode === textMagnifierViewport) {
        textMagnifierViewport.removeChild(magnifierCloneNode);
    }
    magnifierCloneNode = null;
}

function hideTextMagnifier() {
    clearMagnifierPressTimer();
    if (magnifierActive) {
        magnifierSuppressClickUntil = Date.now() + 400;
    }
    magnifierActive = false;
    magnifierPointerId = null;
    magnifierStartPoint = null;
    magnifierLastPoint = null;
    textMagnifier.classList.add('hidden');
    textMagnifier.setAttribute('aria-hidden', 'true');
    teardownTextMagnifierClone();
}

function syncTextMagnifierClone(clientX, clientY) {
    if (!magnifierCloneNode) return;
    const sourceRect = {
        left: 0,
        top: 0,
        width: window.innerWidth,
        height: window.innerHeight,
    };
    const viewportRect = textMagnifierViewport.getBoundingClientRect();
    const visibleX = Math.min(Math.max(clientX - sourceRect.left, 0), sourceRect.width);
    const visibleY = Math.min(Math.max(clientY - sourceRect.top, 0), sourceRect.height);
    syncCloneScrollState(document.body, magnifierCloneNode);
    const translateX = (viewportRect.width / 2) - (visibleX * MAGNIFIER_SCALE);
    const translateY = (viewportRect.height / 2) - (visibleY * MAGNIFIER_SCALE);
    magnifierCloneNode.style.transform = `translate(${translateX}px, ${translateY}px) scale(${MAGNIFIER_SCALE})`;
}

function positionTextMagnifier(clientX, clientY) {
    const lensRect = textMagnifier.getBoundingClientRect();
    const maxLeft = Math.max(window.innerWidth - lensRect.width - 12, 12);
    const maxTop = Math.max(window.innerHeight - lensRect.height - 12, 12);
    const desiredLeft = Math.min(clientX + MAGNIFIER_OFFSET, maxLeft);
    const desiredTop = Math.min(clientY + MAGNIFIER_OFFSET, maxTop);
    textMagnifier.style.left = `${Math.max(12, desiredLeft)}px`;
    textMagnifier.style.top = `${Math.max(12, desiredTop)}px`;
}

function showTextMagnifier(clientX, clientY) {
    teardownTextMagnifierClone();
    const clone = document.body.cloneNode(true);
    sanitizeCloneElementIds(clone);
    removeNodesFromClone(clone, ['script', '.text-magnifier']);
    clone.classList.add('text-magnifier-clone');
    clone.style.width = `${window.innerWidth}px`;
    clone.style.height = `${window.innerHeight}px`;
    clone.style.margin = '0';
    syncCloneScrollState(document.body, clone);
    textMagnifierViewport.appendChild(clone);
    magnifierCloneNode = clone;
    magnifierActive = true;
    textMagnifier.classList.remove('hidden');
    textMagnifier.setAttribute('aria-hidden', 'false');
    positionTextMagnifier(clientX, clientY);
    syncTextMagnifierClone(clientX, clientY);
}

function updateTextMagnifier(clientX, clientY) {
    if (!magnifierActive) return;
    positionTextMagnifier(clientX, clientY);
    syncTextMagnifierClone(clientX, clientY);
}

function isWithinTerminalScrollRegion(clientX, clientY) {
    return clientX >= 0 && clientX <= window.innerWidth && clientY >= 0 && clientY <= window.innerHeight;
}

function shouldEnableTextMagnifier(target) {
    if (!target) return false;
    if (target.closest('#text-magnifier')) return false;
    if (target.closest('#chat-window')) return false;
    return true;
}

function beginTextMagnifierPress(event) {
    if (event.button !== 0 || !shouldEnableTextMagnifier(event.target)) return;
    clearMagnifierPressTimer();
    magnifierPointerId = event.pointerId;
    magnifierStartPoint = { x: event.clientX, y: event.clientY };
    magnifierLastPoint = { x: event.clientX, y: event.clientY };
    magnifierPressTimer = window.setTimeout(() => {
        magnifierPressTimer = null;
        if (!magnifierLastPoint || !isWithinTerminalScrollRegion(magnifierLastPoint.x, magnifierLastPoint.y)) return;
        showTextMagnifier(magnifierLastPoint.x, magnifierLastPoint.y);
    }, MAGNIFIER_LONG_PRESS_MS);
}

function trackTextMagnifierPointer(event) {
    if (magnifierPointerId !== event.pointerId) return;
    magnifierLastPoint = { x: event.clientX, y: event.clientY };
    if (magnifierActive) {
        updateTextMagnifier(event.clientX, event.clientY);
        return;
    }
    if (!magnifierStartPoint) return;
    const movedX = event.clientX - magnifierStartPoint.x;
    const movedY = event.clientY - magnifierStartPoint.y;
    if (Math.hypot(movedX, movedY) > MAGNIFIER_MOVE_TOLERANCE) {
        clearMagnifierPressTimer();
        magnifierPointerId = null;
        magnifierStartPoint = null;
        magnifierLastPoint = null;
    }
}

function endTextMagnifierPress(event) {
    if (magnifierPointerId !== null && magnifierPointerId !== event.pointerId) return;
    hideTextMagnifier();
}

async function hydrateKnownAddressPrefill(force = false) {
    if (!authenticatedUser || !selectedScenario) return;
    const currentValue = knownAddressInput.value.trim();
    if (!force && currentValue && currentValue !== autoKnownAddressValue) return;
    const scenarioId = selectedScenario.id;
    try {
        const params = new URLSearchParams({ scenario_id: scenarioId });
        const data = await apiFetch(`/api/mock-known-address?${params.toString()}`);
        if (!selectedScenario || selectedScenario.id !== scenarioId) return;
        autoKnownAddressValue = String(data.known_address || '').trim();
        knownAddressInput.value = autoKnownAddressValue;
    } catch (error) {
        if (authenticatedUser) {
            appendTerminalLine(`[系统错误] 预填已知地址失败：${error.message}`, 'error');
        }
    }
}

function formatElapsedDuration(startValue, endValue = '') {
    const startedAtDate = parseDisplayTimestamp(startValue);
    if (!startedAtDate) return '-';
    const endedAtDate = parseDisplayTimestamp(endValue);
    const referenceDate = endedAtDate || new Date();
    const elapsedMs = Math.max(referenceDate.getTime() - startedAtDate.getTime(), 0);
    const totalSeconds = Math.floor(elapsedMs / 1000);
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    return `${days}天 ${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function stopSessionTimer() {
    if (sessionTimerInterval !== null) {
        window.clearInterval(sessionTimerInterval);
        sessionTimerInterval = null;
    }
}

function refreshSessionTimerDisplay() {
    const hasTiming = Boolean(sessionStartedAt);
    sessionTimerPanel.classList.toggle('hidden', !hasTiming);
    sessionStartedAtNode.textContent = sessionStartedAt || '-';
    sessionEndedAtNode.textContent = sessionEndedAt || '-';
    sessionElapsedTimeNode.textContent = hasTiming
        ? formatElapsedDuration(sessionStartedAt, sessionEndedAt)
        : '-';
}

function syncSessionTimer() {
    stopSessionTimer();
    refreshSessionTimerDisplay();
    if (!sessionStartedAt || sessionEndedAt) return;
    sessionTimerInterval = window.setInterval(refreshSessionTimerDisplay, 1000);
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
    appendSummaryChip(
        sessionContextSummary,
        '故障描述来源',
        hiddenContext.utterance_reference_source === 'library' ? '参考库' : '纯模型',
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
            const canRewind = entry.tone === 'user'
                && Boolean(currentSessionId)
                && !sessionBusy
                && !sessionReviewLocked
                && Number(entry.round_index) > 0;
            if (entry.tone === 'user') {
                const labelTrigger = document.createElement('button');
                labelTrigger.type = 'button';
                labelTrigger.className = 'terminal-turn-trigger';
                labelTrigger.textContent = `[${entry.round_label}]`;
                labelTrigger.title = '删除该用户行及其下方所有内容';
                labelTrigger.dataset.roundIndex = String(entry.round_index || '');
                labelTrigger.dataset.restoreCheckpointIndex = String(
                    Number.isFinite(Number(entry.restore_checkpoint_index))
                        ? Number(entry.restore_checkpoint_index)
                        : Math.max(Number(entry.round_index || 0) - 1, 0),
                );
                labelTrigger.dataset.rewindEnabled = canRewind ? 'true' : 'false';
                labelTrigger.classList.toggle('is-disabled', !canRewind);
                labelTrigger.classList.add('terminal-turn-rewind-trigger');
                line.classList.add('rewindable');
                line.appendChild(labelTrigger);

                const textNode = document.createElement('span');
                textNode.className = 'terminal-user-text';
                textNode.textContent = ` ${entry.speaker}: ${entry.text}`;
                textNode.dataset.roundIndex = String(entry.round_index || '');
                textNode.dataset.hasAddressIeDisplay = entry.has_address_ie_display ? 'true' : 'false';
                line.appendChild(textNode);
            } else if (shouldOfferIssueReference(entry)) {
                const trigger = document.createElement('button');
                trigger.type = 'button';
                trigger.className = 'terminal-reference-trigger';
                trigger.textContent = `[${entry.round_label}] ${entry.speaker}: ${entry.text}`;
                trigger.dataset.referenceTrigger = 'fault-issue-categories';
                line.appendChild(trigger);
            } else {
                line.textContent = `[${entry.round_label}] ${entry.speaker}: ${entry.text}`;
            }
        } else {
            line.textContent = entry.text || '';
        }

        terminalOutput.appendChild(line);
    });
    terminalScrollRegion.scrollTop = terminalScrollRegion.scrollHeight;
    if (magnifierActive && magnifierLastPoint) {
        showTextMagnifier(magnifierLastPoint.x, magnifierLastPoint.y);
    }
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
    const indicator = document.getElementById('session-id-indicator');
    if (!indicator || !sessionIdCopyButton) return;
    const normalized = String(sessionId || '').trim();
    indicator.textContent = normalized || '-';
    sessionIdCopyButton.disabled = !normalized;
    sessionIdCopyButton.title = normalized ? '点击复制完整 Session ID' : '启动会话后可复制 Session ID';
    sessionIdCopyButton.dataset.sessionId = normalized;
    sessionIdCopyButton.dataset.copied = 'false';
    const labelNode = sessionIdCopyButton.querySelector('.session-id-copy-label');
    if (labelNode) labelNode.textContent = 'Session ID';
    if (sessionIdCopyFeedbackTimer !== null) {
        window.clearTimeout(sessionIdCopyFeedbackTimer);
        sessionIdCopyFeedbackTimer = null;
    }
}

async function copyCurrentSessionId() {
    if (!sessionIdCopyButton) return;
    const sessionId = String(sessionIdCopyButton.dataset.sessionId || '').trim();
    if (!sessionId) return;
    try {
        await navigator.clipboard.writeText(sessionId);
    } catch (error) {
        const fallbackInput = document.createElement('textarea');
        fallbackInput.value = sessionId;
        fallbackInput.setAttribute('readonly', 'readonly');
        fallbackInput.style.position = 'absolute';
        fallbackInput.style.left = '-9999px';
        document.body.appendChild(fallbackInput);
        fallbackInput.select();
        document.execCommand('copy');
        document.body.removeChild(fallbackInput);
    }
    const labelNode = sessionIdCopyButton.querySelector('.session-id-copy-label');
    if (labelNode) labelNode.textContent = '已复制';
    sessionIdCopyButton.dataset.copied = 'true';
    if (sessionIdCopyFeedbackTimer !== null) {
        window.clearTimeout(sessionIdCopyFeedbackTimer);
    }
    sessionIdCopyFeedbackTimer = window.setTimeout(() => {
        const currentLabelNode = sessionIdCopyButton.querySelector('.session-id-copy-label');
        if (currentLabelNode) currentLabelNode.textContent = 'Session ID';
        sessionIdCopyButton.dataset.copied = 'false';
        sessionIdCopyFeedbackTimer = null;
    }, 1600);
}

function updateInputAvailability(enabled) {
    const endButton = document.getElementById('end-session-btn');
    const canInteract = enabled
        && !sessionBusy
        && !reviewPending
        && !isReviewModalVisible()
        && Boolean(authenticatedUser)
        && !sessionReviewLocked;
    userInput.disabled = !canInteract;
    sendButton.disabled = !canInteract;
    endButton.disabled = !currentSessionId || sessionClosed || !authenticatedUser || sessionBusy || sessionReviewLocked;
    if (canInteract) userInput.focus();
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
    updateCallStartTimeValidationState();
    updateStartSessionButtonState();
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
    updateStartSessionButtonState();
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
    sessionStartedAt = String(data.started_at || '').trim();
    sessionEndedAt = String(data.ended_at || '').trim();

    setSessionStatus(data.status || 'active');
    setSessionIdIndicator(data.session_id);
    setNextRound(data.next_round_index);
    updateScenarioHeader(data.scenario);
    updateSessionContext(data.scenario, data.session_config || {});
    updateInspector(data.collected_slots, data.runtime_state, data.scenario);
    renderTerminalEntries(sessionTerminalEntries);
    hideIssueReferencePopover();
    closeTerminalTurnMenu();
    syncSessionTimer();

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

function updateInspector(slots = {}, state = {}, scenario = null) {
    const slotsCont = document.getElementById('slots-container');
    const stateCont = document.getElementById('state-container');

    if (currentSlotKeys.length === 0) {
        slotsCont.innerHTML = '<p class="terminal-hint">会话开始后显示</p>';
    } else {
        slotsCont.innerHTML = '';
        const callStartTime = String(scenario?.call_start_time || '').trim();
        const callStartTimeItem = document.createElement('div');
        callStartTimeItem.className = 'data-item';
        callStartTimeItem.innerHTML = `
            <span class="data-key">call_start_time</span>
            <span class="data-value ${callStartTime ? 'filled' : ''}">${callStartTime || '-'}</span>
        `;
        slotsCont.appendChild(callStartTimeItem);
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

    const currentAddressCandidate = String(state.address_current_candidate || '').trim();
    const hasAddressState = ADDRESS_SLOT_FIELDS.some(([key]) => {
        const value = state[key];
        return value !== null && value !== undefined && String(value).trim() !== '';
    }) || Boolean(currentAddressCandidate);
    if (!hasAddressState) {
        addressSlotsContainer.innerHTML = '<p class="terminal-hint">地址环节开始后显示</p>';
    } else {
        addressSlotsContainer.innerHTML = '';
        if (currentAddressCandidate) {
            const candidateItem = document.createElement('div');
            candidateItem.className = 'data-item address-slot-item';
            candidateItem.innerHTML = `
                <div class="address-slot-head">
                    <span class="data-key">当前地址候选</span>
                </div>
                <span class="address-slot-candidate">${currentAddressCandidate}</span>
            `;
            addressSlotsContainer.appendChild(candidateItem);
        }

        ADDRESS_SLOT_FIELDS.forEach(([key, label]) => {
            const rawValue = state[key];
            const value = rawValue === null || rawValue === undefined ? '' : String(rawValue).trim();
            const item = document.createElement('div');
            item.className = 'data-item address-slot-item';
            item.innerHTML = `
                <div class="address-slot-head">
                    <span class="data-key">${label}</span>
                </div>
                <span class="data-value ${value ? 'filled' : ''}">${value}</span>
            `;
            addressSlotsContainer.appendChild(item);
        });
    }

    const visibleStateEntries = Object.entries(state).filter(([, value]) => {
        if (value === null || value === false || value === 0 || value === '') return false;
        if (Array.isArray(value) && value.length === 0) return false;
        return true;
    });
    const hiddenStateKeys = new Set([
        'address_current_candidate',
        'address_collected_value',
        'address_slot_province',
        'address_slot_city',
        'address_slot_district',
        'address_slot_town',
        'address_slot_road',
        'address_slot_community',
        'address_slot_building',
        'address_slot_unit',
        'address_slot_floor',
        'address_slot_room',
        'address_slot_landmark',
        'address_missing_required_precision',
    ]);
    const filteredStateEntries = visibleStateEntries.filter(([key]) => !hiddenStateKeys.has(key));

    if (filteredStateEntries.length === 0) {
        stateCont.innerHTML = '<p class="terminal-hint">当前没有活跃运行时状态</p>';
        return;
    }

    stateCont.innerHTML = '';
    filteredStateEntries.forEach(([key, value]) => {
        const item = document.createElement('div');
        item.className = 'data-item state-item';
        item.innerHTML = `
            <span class="data-key">${key}</span>
            <span class="data-value mono">${JSON.stringify(value)}</span>
        `;
        stateCont.appendChild(item);
    });
}

function renderChatAdminControls() {
    if (!chatAdminControls || !chatAdminStatus || !chatClearHistoryButton || !chatClearHistoryCheckbox) return;
    const shouldShow = Boolean(chatAdminEnabled);
    chatAdminControls.classList.toggle('hidden', !shouldShow);
    if (!shouldShow) {
        chatClearHistoryCheckbox.checked = false;
        chatClearHistoryButton.disabled = true;
        chatAdminStatus.textContent = '';
        chatAdminStatus.classList.add('hidden');
        chatAdminStatus.classList.remove('is-error');
        return;
    }
    chatClearHistoryButton.disabled = !chatClearHistoryCheckbox.checked;
}

function setChatSendStatus(message = '', { isError = false } = {}) {
    if (!chatSendStatus) return;
    chatSendStatus.textContent = String(message || '');
    chatSendStatus.classList.toggle('hidden', !message);
    chatSendStatus.classList.toggle('is-error', Boolean(message) && isError);
}

function getChatMentionCandidates(query = '') {
    const normalizedQuery = String(query || '').trim().toLowerCase();
    const uniqueByUsername = new Map();
    chatOnlineUsersCache.forEach((user) => {
        const username = String(user.username || '').trim();
        if (!username || username === authenticatedUser?.username) return;
        if (!normalizedQuery) {
            uniqueByUsername.set(username, user);
            return;
        }
        const displayName = String(user.display_name || '').trim().toLowerCase();
        if (username.toLowerCase().includes(normalizedQuery) || displayName.includes(normalizedQuery)) {
            uniqueByUsername.set(username, user);
        }
    });
    return Array.from(uniqueByUsername.values()).slice(0, CHAT_MENTION_OPTION_LIMIT);
}

function getTextareaCaretCoordinates(textarea, position) {
    const mirror = document.createElement('div');
    const style = window.getComputedStyle(textarea);
    const properties = [
        'boxSizing', 'width', 'height', 'overflowX', 'overflowY',
        'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth',
        'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
        'fontStyle', 'fontVariant', 'fontWeight', 'fontStretch', 'fontSize',
        'fontSizeAdjust', 'lineHeight', 'fontFamily', 'textAlign', 'textTransform',
        'textIndent', 'textDecoration', 'letterSpacing', 'wordSpacing',
        'tabSize', 'MozTabSize', 'whiteSpace', 'wordBreak', 'overflowWrap',
    ];
    mirror.style.position = 'fixed';
    mirror.style.left = '-9999px';
    mirror.style.top = '0';
    mirror.style.visibility = 'hidden';
    properties.forEach((property) => {
        mirror.style[property] = style[property];
    });
    mirror.style.whiteSpace = 'pre-wrap';
    mirror.style.wordBreak = 'break-word';
    mirror.style.overflowWrap = 'anywhere';
    mirror.textContent = textarea.value.slice(0, position);
    const marker = document.createElement('span');
    marker.textContent = textarea.value.slice(position) || '.';
    mirror.appendChild(marker);
    document.body.appendChild(mirror);
    const textareaRect = textarea.getBoundingClientRect();
    const markerRect = marker.getBoundingClientRect();
    const result = {
        left: textareaRect.left + (markerRect.left - mirror.getBoundingClientRect().left) - textarea.scrollLeft,
        top: textareaRect.top + (markerRect.top - mirror.getBoundingClientRect().top) - textarea.scrollTop,
        height: markerRect.height || parseFloat(style.lineHeight) || 20,
    };
    document.body.removeChild(mirror);
    return result;
}

function renderChatMentionDropdown() {
    if (!chatMentionState || chatMentionOptions.length === 0) {
        clearChatMentionDropdown();
        return;
    }
    const optionsMarkup = chatMentionOptions.map((user, index) => `
        <button
            class="chat-mention-option ${index === chatMentionActiveIndex ? 'is-active' : ''}"
            type="button"
            data-username="${escapeHtml(user.username || '')}"
        >
            <span class="chat-mention-option-name">${escapeHtml(user.display_name || user.username || '匿名用户')}</span>
            <span class="chat-mention-option-meta">@${escapeHtml(user.username || '-')}</span>
        </button>
    `).join('');
    chatMentionDropdown.innerHTML = optionsMarkup;
    chatMentionDropdown.classList.remove('hidden');
    chatMentionDropdown.setAttribute('aria-hidden', 'false');
}

function positionChatMentionDropdown() {
    if (!chatMentionState || chatMentionDropdown.classList.contains('hidden')) return;
    const caret = getTextareaCaretCoordinates(chatInput, chatMentionState.cursorIndex);
    const width = Math.min(240, Math.max(window.innerWidth - 16, 160));
    const dropdownWidth = Math.min(width, 240);
    const dropdownHeight = Math.min(224, Math.max(window.innerHeight - 16, 96));
    const maxLeft = Math.max(8, window.innerWidth - dropdownWidth - 8);
    const maxTop = Math.max(8, window.innerHeight - dropdownHeight - 8);
    const left = clamp(caret.left + 12, 8, maxLeft);
    const top = clamp(caret.top + caret.height + 8, 8, maxTop);
    chatMentionDropdown.style.left = `${left}px`;
    chatMentionDropdown.style.top = `${top}px`;
}

function updateChatMentionDropdown() {
    if (!authenticatedUser || !chatInput) return;
    const cursorIndex = Number(chatInput.selectionStart || 0);
    const valueBeforeCursor = chatInput.value.slice(0, cursorIndex);
    const mentionMatch = valueBeforeCursor.match(/(^|[\s(（\[【])@([^\s@]*)$/);
    if (!mentionMatch) {
        clearChatMentionDropdown();
        return;
    }
    const query = mentionMatch[2] || '';
    const options = getChatMentionCandidates(query);
    if (options.length === 0) {
        clearChatMentionDropdown();
        return;
    }
    chatMentionState = {
        startIndex: cursorIndex - query.length - 1,
        cursorIndex,
        query,
    };
    chatMentionOptions = options;
    chatMentionActiveIndex = 0;
    renderChatMentionDropdown();
    positionChatMentionDropdown();
}

function applyChatMention(user) {
    if (!user || !chatMentionState) return;
    const before = chatInput.value.slice(0, chatMentionState.startIndex);
    const after = chatInput.value.slice(chatInput.selectionStart || chatMentionState.cursorIndex);
    const mentionText = `@${user.username} `;
    const nextValue = `${before}${mentionText}${after}`;
    const nextCursorIndex = before.length + mentionText.length;
    chatInput.value = nextValue;
    chatInput.focus();
    chatInput.setSelectionRange(nextCursorIndex, nextCursorIndex);
    clearChatMentionDropdown();
}

function extractMentionedUsernames(text) {
    const usernames = new Set();
    const mentionPattern = /@([A-Za-z0-9._-]+)/g;
    let matched;
    while ((matched = mentionPattern.exec(String(text || ''))) !== null) {
        usernames.add(matched[1]);
    }
    return usernames;
}

function beginChatLauncherDrag(event) {
    if (chatLauncher.classList.contains('hidden') || event.button !== 0) return;
    const currentRect = chatLauncher.getBoundingClientRect();
    chatLauncherDragState = {
        pointerId: event.pointerId,
        offsetX: event.clientX - currentRect.left,
        offsetY: event.clientY - currentRect.top,
        moved: false,
    };
}

function handleChatLauncherDrag(event) {
    if (!chatLauncherDragState || event.pointerId !== chatLauncherDragState.pointerId) return;
    const bounds = getChatViewportBounds();
    const width = Math.max(chatLauncher.offsetWidth || 172, 120);
    const height = Math.max(chatLauncher.offsetHeight || 50, 40);
    const maxLeft = Math.max(CHAT_VIEWPORT_MARGIN, bounds.width - width - CHAT_VIEWPORT_MARGIN);
    const maxTop = Math.max(CHAT_VIEWPORT_MARGIN, bounds.height - height - CHAT_VIEWPORT_MARGIN);
    const nextLeft = clamp(event.clientX - chatLauncherDragState.offsetX, CHAT_VIEWPORT_MARGIN, maxLeft);
    const nextTop = clamp(event.clientY - chatLauncherDragState.offsetY, CHAT_VIEWPORT_MARGIN, maxTop);
    chatLauncher.style.left = `${nextLeft}px`;
    chatLauncher.style.top = `${nextTop}px`;
    chatLauncher.style.right = 'auto';
    chatLauncher.style.bottom = 'auto';
    chatLauncherDragState.moved = true;
}

function endChatLauncherDrag(event) {
    if (!chatLauncherDragState || (event && event.pointerId !== chatLauncherDragState.pointerId)) return;
    const moved = chatLauncherDragState.moved;
    chatLauncherDragState = null;
    if (moved) {
        chatLauncherSuppressClickUntil = Date.now() + 240;
        syncChatLauncherStateFromDom();
        persistChatWindowState();
    }
}

function setChatOnlineDrawerOpen(open) {
    chatOnlineDrawerOpen = Boolean(open);
    chatOnlineCount.setAttribute('aria-expanded', chatOnlineDrawerOpen ? 'true' : 'false');
    chatOnlineUsers.classList.toggle('hidden', !chatOnlineDrawerOpen);
    if (!chatOnlineDrawerOpen) {
        chatOnlineDrawerPosition = null;
        chatOnlineUsers.style.left = '';
        chatOnlineUsers.style.top = '';
    }
}

function positionChatOnlineDrawer(clientX, clientY) {
    if (!chatOnlineUsers) return;
    const drawerWidth = Math.min(288, Math.max(window.innerWidth - 16, 160));
    const drawerHeight = Math.min(256, Math.max(window.innerHeight - 16, 120));
    const maxLeft = Math.max(8, window.innerWidth - drawerWidth - 8);
    const maxTop = Math.max(8, window.innerHeight - drawerHeight - 8);
    const left = clamp((clientX || 0) + 14, 8, maxLeft);
    const top = clamp((clientY || 0) - 8, 8, maxTop);
    chatOnlineDrawerPosition = { clientX: Number(clientX || 0), clientY: Number(clientY || 0) };
    chatOnlineUsers.style.left = `${left}px`;
    chatOnlineUsers.style.top = `${top}px`;
}

function clearChatMessageHold() {
    if (chatMessageHoldTimer !== null) {
        window.clearTimeout(chatMessageHoldTimer);
        chatMessageHoldTimer = null;
    }
    chatMessageHoldPointerId = null;
    chatMessageHoldStartPoint = null;
    chatMessageHoldMessageId = 0;
}

function closeChatMessageMenu() {
    chatContextMenuMessageId = 0;
    if (!chatMessageMenu) return;
    chatMessageMenu.classList.add('hidden');
    chatMessageMenu.setAttribute('aria-hidden', 'true');
    chatMessageMenu.style.left = '';
    chatMessageMenu.style.top = '';
}

function openChatMessageMenu(messageId, clientX, clientY) {
    if (!chatMessageMenu || !chatRecallButton || !messageId) return;
    chatContextMenuMessageId = Number(messageId || 0);
    chatMessageMenu.classList.remove('hidden');
    chatMessageMenu.setAttribute('aria-hidden', 'false');
    chatRecallButton.disabled = false;

    const menuWidth = Math.max(chatMessageMenu.offsetWidth || 148, 132);
    const menuHeight = Math.max(chatMessageMenu.offsetHeight || 54, 48);
    const maxLeft = Math.max(8, window.innerWidth - menuWidth - 8);
    const maxTop = Math.max(8, window.innerHeight - menuHeight - 8);
    const left = clamp(Number(clientX || 0), 8, maxLeft);
    const top = clamp(Number(clientY || 0), 8, maxTop);
    chatMessageMenu.style.left = `${left}px`;
    chatMessageMenu.style.top = `${top}px`;
}

function resetChatRuntime() {
    chatMessages = [];
    chatLatestMessageId = 0;
    chatLatestSelfMessageId = 0;
    chatReadReceiptOpenMessageId = 0;
    chatReadReceiptMembers = [];
    chatUnreadCount = 0;
    chatStateInitialized = false;
    chatSnapshotRevision = 0;
    chatStoragePath = '';
    chatOnlineUserCount = 0;
    chatOnlineUsersCache = [];
    chatOnlineDrawerOpen = false;
    chatOnlineDrawerPosition = null;
    chatAdminEnabled = false;
    chatMentionAlertActive = false;
    chatPollInFlight = false;
    endChatLauncherDrag();
    clearChatMessageHold();
    clearChatMentionDropdown();
    closeChatMessageMenu();
    if (chatSendButton) chatSendButton.disabled = false;
    if (chatInput) chatInput.value = '';
    if (chatStorageStatus) {
        chatStorageStatus.textContent = '';
        chatStorageStatus.classList.add('hidden');
    }
    setChatSendStatus('');
    if (chatOnlineCount) chatOnlineCount.textContent = '在线 0 人';
    if (chatOnlinePreview) chatOnlinePreview.innerHTML = '<p class="terminal-hint">登录后显示在线成员</p>';
    if (chatOnlineUsers) chatOnlineUsers.innerHTML = '<p class="terminal-hint">登录后显示全部在线成员</p>';
    setChatOnlineDrawerOpen(false);
    if (chatMessageList) chatMessageList.innerHTML = '<p class="terminal-hint">登录后显示群聊记录</p>';
    renderChatAdminControls();
    updateChatLauncher();
}

function stopChatPolling() {
    if (chatPollTimer !== null) {
        window.clearInterval(chatPollTimer);
        chatPollTimer = null;
    }
    chatPollInFlight = false;
}

function isChatNearBottom() {
    if (!chatMessageList) return true;
    const distance = chatMessageList.scrollHeight - chatMessageList.scrollTop - chatMessageList.clientHeight;
    return distance < 36;
}

function formatChatUserHandle(username) {
    const normalizedUsername = String(username || '').trim();
    return normalizedUsername ? `@${normalizedUsername}` : '@-';
}

function renderChatOnlineUsers(users = []) {
    chatOnlineUsersCache = Array.isArray(users) ? users : [];
    chatOnlineUserCount = users.length;
    chatOnlineCount.textContent = `在线 ${users.length} 人`;

    clearElement(chatOnlinePreview);
    if (users.length === 0) {
        chatOnlinePreview.innerHTML = '<p class="terminal-hint">当前暂无在线成员</p>';
        chatOnlineUsers.innerHTML = '<p class="terminal-hint">当前暂无在线成员</p>';
        setChatOnlineDrawerOpen(false);
        updateChatLauncher();
        return;
    }

    users.slice(0, 3).forEach((user) => {
        const item = document.createElement('div');
        item.className = 'chat-user-chip is-preview';

        const name = document.createElement('span');
        name.className = 'chat-user-chip-name';
        name.textContent = formatChatUserHandle(user.username);

        item.appendChild(name);
        chatOnlinePreview.appendChild(item);
    });

    clearElement(chatOnlineUsers);
    users.forEach((user) => {
        const item = document.createElement('div');
        item.className = 'chat-user-chip';

        const name = document.createElement('span');
        name.className = 'chat-user-chip-name';
        name.textContent = formatChatUserHandle(user.username);

        item.appendChild(name);
        chatOnlineUsers.appendChild(item);
    });

    if (chatOnlineDrawerOpen && chatOnlineDrawerPosition) {
        positionChatOnlineDrawer(chatOnlineDrawerPosition.clientX, chatOnlineDrawerPosition.clientY);
    } else {
        setChatOnlineDrawerOpen(false);
    }
    updateChatLauncher();
}

function latestSelfChatMessageId(messages = []) {
    if (!authenticatedUser) return 0;
    for (let index = messages.length - 1; index >= 0; index -= 1) {
        const message = messages[index];
        if (message && !message.recalled && message.username === authenticatedUser.username) {
            return Number(message.id || 0);
        }
    }
    return 0;
}

function renderChatMessages({ forceScroll = false } = {}) {
    const shouldScroll = forceScroll || isChatNearBottom();
    clearElement(chatMessageList);
    if (chatMessages.length === 0) {
        chatMessageList.innerHTML = '<p class="terminal-hint">还没有群聊消息，发一条试试。</p>';
        return;
    }
    chatMessages.forEach((message) => {
        const item = document.createElement('article');
        item.className = 'chat-message-item';
        const isSelf = Boolean(authenticatedUser && message.username === authenticatedUser.username);
        const isRecalled = Boolean(message.recalled);
        const isLatestSelf = isSelf && !isRecalled && Number(message.id || 0) === chatLatestSelfMessageId;
        item.dataset.messageId = String(message.id || 0);
        item.dataset.recalled = isRecalled ? 'true' : 'false';
        if (isSelf) {
            item.classList.add('is-self');
        }
        if (isRecalled) {
            item.classList.add('is-recalled');
        }
        if (isLatestSelf) {
            item.classList.add('is-latest-self');
        }

        const meta = document.createElement('div');
        meta.className = 'chat-message-meta';

        const sentAt = document.createElement('span');
        sentAt.textContent = message.sent_at || '-';

        const author = document.createElement('span');
        author.className = 'chat-message-author';
        author.textContent = formatChatUserHandle(message.username);

        const text = document.createElement('p');
        text.className = 'chat-message-text';
        text.textContent = isRecalled ? '--该条信息已撤回--' : (message.text || '');
        if (isRecalled) {
            text.classList.add('is-recalled-notice');
        }

        meta.appendChild(sentAt);
        meta.appendChild(author);
        item.appendChild(meta);
        item.appendChild(text);

        if (isLatestSelf) {
            const hint = document.createElement('div');
            hint.className = 'chat-message-read-hint';
            hint.textContent = '长按查看已读成员';
            item.appendChild(hint);
        }

        if (chatReadReceiptOpenMessageId === Number(message.id || 0)) {
            const drawer = document.createElement('section');
            drawer.className = 'chat-readers-drawer';

            const drawerTitle = document.createElement('div');
            drawerTitle.className = 'chat-readers-title';
            drawerTitle.textContent = '已读成员';
            drawer.appendChild(drawerTitle);

            if (chatReadReceiptMembers.length === 0) {
                const empty = document.createElement('p');
                empty.className = 'chat-readers-empty';
                empty.textContent = '暂时还没有成员已读';
                drawer.appendChild(empty);
            } else {
                const list = document.createElement('div');
                list.className = 'chat-readers-list';
                chatReadReceiptMembers.forEach((member) => {
                    const chip = document.createElement('span');
                    chip.className = 'chat-readers-chip';
                    chip.textContent = member.username || member.display_name || '-';
                    list.appendChild(chip);
                });
                drawer.appendChild(list);
            }
            item.appendChild(drawer);
        }
        chatMessageList.appendChild(item);
    });
    if (shouldScroll && chatWindowState?.visible !== false) {
        window.requestAnimationFrame(() => {
            chatMessageList.scrollTop = chatMessageList.scrollHeight;
        });
    }
}

function isChatPersistenceAdmin() {
    return Boolean(chatAdminEnabled);
}

function mergeChatState(data, { forceScroll = false } = {}) {
    if (!data || !authenticatedUser) return;
    chatStoragePath = String(data.storage_path || '').trim();
    const serverSnapshotRevision = Math.max(Number(data.snapshot_revision || 0), 0);
    if (typeof data.chat_admin === 'boolean') {
        chatAdminEnabled = data.chat_admin;
    }
    if (chatStorageStatus) {
        if (chatStoragePath && isChatPersistenceAdmin()) {
            chatStorageStatus.textContent = '本地持久化已开启';
            chatStorageStatus.classList.remove('hidden');
        } else {
            chatStorageStatus.textContent = '';
            chatStorageStatus.classList.add('hidden');
        }
    }
    setChatSendStatus('');
    renderChatAdminControls();
    if (Array.isArray(data.online_users)) {
        renderChatOnlineUsers(data.online_users);
    }

    const incoming = Array.isArray(data.messages) ? data.messages : [];
    const isInitialSnapshot = !chatStateInitialized;
    const previousLatest = chatLatestMessageId;
    const serverLatest = Number(data.latest_message_id || 0);
    const serverReset = serverLatest < previousLatest;
    const shouldReplaceMessages = serverReset || Boolean(data.full_sync) || isInitialSnapshot;

    if (shouldReplaceMessages) {
        chatMessages = incoming;
    } else if (incoming.length > 0) {
        const knownIds = new Set(chatMessages.map((item) => item.id));
        incoming.forEach((message) => {
            if (!knownIds.has(message.id)) {
                chatMessages.push(message);
            }
        });
    }

    chatMessages = chatMessages
        .filter((message) => message && Number(message.id) > 0)
        .sort((left, right) => Number(left.id) - Number(right.id));
    chatLatestSelfMessageId = latestSelfChatMessageId(chatMessages);
    if (chatReadReceiptOpenMessageId && chatReadReceiptOpenMessageId !== chatLatestSelfMessageId) {
        chatReadReceiptOpenMessageId = 0;
        chatReadReceiptMembers = [];
    }
    chatLatestMessageId = Math.max(serverLatest, ...chatMessages.map((item) => Number(item.id || 0)), previousLatest);
    chatSnapshotRevision = serverSnapshotRevision;

    const newMessageCount = isInitialSnapshot
        ? 0
        : incoming.filter((message) => Number(message.id || 0) > previousLatest).length;
    const hasMentionForCurrentUser = !isInitialSnapshot && incoming.some((message) => (
        message
        && String(message.username || '') !== String(authenticatedUser?.username || '')
        && extractMentionedUsernames(message.text || '').has(String(authenticatedUser?.username || ''))
    ));
    if (chatWindowState?.visible === false && newMessageCount > 0) {
        chatUnreadCount += newMessageCount;
        if (hasMentionForCurrentUser) {
            chatMentionAlertActive = true;
        }
    } else if (chatWindowState?.visible !== false) {
        chatUnreadCount = 0;
        chatMentionAlertActive = false;
    }
    if (serverReset) {
        chatUnreadCount = 0;
        chatMentionAlertActive = false;
    }

    renderChatMessages({ forceScroll: forceScroll || isInitialSnapshot });
    chatStateInitialized = true;
    updateChatLauncher();
}

async function refreshChatState({ forceScroll = false } = {}) {
    if (!authenticatedUser || chatPollInFlight) return;
    chatPollInFlight = true;
    try {
        const params = new URLSearchParams({
            since_message_id: String(chatLatestMessageId || 0),
            since_snapshot_revision: String(chatSnapshotRevision || 0),
            chat_visible: chatWindowState?.visible === false ? 'false' : 'true',
        });
        const data = await apiFetch(`/api/chat/state?${params.toString()}`);
        mergeChatState(data, { forceScroll });
    } finally {
        chatPollInFlight = false;
    }
}

function startChatPolling() {
    stopChatPolling();
    resetChatRuntime();
    refreshChatState({ forceScroll: true });
    chatPollTimer = window.setInterval(() => {
        refreshChatState();
    }, CHAT_POLL_INTERVAL_MS);
}

function beginChatDrag(event) {
    if (!chatWindowState?.visible) return;
    if (event.target.closest('button, textarea, input')) return;
    event.preventDefault();
    const currentLeft = parseFloat(chatWindow.style.left) || 0;
    const currentTop = parseFloat(chatWindow.style.top) || 0;
    chatDragState = {
        pointerId: event.pointerId,
        offsetX: event.clientX - currentLeft,
        offsetY: event.clientY - currentTop,
    };
}

function handleChatDrag(event) {
    if (!chatDragState || event.pointerId !== chatDragState.pointerId) return;
    const width = chatWindow.offsetWidth || chatWindowState.width || CHAT_MIN_WIDTH;
    const height = chatWindow.offsetHeight || chatWindowState.height || CHAT_MIN_HEIGHT;
    const bounds = getChatViewportBounds();
    const nextLeft = clamp(event.clientX - chatDragState.offsetX, CHAT_VIEWPORT_MARGIN, bounds.width - width - CHAT_VIEWPORT_MARGIN);
    const nextTop = clamp(event.clientY - chatDragState.offsetY, CHAT_VIEWPORT_MARGIN, bounds.height - height - CHAT_VIEWPORT_MARGIN);
    chatWindow.style.left = `${nextLeft}px`;
    chatWindow.style.top = `${nextTop}px`;
}

function endChatDrag(event) {
    if (!chatDragState || (event && event.pointerId !== chatDragState.pointerId)) return;
    chatDragState = null;
    syncChatWindowStateFromDom();
    persistChatWindowState();
}

async function sendChatMessage() {
    if (!authenticatedUser) return;
    const text = chatInput.value.trim();
    if (!text) return;
    chatSendButton.disabled = true;
    setChatSendStatus('');
    try {
        const data = await apiFetch('/api/chat/messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
        chatInput.value = '';
        mergeChatState(
            {
                messages: [data.message],
                latest_message_id: data.message?.id || chatLatestMessageId,
                snapshot_revision: data.snapshot_revision || chatSnapshotRevision,
                storage_path: data.storage_path || chatStoragePath,
            },
            { forceScroll: true },
        );
        await refreshChatState({ forceScroll: true });
        clearChatMentionDropdown();
    } catch (error) {
        setChatSendStatus(error.message, { isError: true });
        throw error;
    } finally {
        chatSendButton.disabled = false;
    }
}

async function recallChatMessage(messageId) {
    if (!authenticatedUser || !messageId) return;
    chatRecallButton.disabled = true;
    setChatSendStatus('');
    try {
        const data = await apiFetch(`/api/chat/messages/${messageId}/recall`, {
            method: 'POST',
        });
        closeChatMessageMenu();
        mergeChatState(data, { forceScroll: false });
    } catch (error) {
        setChatSendStatus(error.message, { isError: true });
        throw error;
    } finally {
        if (chatRecallButton) {
            chatRecallButton.disabled = false;
        }
    }
}

async function showLatestSelfMessageReaders(messageId) {
    if (!authenticatedUser || !messageId || messageId !== chatLatestSelfMessageId) return;
    const params = new URLSearchParams({
        chat_visible: chatWindowState?.visible === false ? 'false' : 'true',
    });
    const data = await apiFetch(`/api/chat/messages/latest-readers?${params.toString()}`);
    if (Number(data.latest_self_message_id || 0) !== Number(messageId)) {
        chatReadReceiptOpenMessageId = 0;
        chatReadReceiptMembers = [];
        renderChatMessages();
        return;
    }
    chatReadReceiptOpenMessageId = Number(messageId);
    chatReadReceiptMembers = Array.isArray(data.read_by) ? data.read_by : [];
    renderChatMessages();
}

function beginChatMessageHold(event) {
    const messageNode = event.target.closest('.chat-message-item.is-self.is-latest-self');
    if (!messageNode) return;
    if (event.button !== 0) return;
    clearChatMessageHold();
    chatMessageHoldPointerId = event.pointerId;
    chatMessageHoldStartPoint = { x: event.clientX, y: event.clientY };
    chatMessageHoldMessageId = Number(messageNode.dataset.messageId || 0);
    chatMessageHoldTimer = window.setTimeout(() => {
        const targetMessageId = chatMessageHoldMessageId;
        clearChatMessageHold();
        showLatestSelfMessageReaders(targetMessageId).catch(() => {});
    }, CHAT_MESSAGE_HOLD_MS);
}

function trackChatMessageHold(event) {
    if (chatMessageHoldPointerId !== event.pointerId || !chatMessageHoldStartPoint) return;
    const movedX = event.clientX - chatMessageHoldStartPoint.x;
    const movedY = event.clientY - chatMessageHoldStartPoint.y;
    if (Math.hypot(movedX, movedY) > CHAT_MESSAGE_HOLD_MOVE_TOLERANCE) {
        clearChatMessageHold();
    }
}

function endChatMessageHold(event) {
    if (chatMessageHoldPointerId !== null && event && event.pointerId !== chatMessageHoldPointerId) return;
    clearChatMessageHold();
}

async function clearChatHistory() {
    if (!chatAdminEnabled) return;
    if (!chatClearHistoryCheckbox.checked) {
        chatAdminStatus.textContent = '请先勾选“清空全部聊天历史”。';
        chatAdminStatus.classList.remove('hidden');
        chatAdminStatus.classList.add('is-error');
        return;
    }
    const confirmed = window.confirm('确认清空全部聊天历史吗？该操作会同时删除本地持久化内容，且不可恢复。');
    if (!confirmed) return;

    chatClearHistoryButton.disabled = true;
    chatAdminStatus.textContent = '正在清空聊天历史...';
    chatAdminStatus.classList.remove('hidden');
    chatAdminStatus.classList.remove('is-error');

    try {
        const data = await apiFetch('/api/chat/history/clear', {
            method: 'POST',
        });
        chatMessages = [];
        chatLatestMessageId = 0;
        chatStoragePath = String(data.storage_path || '').trim();
        chatClearHistoryCheckbox.checked = false;
        renderChatAdminControls();
        mergeChatState(
            {
                messages: [],
                latest_message_id: 0,
                snapshot_revision: data.snapshot_revision || 0,
                full_sync: true,
                storage_path: data.storage_path || '',
                chat_admin: true,
            },
            { forceScroll: true },
        );
        renderChatMessages({ forceScroll: true });
        chatAdminStatus.textContent = '聊天历史已清空，本地持久化内容已同步删除。';
        chatAdminStatus.classList.remove('hidden');
        chatAdminStatus.classList.remove('is-error');
        await refreshChatState({ forceScroll: true });
    } catch (error) {
        chatAdminStatus.textContent = error.message;
        chatAdminStatus.classList.remove('hidden');
        chatAdminStatus.classList.add('is-error');
        renderChatAdminControls();
        throw error;
    }
}

function initializeChatWindow() {
    chatWindowState = loadChatWindowState();
    applyChatWindowRect();
    setChatWindowVisibility(chatWindowState.visible !== false, { persist: false });
    if ('ResizeObserver' in window && !chatResizeObserver) {
        chatResizeObserver = new ResizeObserver(() => {
            if (chatWindow.classList.contains('hidden')) return;
            syncChatWindowStateFromDom();
            persistChatWindowState();
        });
        chatResizeObserver.observe(chatWindow);
    }
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
    sessionStartedAt = '';
    sessionEndedAt = '';
    autoKnownAddressValue = '';
    autoCallStartTimeValue = '';
    stopSessionTimer();
    refreshSessionTimerDisplay();
    hideIssueReferencePopover();
    hideTextMagnifier();
    resetReviewState();
    updateScenarioHeader(null);
    updateSessionContext(null, {});
    updateInspector({}, {});
    setSessionStatus('idle');
    setSessionIdIndicator('');
    setNextRound(1);
    updateInputAvailability(false);
    knownAddressInput.value = '';
    callStartTimeInput.value = '';
    useSessionStartTimeCheckbox.checked = false;
    prefillMockCallStartTime(true);
    updateCallStartTimeValidationState();
    updateStartSessionButtonState();
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
    updateCallStartTimeValidationState();
    updateStartSessionButtonState();
    initializeChatWindow();
    startChatPolling();
}

function applyLoggedOutState(message = '') {
    authenticatedUser = null;
    authUserName.textContent = '未登录';
    authUserMeta.textContent = '只有备案账号可访问测试台。';
    appShell.classList.add('hidden');
    authGate.classList.remove('hidden');
    stopChatPolling();
    resetChatRuntime();
    chatLauncher.classList.add('hidden');
    chatWindow.classList.add('hidden');
    chatWindow.setAttribute('aria-hidden', 'true');
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
    prefillMockCallStartTime(false);
    updateCallStartTimeValidationState();
    updateStartSessionButtonState();
    hydrateKnownAddressPrefill(false);
}

async function checkAuth() {
    resetWorkspace();
    stopChatPolling();
    resetChatRuntime();
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
                ? `[系统] 评审已提交，session_id=${data.session_id}，username=${data.username}。数据 ${data.session_id} 已写入数据库。`
                : `[系统] 评审已提交，session_id=${data.session_id}，username=${data.username}，本次数据未写入数据库。`,
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
    updateStartSessionButtonState();
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

    if (!updateCallStartTimeValidationState()) {
        updateStartSessionButtonState();
        return;
    }
    const payload = {
        scenario_id: selectedScenario.id,
        auto_generate_hidden_settings: document.getElementById('auto-hidden-settings').checked,
        known_address: knownAddressInput.value,
        call_start_time: callStartTimeInput.value.trim(),
        use_session_start_time_as_call_start_time: useSessionStartTimeCheckbox.checked,
        persist_to_db: document.getElementById('persist-to-db').checked,
    };

    const output = document.getElementById('terminal-output');
    output.innerHTML = '';
    appendTerminalLine('正在初始化手工测试会话...', 'system');
    sessionBusy = true;
    updateInputAvailability(false);
    updateStartSessionButtonState();
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
    const rawText = userInput.value;
    const text = rawText.trim();
    if (!text || !currentSessionId || sessionClosed) return;

    if (sessionInputHistory.length === 0 || sessionInputHistory[sessionInputHistory.length - 1] !== rawText) {
        sessionInputHistory.push(rawText);
        if (sessionInputHistory.length > SESSION_INPUT_HISTORY_LIMIT) {
            sessionInputHistory = sessionInputHistory.slice(-SESSION_INPUT_HISTORY_LIMIT);
        }
    }
    sessionInputHistoryIndex = -1;
    sessionInputDraft = '';
    userInput.value = '';
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

async function toggleAddressIeDisplayForRound(roundIndex, enabled) {
    if (!currentSessionId || sessionBusy || roundIndex < 1) return;

    setSessionBusyState(true);
    let errorMessage = '';
    try {
        const data = await apiFetch('/api/session/address-ie-display', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                round_index: roundIndex,
                enabled: Boolean(enabled),
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
        closeTerminalTurnMenu();
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
startSessionButton.onclick = startSession;
document.getElementById('end-session-btn').onclick = forceEndSession;
document.getElementById('send-btn').onclick = sendMessage;
chatLauncher.addEventListener('click', () => {
    if (Date.now() < chatLauncherSuppressClickUntil) return;
    setChatWindowVisibility(true, { scrollToBottom: true });
});
chatLauncher.addEventListener('pointerdown', beginChatLauncherDrag);
chatHideButton.addEventListener('click', () => {
    setChatWindowVisibility(false);
});
chatOnlineCount.addEventListener('click', (event) => {
    if (chatOnlineUsersCache.length === 0) return;
    if (chatOnlineDrawerOpen) {
        setChatOnlineDrawerOpen(false);
        return;
    }
    positionChatOnlineDrawer(event.clientX, event.clientY);
    setChatOnlineDrawerOpen(true);
});
chatWindowHeader.addEventListener('pointerdown', beginChatDrag);
chatMessageList.addEventListener('pointerdown', beginChatMessageHold);
chatMessageList.addEventListener('pointermove', trackChatMessageHold);
chatMessageList.addEventListener('pointerup', endChatMessageHold);
chatMessageList.addEventListener('pointercancel', endChatMessageHold);
chatMessageList.addEventListener('pointerleave', endChatMessageHold);
chatMessageList.addEventListener('contextmenu', (event) => {
    const messageNode = event.target.closest('.chat-message-item.is-self');
    if (!messageNode || messageNode.dataset.recalled === 'true') {
        closeChatMessageMenu();
        return;
    }
    event.preventDefault();
    openChatMessageMenu(Number(messageNode.dataset.messageId || 0), event.clientX, event.clientY);
});
chatClearHistoryCheckbox.addEventListener('change', () => {
    if (chatAdminStatus) {
        chatAdminStatus.textContent = '';
        chatAdminStatus.classList.add('hidden');
        chatAdminStatus.classList.remove('is-error');
    }
    renderChatAdminControls();
});
chatClearHistoryButton.addEventListener('click', () => {
    clearChatHistory().catch(() => {});
});
chatMentionDropdown.addEventListener('click', (event) => {
    const option = event.target.closest('.chat-mention-option');
    if (!option) return;
    const matched = chatMentionOptions.find((user) => user.username === option.dataset.username);
    if (!matched) return;
    applyChatMention(matched);
});
chatRecallButton.addEventListener('click', () => {
    recallChatMessage(chatContextMenuMessageId).catch(() => {});
});
chatSendButton.addEventListener('click', () => {
    sendChatMessage().catch(() => {});
});
chatInput.addEventListener('keydown', (event) => {
    if (!chatMentionDropdown.classList.contains('hidden')) {
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            chatMentionActiveIndex = (chatMentionActiveIndex + 1) % chatMentionOptions.length;
            renderChatMentionDropdown();
            positionChatMentionDropdown();
            return;
        }
        if (event.key === 'ArrowUp') {
            event.preventDefault();
            chatMentionActiveIndex = (chatMentionActiveIndex - 1 + chatMentionOptions.length) % chatMentionOptions.length;
            renderChatMentionDropdown();
            positionChatMentionDropdown();
            return;
        }
        if (event.key === 'Enter' && chatMentionOptions.length > 0) {
            event.preventDefault();
            applyChatMention(chatMentionOptions[chatMentionActiveIndex]);
            return;
        }
        if (event.key === 'Escape') {
            clearChatMentionDropdown();
            return;
        }
    }
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendChatMessage().catch(() => {});
    }
});
chatInput.addEventListener('input', updateChatMentionDropdown);
chatInput.addEventListener('click', updateChatMentionDropdown);
chatInput.addEventListener('keyup', (event) => {
    if (['ArrowDown', 'ArrowUp', 'Enter', 'Escape'].includes(event.key)) return;
    updateChatMentionDropdown();
});
document.getElementById('review-submit-btn').onclick = submitReview;
document.getElementById('review-close-btn').onclick = dismissReview;
document.getElementById('review-toggle-btn').onclick = reopenReviewModal;
sessionIdCopyButton.addEventListener('click', copyCurrentSessionId);
clearKnownAddressButton.addEventListener('click', () => {
    knownAddressInput.value = '';
    autoKnownAddressValue = '';
});
generateKnownAddressButton.addEventListener('click', () => {
    hydrateKnownAddressPrefill(true);
});
generateCallStartTimeButton.addEventListener('click', () => {
    useSessionStartTimeCheckbox.checked = false;
    prefillMockCallStartTime(true);
    updateCallStartTimeValidationState();
    updateStartSessionButtonState();
});
knownAddressInput.addEventListener('input', () => {
    if (knownAddressInput.value.trim() !== autoKnownAddressValue) {
        autoKnownAddressValue = '';
    }
});
callStartTimeInput.addEventListener('input', () => {
    if (callStartTimeInput.value.trim() !== autoCallStartTimeValue) {
        autoCallStartTimeValue = '';
    }
    updateCallStartTimeValidationState();
    updateStartSessionButtonState();
});
useSessionStartTimeCheckbox.addEventListener('change', () => {
    if (useSessionStartTimeCheckbox.checked) {
        callStartTimeInput.value = formatDisplayTimestamp(new Date());
    } else if (!callStartTimeInput.value.trim()) {
        prefillMockCallStartTime(true);
    }
    updateCallStartTimeValidationState();
    updateStartSessionButtonState();
});
document.querySelectorAll('input[name="review-correctness"]').forEach((input) => {
    input.addEventListener('change', syncReviewErrorFields);
});
terminalOutput.addEventListener('click', (event) => {
    if (Date.now() < magnifierSuppressClickUntil) {
        event.preventDefault();
        event.stopPropagation();
        return;
    }
    const referenceButton = event.target.closest('.terminal-reference-trigger');
    if (referenceButton) {
        event.preventDefault();
        event.stopPropagation();
        openIssueReferencePopover(referenceButton);
        return;
    }
    const button = event.target.closest('.terminal-turn-rewind-trigger');
    if (!button) return;
    event.preventDefault();
    if (button.dataset.rewindEnabled !== 'true') return;
    const roundIndex = Number(button.dataset.roundIndex || '0');
    const restoreCheckpointIndex = Number(button.dataset.restoreCheckpointIndex || '-1');
    if (!roundIndex) return;
    rewindFromUserRound(roundIndex, restoreCheckpointIndex);
});
terminalOutput.addEventListener('contextmenu', (event) => {
    const userTextNode = event.target.closest('.terminal-user-text');
    if (!userTextNode) {
        closeTerminalTurnMenu();
        return;
    }
    event.preventDefault();
    if (!currentSessionId || sessionBusy || sessionReviewLocked) {
        closeTerminalTurnMenu();
        return;
    }
    const roundIndex = Number(userTextNode.dataset.roundIndex || '0');
    if (!roundIndex) {
        closeTerminalTurnMenu();
        return;
    }
    openTerminalTurnMenu({
        roundIndex,
        hasAddressIeDisplay: userTextNode.dataset.hasAddressIeDisplay === 'true',
        clientX: event.clientX,
        clientY: event.clientY,
    });
});
issueReferenceCloseButton.addEventListener('click', hideIssueReferencePopover);
terminalToggleAddressIeButton.addEventListener('click', () => {
    if (!terminalTurnMenuState) return;
    toggleAddressIeDisplayForRound(
        Number(terminalTurnMenuState.roundIndex || 0),
        !terminalTurnMenuState.hasAddressIeDisplay,
    ).catch(() => {});
});
document.addEventListener('click', (event) => {
    if (issueReferencePopover.classList.contains('hidden')) return;
    const clickedInsidePopover = event.target.closest('#issue-reference-popover');
    const clickedTrigger = event.target.closest('.terminal-reference-trigger');
    if (!clickedInsidePopover && !clickedTrigger) {
        hideIssueReferencePopover();
    }
});
document.addEventListener('click', (event) => {
    if (!terminalTurnMenu || terminalTurnMenu.classList.contains('hidden')) return;
    if (event.target.closest('#terminal-turn-menu')) return;
    closeTerminalTurnMenu();
});
document.addEventListener('click', (event) => {
    if (!chatOnlineDrawerOpen) return;
    const clickedCount = event.target.closest('#chat-online-count');
    const clickedDrawer = event.target.closest('#chat-online-users');
    if (!clickedCount && !clickedDrawer) {
        setChatOnlineDrawerOpen(false);
    }
});
document.addEventListener('click', (event) => {
    if (!chatReadReceiptOpenMessageId) return;
    if (event.target.closest('.chat-readers-drawer')) return;
    if (event.target.closest('.chat-message-item.is-self.is-latest-self')) return;
    chatReadReceiptOpenMessageId = 0;
    chatReadReceiptMembers = [];
    renderChatMessages();
});
document.addEventListener('click', (event) => {
    if (chatMentionDropdown.classList.contains('hidden')) return;
    const clickedInput = event.target.closest('#chat-input');
    const clickedDropdown = event.target.closest('#chat-mention-dropdown');
    if (!clickedInput && !clickedDropdown) {
        clearChatMentionDropdown();
    }
});
document.addEventListener('click', (event) => {
    if (!chatMessageMenu || chatMessageMenu.classList.contains('hidden')) return;
    if (event.target.closest('#chat-message-menu')) return;
    closeChatMessageMenu();
});
window.addEventListener('resize', () => {
    hideIssueReferencePopover();
    resizeCursorTrailCanvas();
    if (chatOnlineDrawerOpen && chatOnlineDrawerPosition) {
        positionChatOnlineDrawer(chatOnlineDrawerPosition.clientX, chatOnlineDrawerPosition.clientY);
    }
    if (chatWindowState) {
        applyChatWindowRect();
        persistChatWindowState();
    }
    if (!chatLauncher.classList.contains('hidden')) {
        applyChatLauncherRect();
        persistChatWindowState();
    }
    if (!chatMentionDropdown.classList.contains('hidden')) {
        positionChatMentionDropdown();
    }
    if (!chatMessageMenu.classList.contains('hidden')) {
        closeChatMessageMenu();
    }
    if (!terminalTurnMenu.classList.contains('hidden')) {
        closeTerminalTurnMenu();
    }
});
window.addEventListener('pointermove', updateCursorGlow, { passive: true });
window.addEventListener('pointermove', handleChatLauncherDrag);
window.addEventListener('pointermove', handleChatDrag);
window.addEventListener('pointermove', trackChatMessageHold);
window.addEventListener('pointermove', trackTextMagnifierPointer);
window.addEventListener('pointerup', endChatLauncherDrag);
window.addEventListener('pointerup', endChatDrag);
window.addEventListener('pointerup', endChatMessageHold);
window.addEventListener('pointerup', endTextMagnifierPress);
window.addEventListener('pointercancel', endTextMagnifierPress);
window.addEventListener('pointercancel', endChatLauncherDrag);
window.addEventListener('pointercancel', endChatDrag);
window.addEventListener('pointercancel', endChatMessageHold);
window.addEventListener('pointerleave', (event) => {
    if (event.target === document.body || event.target === document.documentElement) {
        endChatLauncherDrag(event);
        endChatMessageHold(event);
        endChatDrag(event);
        endTextMagnifierPress(event);
    }
});
window.addEventListener('blur', () => {
    endChatLauncherDrag();
    endChatMessageHold();
    endChatDrag();
    closeChatMessageMenu();
    closeTerminalTurnMenu();
    hideTextMagnifier();
});
document.addEventListener('pointerleave', hideCursorGlow, true);
document.addEventListener('pointerout', (event) => {
    if (!event.relatedTarget) {
        hideCursorGlow();
    }
}, true);
document.addEventListener('visibilitychange', () => {
    if (document.hidden || !authenticatedUser) return;
    refreshChatState({ forceScroll: chatWindowState?.visible !== false }).catch(() => {});
});
document.addEventListener('pointerdown', beginTextMagnifierPress);
document.addEventListener('scroll', handleDocumentScroll, true);

sessionContextDetails.forEach((detail) => {
    detail.addEventListener('toggle', updateSessionContextDensity);
});
userInput.addEventListener('input', () => {
    if (sessionInputHistoryIndex !== -1) {
        sessionInputHistoryIndex = -1;
    }
    sessionInputDraft = userInput.value;
});
userInput.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowUp') {
        if (!sessionInputHistory.length) return;
        event.preventDefault();
        if (sessionInputHistoryIndex === -1) {
            sessionInputDraft = userInput.value;
            sessionInputHistoryIndex = sessionInputHistory.length - 1;
        } else if (sessionInputHistoryIndex > 0) {
            sessionInputHistoryIndex -= 1;
        }
        userInput.value = sessionInputHistory[sessionInputHistoryIndex] || '';
        userInput.setSelectionRange(userInput.value.length, userInput.value.length);
        return;
    }
    if (event.key === 'ArrowDown') {
        if (sessionInputHistoryIndex === -1) return;
        event.preventDefault();
        if (sessionInputHistoryIndex < sessionInputHistory.length - 1) {
            sessionInputHistoryIndex += 1;
            userInput.value = sessionInputHistory[sessionInputHistoryIndex] || '';
        } else {
            sessionInputHistoryIndex = -1;
            userInput.value = sessionInputDraft;
        }
        userInput.setSelectionRange(userInput.value.length, userInput.value.length);
        return;
    }
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
prefillMockCallStartTime(true);
updateCallStartTimeValidationState();
updateStartSessionButtonState();
resizeCursorTrailCanvas();
chatWindowState = loadChatWindowState();
resetChatRuntime();
setChatWindowVisibility(chatWindowState.visible !== false, { persist: false });
checkAuth();

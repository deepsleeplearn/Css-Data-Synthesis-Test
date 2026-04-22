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
let chatEditState = null;
let chatReplyState = null;
let sessionInputHistory = [];
let sessionInputHistoryIndex = -1;
let sessionInputDraft = '';
let terminalTurnMenuState = null;
let activeAppMode = 'manual';
let rewriteRecords = [];
let rewriteImportedRecords = [];
let rewriteSelectedIndex = -1;
let rewriteSourceName = '';
let rewriteSourceFormat = '';
let rewriteIdKeyPreference = '';
let rewriteDialogueKeyPreference = '';
let rewriteEditableLineIdCounter = 0;
let rewriteDragState = null;
const rewriteRecordEditCache = new Map();
const rewriteRecordHistoryCache = new Map();
let rewriteActiveEditSession = null;
let rewriteAvailableRoles = [];
let rewriteWorkbenchResizeState = null;
let rewriteWorkbenchRatio = 0.4;
let rewriteShellResizeState = null;
let rewriteShellLeftWidth = 320;
let rewriteShellRightWidth = 340;
let rewriteConflictFocusTimer = null;
let rewriteRecordSearchQuery = '';
const rewriteObservationLoadingLineIds = new Set();
let rewritePendingExportAction = null;
let rewriteKeyPromptState = null;
let rewriteTransferNoticeTimer = null;

const authGate = document.getElementById('auth-gate');
const appShell = document.getElementById('app-shell');
const rewriteShell = document.getElementById('rewrite-shell');
const rewriteTransferNotice = document.getElementById('rewrite-transfer-notice');
const rewriteLeftPanel = document.getElementById('rewrite-left-panel');
const rewriteRightPanel = document.getElementById('rewrite-right-panel');
const rewriteMainPanel = document.getElementById('rewrite-main-panel');
const rewriteShellLeftSplitter = document.getElementById('rewrite-shell-left-splitter');
const rewriteShellRightSplitter = document.getElementById('rewrite-shell-right-splitter');
const rewriteWorkbench = document.getElementById('rewrite-workbench');
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
const modeSwitchButton = document.getElementById('mode-switch-btn');
const reviewModal = document.getElementById('review-modal');
const rewriteExportModal = document.getElementById('rewrite-export-modal');
const rewriteKeyModal = document.getElementById('rewrite-key-modal');
const reviewCloseButton = document.getElementById('review-close-btn');
const reviewToggleButton = document.getElementById('review-toggle-btn');
const reviewSummary = document.getElementById('review-summary');
const reviewErrorFields = document.getElementById('review-error-fields');
const failedFlowStageSelect = document.getElementById('failed-flow-stage');
const reviewNotes = document.getElementById('review-notes');
const reviewPersistCheckbox = document.getElementById('review-persist-to-db');
const reviewSubmitButton = document.getElementById('review-submit-btn');
const reviewToRewriteButton = document.getElementById('review-to-rewrite-btn');
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
const chatReplyButton = document.getElementById('chat-reply-btn');
const chatEditButton = document.getElementById('chat-edit-btn');
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
const chatEditPreview = document.getElementById('chat-edit-preview');
const chatEditPreviewAuthor = document.getElementById('chat-edit-preview-author');
const chatEditPreviewText = document.getElementById('chat-edit-preview-text');
const chatEditCancelButton = document.getElementById('chat-edit-cancel-btn');
const chatReplyPreview = document.getElementById('chat-reply-preview');
const chatReplyPreviewAuthor = document.getElementById('chat-reply-preview-author');
const chatReplyPreviewText = document.getElementById('chat-reply-preview-text');
const chatReplyCancelButton = document.getElementById('chat-reply-cancel-btn');
const rewriteFileInput = document.getElementById('rewrite-file-input');
const rewriteExportButton = document.getElementById('rewrite-export-btn');
const rewriteUploadStatus = document.getElementById('rewrite-upload-status');
const rewriteRecordList = document.getElementById('rewrite-record-list');
const rewriteTitle = document.getElementById('rewrite-title');
const rewriteRecordIndicator = document.getElementById('rewrite-record-indicator');
const rewriteSubmitButton = document.getElementById('rewrite-submit-btn');
const rewriteResetButton = document.getElementById('rewrite-reset-btn');
const rewriteUndoButton = document.getElementById('rewrite-undo-btn');
const rewriteRedoButton = document.getElementById('rewrite-redo-btn');
const rewriteBackButton = document.getElementById('rewrite-back-btn');
const rewriteOriginalOutput = document.getElementById('rewrite-original-output');
const rewriteSplitter = document.getElementById('rewrite-splitter');
const rewriteScrollRegion = document.getElementById('rewrite-scroll-region');
const rewriteDialogueOutput = document.getElementById('rewrite-dialogue-output');
const rewritePrevButton = document.getElementById('rewrite-prev-btn');
const rewriteNextButton = document.getElementById('rewrite-next-btn');
const rewriteCurrentRecordLabel = document.getElementById('rewrite-current-record-label');
const rewriteFileInfo = document.getElementById('rewrite-file-info');
const rewriteRecordInfo = document.getElementById('rewrite-record-info');
const rewriteRecordSearchInput = document.getElementById('rewrite-record-search-input');
const rewriteRecordSearchStatus = document.getElementById('rewrite-record-search-status');
const rewriteAlternationStatus = document.getElementById('rewrite-alternation-status');
const rewriteAlternationBadge = document.getElementById('rewrite-alternation-badge');
const rewriteAlternationText = document.getElementById('rewrite-alternation-text');
const rewriteAlternationList = document.getElementById('rewrite-alternation-list');
const rewriteExportSummary = document.getElementById('rewrite-export-summary');
const rewriteExportStats = document.getElementById('rewrite-export-stats');
const rewriteExportCloseButton = document.getElementById('rewrite-export-close-btn');
const rewriteExportCancelButton = document.getElementById('rewrite-export-cancel-btn');
const rewriteExportConfirmButton = document.getElementById('rewrite-export-confirm-btn');
const rewriteKeyTitle = document.getElementById('rewrite-key-title');
const rewriteKeySummary = document.getElementById('rewrite-key-summary');
const rewriteKeyStats = document.getElementById('rewrite-key-stats');
const rewriteKeyInputLabel = document.getElementById('rewrite-key-input-label');
const rewriteKeyInput = document.getElementById('rewrite-key-input');
const rewriteKeyError = document.getElementById('rewrite-key-error');
const rewriteKeyCloseButton = document.getElementById('rewrite-key-close-btn');
const rewriteKeyCancelButton = document.getElementById('rewrite-key-cancel-btn');
const rewriteKeyConfirmButton = document.getElementById('rewrite-key-confirm-btn');
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
const REWRITE_RECORD_COLLECTION_KEYS = [
    'records',
    'items',
    'data',
    'dialogues',
    'conversations',
    'samples',
    'examples',
    'results',
];
const REWRITE_RECORD_ID_KEYS = [
    'scenario_id',
    'id',
    'sample_id',
    'session_id',
    'uuid',
    'record_id',
    'unique_id',
    '接入单号',
    '编号',
];
const REWRITE_DIALOGUE_KEYS = [
    'dialogue_process',
    'transcript',
    'dialogue',
    'conversation',
    'messages',
    'turns',
    'records',
    '通话记录',
    '对话记录',
    '通话',
    '对话',
];
const REWRITE_DRAG_SCROLL_EDGE_PX = 96;
const REWRITE_DRAG_SCROLL_STEP_PX = 24;
const REWRITE_HISTORY_LIMIT = 120;
const REWRITE_MIN_PANE_RATIO = 0.28;
const REWRITE_MAX_PANE_RATIO = 0.72;
const REWRITE_STACK_BREAKPOINT_PX = 1100;
const REWRITE_SHELL_LEFT_MIN_PX = 260;
const REWRITE_SHELL_LEFT_MAX_PX = 520;
const REWRITE_SHELL_RIGHT_MIN_PX = 280;
const REWRITE_SHELL_RIGHT_MAX_PX = 560;
const REWRITE_SHELL_CENTER_MIN_PX = 420;
const REWRITE_FUNCTION_CALL_ADDRESS_TARGET = 'addressInfo';
const REWRITE_FUNCTION_CALL_ADDRESS_LABEL = '地址';
const REWRITE_FUNCTION_CALL_ADDRESS_PAYLOAD = '[{"name": "ie", "arguments": {"entity_type": "addressInfo"}}]';

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

function appendDataItem(container, key, value, { filled = true } = {}) {
    if (!container) return;
    const item = document.createElement('div');
    item.className = 'data-item';

    const keyNode = document.createElement('span');
    keyNode.className = 'data-key';
    keyNode.textContent = key;

    const valueNode = document.createElement('span');
    valueNode.className = `data-value ${filled ? 'filled' : ''}`.trim();
    valueNode.textContent = value || '-';

    item.appendChild(keyNode);
    item.appendChild(valueNode);
    container.appendChild(item);
}

function setRewriteUploadStatus(message, { isError = false } = {}) {
    if (!rewriteUploadStatus) return;
    rewriteUploadStatus.textContent = message;
    rewriteUploadStatus.classList.toggle('error', Boolean(isError));
}

function closeRewriteKeyModal() {
    if (!rewriteKeyModal) return;
    rewriteKeyModal.classList.add('hidden');
    rewriteKeyModal.setAttribute('aria-hidden', 'true');
    if (rewriteKeyError) {
        rewriteKeyError.textContent = '请输入有效键名。';
        rewriteKeyError.classList.add('hidden');
    }
}

function openRewriteKeyPrompt({
    title = '补充导入键名',
    summary = '',
    label = '请输入键名',
    placeholder = '',
    candidateKeys = [],
    validate = null,
}) {
    if (!rewriteKeyModal || !rewriteKeyInput) {
        return Promise.reject(new Error('当前页面缺少导入键名补录弹框。'));
    }
    closeRewriteKeyModal();
    rewriteKeyPromptState = null;
    if (rewriteKeyTitle) rewriteKeyTitle.textContent = title;
    if (rewriteKeySummary) rewriteKeySummary.textContent = summary;
    if (rewriteKeyInputLabel) rewriteKeyInputLabel.textContent = label;
    rewriteKeyInput.value = '';
    rewriteKeyInput.placeholder = placeholder;
    if (rewriteKeyStats) {
        clearElement(rewriteKeyStats);
        if (candidateKeys.length) {
            appendDataItem(rewriteKeyStats, '可选键', candidateKeys.join('、'));
        }
    }
    rewriteKeyModal.classList.remove('hidden');
    rewriteKeyModal.setAttribute('aria-hidden', 'false');
    window.requestAnimationFrame(() => rewriteKeyInput.focus());
    return new Promise((resolve, reject) => {
        rewriteKeyPromptState = {
            resolve,
            reject,
            validate,
        };
    });
}

function confirmRewriteKeyPrompt() {
    if (!rewriteKeyPromptState || !rewriteKeyInput) return;
    const value = String(rewriteKeyInput.value || '').trim();
    const validationError = typeof rewriteKeyPromptState.validate === 'function'
        ? rewriteKeyPromptState.validate(value)
        : (!value ? '请输入有效键名。' : '');
    if (validationError) {
        if (rewriteKeyError) {
            rewriteKeyError.textContent = validationError;
            rewriteKeyError.classList.remove('hidden');
        }
        rewriteKeyInput.focus();
        return;
    }
    const { resolve } = rewriteKeyPromptState;
    rewriteKeyPromptState = null;
    closeRewriteKeyModal();
    resolve(value);
}

function cancelRewriteKeyPrompt() {
    if (!rewriteKeyPromptState) return;
    const { reject } = rewriteKeyPromptState;
    rewriteKeyPromptState = null;
    closeRewriteKeyModal();
    reject(new Error('已取消导入'));
}

function resetRewriteWorkspace() {
    rewriteRecords = [];
    rewriteImportedRecords = [];
    rewriteSelectedIndex = -1;
    rewriteSourceName = '';
    rewriteSourceFormat = '';
    rewriteIdKeyPreference = '';
    rewriteDialogueKeyPreference = '';
    rewriteEditableLineIdCounter = 0;
    rewriteDragState = null;
    rewriteActiveEditSession = null;
    rewriteAvailableRoles = [];
    rewriteRecordSearchQuery = '';
    rewriteRecordEditCache.clear();
    rewriteRecordHistoryCache.clear();
    if (rewriteFileInput) rewriteFileInput.value = '';
    if (rewriteRecordSearchInput) rewriteRecordSearchInput.value = '';
    if (rewriteTitle) rewriteTitle.textContent = '请先上传对话文件';
    if (rewriteRecordIndicator) rewriteRecordIndicator.textContent = '记录: -';
    if (rewriteCurrentRecordLabel) rewriteCurrentRecordLabel.textContent = '未选择记录';
    if (rewritePrevButton) rewritePrevButton.disabled = true;
    if (rewriteNextButton) rewriteNextButton.disabled = true;
    if (rewriteDialogueOutput) {
        rewriteDialogueOutput.innerHTML = '<p class="terminal-hint">导入文件后显示对话内容</p>';
        rewriteDialogueOutput.classList.remove('rewrite-dialogue-canvas');
        rewriteDialogueOutput.ondragover = null;
        rewriteDialogueOutput.ondrop = null;
    }
    if (rewriteOriginalOutput) {
        rewriteOriginalOutput.innerHTML = '<p class="terminal-hint">导入文件后显示原始对话内容</p>';
    }
    if (rewriteScrollRegion) {
        rewriteScrollRegion.ondragover = null;
    }
    if (rewriteSplitter) {
        rewriteSplitter.classList.remove('is-dragging');
    }
    if (rewriteShellLeftSplitter) {
        rewriteShellLeftSplitter.classList.remove('is-dragging');
    }
    if (rewriteShellRightSplitter) {
        rewriteShellRightSplitter.classList.remove('is-dragging');
    }
    if (rewriteRecordList) rewriteRecordList.innerHTML = '<div class="terminal-hint">导入文件后显示记录列表</div>';
    if (rewriteFileInfo) rewriteFileInfo.innerHTML = '<p class="terminal-hint">导入文件后显示</p>';
    if (rewriteRecordInfo) rewriteRecordInfo.innerHTML = '<p class="terminal-hint">选择记录后显示</p>';
    if (rewriteAlternationBadge) {
        rewriteAlternationBadge.textContent = '待检测';
        rewriteAlternationBadge.classList.remove('is-good', 'is-warning', 'is-error');
    }
    if (rewriteAlternationText) {
        rewriteAlternationText.textContent = '导入文件后根据右侧可编辑内容实时判断角色是否交替。';
    }
    if (rewriteAlternationList) {
        clearElement(rewriteAlternationList);
    }
    if (rewriteRecordSearchStatus) {
        rewriteRecordSearchStatus.textContent = '输入后实时筛选，回车跳到首条匹配记录。';
    }
    setRewriteUploadStatus('尚未导入文件。');
    updateRewriteHistoryButtons();
}

function updateModeSwitchButtons() {
    const canSwitch = Boolean(authenticatedUser) && !isReviewModalVisible();
    if (modeSwitchButton) modeSwitchButton.disabled = !canSwitch;
    if (rewriteBackButton) rewriteBackButton.disabled = !canSwitch;
}

function syncAppModeView() {
    const showManual = Boolean(authenticatedUser) && activeAppMode === 'manual';
    const showRewrite = Boolean(authenticatedUser) && activeAppMode === 'rewrite';
    appShell.classList.toggle('hidden', !showManual);
    rewriteShell.classList.toggle('hidden', !showRewrite);

    const showChatWindow = Boolean(authenticatedUser) && chatWindowState?.visible !== false;
    chatWindow.classList.toggle('hidden', !showChatWindow);
    chatWindow.setAttribute('aria-hidden', showChatWindow ? 'false' : 'true');
    if (showChatWindow) {
        applyChatWindowRect();
    }
    updateChatLauncher();
    updateModeSwitchButtons();
    updateRewriteHistoryButtons();
    if (showRewrite) {
        window.requestAnimationFrame(() => {
            applyRewriteShellLayout();
            applyRewriteWorkbenchRatio();
        });
    }
}

function setAppMode(mode) {
    endRewriteEditSession({ force: false });
    const nextMode = mode === 'rewrite' ? 'rewrite' : 'manual';
    activeAppMode = nextMode;
    hideIssueReferencePopover();
    closeTerminalTurnMenu();
    hideTextMagnifier();
    syncAppModeView();
}

function isPotentialRewriteTurn(value) {
    if (!value) return false;
    if (typeof value === 'string') return value.trim() !== '';
    if (typeof value !== 'object') return false;
    return [
        'speaker',
        'role',
        'text',
        'content',
        'utterance',
        'message',
        'display_kind',
    ].some((key) => key in value);
}

function normalizeRewriteRecordsPayload(payload) {
    if (Array.isArray(payload)) {
        if (payload.every((item) => isPotentialRewriteTurn(item))) {
            return [payload];
        }
        return payload;
    }
    if (!payload || typeof payload !== 'object') return [payload];

    const looksLikeSingleRecord = REWRITE_DIALOGUE_KEYS.some((key) => (
        Array.isArray(payload[key]) && payload[key].some((item) => isPotentialRewriteTurn(item))
    )) || (typeof payload.dialogue_text === 'string' && payload.dialogue_text.trim());
    if (looksLikeSingleRecord) {
        return [payload];
    }

    for (const key of REWRITE_RECORD_COLLECTION_KEYS) {
        if (Array.isArray(payload[key])) {
            return payload[key];
        }
    }

    const discoveredArray = Object.values(payload).find(
        (value) => Array.isArray(value) && value.length > 0,
    );
    if (Array.isArray(discoveredArray)) {
        return discoveredArray;
    }
    return [payload];
}

function normalizeRewriteRecordsPayloadWithPreference(payload, dialogueKeyOverride = '') {
    if (Array.isArray(payload)) {
        if (payload.every((item) => isPotentialRewriteTurn(item))) {
            return [payload];
        }
        return payload;
    }
    if (!payload || typeof payload !== 'object') return [payload];

    const candidateDialogueKeys = dialogueKeyOverride
        ? [dialogueKeyOverride, ...REWRITE_DIALOGUE_KEYS.filter((key) => key !== dialogueKeyOverride)]
        : REWRITE_DIALOGUE_KEYS;
    const looksLikeSingleRecord = candidateDialogueKeys.some((key) => (
        Array.isArray(payload[key]) && payload[key].some((item) => isPotentialRewriteTurn(item))
    )) || (typeof payload.dialogue_text === 'string' && payload.dialogue_text.trim());
    if (looksLikeSingleRecord) {
        return [payload];
    }

    for (const key of REWRITE_RECORD_COLLECTION_KEYS) {
        if (Array.isArray(payload[key])) {
            return payload[key];
        }
    }

    const discoveredArray = Object.values(payload).find(
        (value) => Array.isArray(value) && value.length > 0,
    );
    if (Array.isArray(discoveredArray)) {
        return discoveredArray;
    }
    return [payload];
}

function parseJsonlRecords(text) {
    const records = [];
    String(text || '')
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean)
        .forEach((line, index) => {
            try {
                const parsedLine = JSON.parse(line);
                if (Array.isArray(parsedLine)) {
                    if (parsedLine.every((item) => isPotentialRewriteTurn(item))) {
                        records.push(parsedLine);
                    } else {
                        records.push(...parsedLine);
                    }
                } else {
                    records.push(parsedLine);
                }
            } catch (error) {
                throw new Error(`第 ${index + 1} 行不是合法 JSON`);
            }
        });
    return records;
}

function parseRewriteSourcePayload(text, fileName = '') {
    const normalizedText = String(text || '').trim();
    if (!normalizedText) {
        throw new Error('文件内容为空');
    }

    const normalizedName = String(fileName || '').toLowerCase();
    const preferJsonl = normalizedName.endsWith('.jsonl');
    let parsed = null;
    let format = '';

    if (preferJsonl) {
        try {
            parsed = parseJsonlRecords(normalizedText);
            format = 'jsonl';
        } catch (jsonlError) {
            parsed = JSON.parse(normalizedText);
            format = 'json';
        }
    } else {
        try {
            parsed = JSON.parse(normalizedText);
            format = 'json';
        } catch (jsonError) {
            parsed = parseJsonlRecords(normalizedText);
            format = 'jsonl';
        }
    }

    return { parsed, format };
}

function parseRewriteRecords(payload, { dialogueKeyOverride = '' } = {}) {
    const records = normalizeRewriteRecordsPayloadWithPreference(payload, dialogueKeyOverride)
        .filter((item) => item !== null && item !== undefined);
    if (records.length === 0) {
        throw new Error('文件中没有可渲染的记录');
    }
    return records;
}

function extractRewriteTurns(record) {
    if (Array.isArray(record) && record.some((item) => isPotentialRewriteTurn(item))) {
        return record;
    }
    if (isPotentialRewriteTurn(record)) {
        return [record];
    }
    if (!record || typeof record !== 'object') return [];

    const candidateKeys = rewriteDialogueKeyPreference
        ? [rewriteDialogueKeyPreference, ...REWRITE_DIALOGUE_KEYS.filter((key) => key !== rewriteDialogueKeyPreference)]
        : REWRITE_DIALOGUE_KEYS;
    for (const key of candidateKeys) {
        if (Array.isArray(record[key]) && record[key].some((item) => isPotentialRewriteTurn(item))) {
            return record[key];
        }
    }

    if (typeof record.dialogue_text === 'string' && record.dialogue_text.trim()) {
        return record.dialogue_text
            .split(/\r?\n/)
            .map((line) => line.trim())
            .filter(Boolean);
    }
    return [];
}

function extractRewriteOriginalLines(record) {
    return extractRewriteTurns(record)
        .map((item, index) => normalizeRewriteLine(item, index + 1))
        .filter(Boolean);
}

function normalizeRewriteSpeaker(rawSpeaker = '') {
    const speaker = String(rawSpeaker || '').trim();
    const lowered = speaker.toLowerCase();
    if (!speaker) return '';
    if (['user', 'human', 'customer', 'caller'].includes(lowered) || speaker === '用户') {
        return '用户';
    }
    if (['service', 'assistant', 'agent', '客服'].includes(lowered) || speaker === '客服') {
        return '客服';
    }
    if (['system', 'tool', 'function_call', 'observation'].includes(lowered)) {
        return '';
    }
    return speaker;
}

function inferRewriteToneFromRole(role = '', fallbackTone = 'system') {
    if (isRewriteFunctionCallRole(role) || isRewriteObservationRole(role)) return 'system';
    const normalizedRole = normalizeRewriteSpeaker(role);
    if (normalizedRole === '用户') return 'user';
    if (normalizedRole === '客服') return 'service';
    if (!role || normalizedRole === '系统') return 'system';
    return fallbackTone || 'system';
}

function defaultRewriteRoleForTone(tone = 'system') {
    if (tone === 'user') return '用户';
    if (tone === 'service') return '客服';
    return '系统';
}

function isRewriteFunctionCallRole(role = '') {
    return String(role || '').trim().toLowerCase() === 'function_call';
}

function isRewriteObservationRole(role = '') {
    return String(role || '').trim().toLowerCase() === 'observation';
}

function extractRewriteStructuredLine(text = '', explicitKind = '') {
    const normalizedText = String(text || '').trim();
    const normalizedKind = String(explicitKind || '').trim().toLowerCase();
    if (normalizedKind === 'function_call' || normalizedText.startsWith('function_call:')) {
        return {
            tone: 'system',
            role: 'function_call',
            text: normalizedText.replace(/^function_call:\s*/i, '').trim(),
        };
    }
    if (normalizedKind === 'observation' || normalizedText.startsWith('observation:')) {
        return {
            tone: 'system',
            role: 'observation',
            text: normalizedText.replace(/^observation:\s*/i, '').trim(),
        };
    }
    return null;
}

function inferRewriteFunctionCallTarget(text = '') {
    const normalizedText = String(text || '').trim();
    return normalizedText === REWRITE_FUNCTION_CALL_ADDRESS_PAYLOAD
        ? REWRITE_FUNCTION_CALL_ADDRESS_TARGET
        : '';
}

function createDefaultRewriteObservationPayload() {
    return {
        address: '',
        error_code: '',
        error_msg: '',
    };
}

function parseRewriteObservationPayload(text = '') {
    const fallback = createDefaultRewriteObservationPayload();
    const normalizedText = String(text || '').trim();
    if (!normalizedText) {
        return fallback;
    }
    try {
        const parsed = JSON.parse(normalizedText);
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
            return {
                address: String(parsed.address ?? ''),
                error_code: String(parsed.error_code ?? ''),
                error_msg: String(parsed.error_msg ?? ''),
            };
        }
    } catch (error) {
        // Fallback to the inline observation display format.
    }

    const inlineMatch = normalizedText.match(
        /^observation\s+address:\s*(.*?);\s*error_code:\s*(.*?);\s*error_msg:\s*(.*)$/i,
    );
    if (inlineMatch) {
        return {
            address: String(inlineMatch[1] ?? '').trim(),
            error_code: String(inlineMatch[2] ?? '').trim(),
            error_msg: String(inlineMatch[3] ?? '').trim(),
        };
    }
    return {
        ...fallback,
        address: normalizedText,
    };
}

function serializeRewriteObservationPayload(payload = {}) {
    const rawErrorCode = String(payload.error_code ?? '').trim();
    const normalizedErrorCode = /^-?\d+$/.test(rawErrorCode) ? Number(rawErrorCode) : rawErrorCode;
    return JSON.stringify({
        address: String(payload.address ?? '').trim(),
        error_code: normalizedErrorCode,
        error_msg: String(payload.error_msg ?? '').trim(),
    });
}

function stripRewriteLinePrefix(text = '') {
    return String(text || '').replace(/^\[(?![\{\[])[^\]]+\]\s*/, '').trim();
}

function normalizeRewriteLine(item, fallbackIndex = 0) {
    if (typeof item === 'string') {
        const text = item.trim();
        if (!text) return null;
        const structuredLine = extractRewriteStructuredLine(text);
        if (structuredLine) {
            return structuredLine;
        }
        const turnMatch = text.match(/^\[([^\]]+)\]\s*([^:：]+)[:：]\s*(.+)$/);
        if (turnMatch) {
            const [, roundLabel, rawSpeaker, rawText] = turnMatch;
            const speaker = normalizeRewriteSpeaker(rawSpeaker);
            let tone = 'system';
            if (speaker === '用户') tone = 'user';
            if (speaker === '客服') tone = 'service';
            return {
                tone,
                role: speaker || rawSpeaker,
                text: stripRewriteLinePrefix(rawText),
            };
        }
        return {
            tone: 'system',
            role: '系统',
            text,
        };
    }
    if (!item || typeof item !== 'object') return null;

    const rawText = String(
        item.text
        ?? item.content
        ?? item.utterance
        ?? item.message
        ?? '',
    ).trim();
    if (!rawText) return null;

    const displayKind = String(item.display_kind || item.kind || '').trim().toLowerCase();
    const speaker = normalizeRewriteSpeaker(item.speaker || item.role || item.actor || item.from || '');
    const structuredLine = extractRewriteStructuredLine(rawText, displayKind);
    if (structuredLine) {
        return structuredLine;
    }

    let tone = 'system';
    if (speaker === '用户') tone = 'user';
    if (speaker === '客服') tone = 'service';
    return {
        tone,
        role: speaker || '系统',
        text: stripRewriteLinePrefix(rawText),
    };
}

function nextRewriteEditableLineId() {
    rewriteEditableLineIdCounter += 1;
    return `rewrite-line-${rewriteEditableLineIdCounter}`;
}

function createRewriteEditableLine(entry = {}) {
    const tone = String(entry.tone || 'system').trim() || 'system';
    const hasExplicitRole = Object.prototype.hasOwnProperty.call(entry, 'role');
    const fallbackRole = rewriteAvailableRoles[0] || defaultRewriteRoleForTone(tone);
    const rawRole = hasExplicitRole ? String(entry.role ?? '').trim() : fallbackRole;
    return {
        id: nextRewriteEditableLineId(),
        tone,
        role: hasExplicitRole ? rawRole : fallbackRole,
        text: String(entry.text || ''),
        metaType: String(entry.metaType || '').trim(),
    };
}

function cloneRewriteLines(lines = []) {
    return lines.map((line) => ({
        id: String(line.id || nextRewriteEditableLineId()),
        tone: String(line.tone || 'system'),
        role: String(line.role ?? ''),
        text: String(line.text ?? ''),
        metaType: String(line.metaType ?? ''),
    }));
}

function rewriteLinesSignature(lines = []) {
    return JSON.stringify(lines.map((line) => [line.id, line.tone, line.role, line.text, line.metaType]));
}

function updateRewriteRoleEditorWidth(control) {
    if (!(control instanceof HTMLInputElement) && !(control instanceof HTMLSelectElement)) return '';
    const measureSource = String(control.value || control.getAttribute('placeholder') || '角色').trim();
    const computedStyle = window.getComputedStyle(control);
    const canvas = updateRewriteRoleEditorWidth._canvas || document.createElement('canvas');
    updateRewriteRoleEditorWidth._canvas = canvas;
    const context = canvas.getContext('2d');
    if (!context) {
        const widthCh = Math.min(Math.max(measureSource.length + 2.8, 6), 14);
        control.style.width = '100%';
        return `${widthCh}ch`;
    }
    context.font = computedStyle.font || `${computedStyle.fontSize} ${computedStyle.fontFamily}`;
    const measuredTextWidth = context.measureText(measureSource || '角色').width;
    const horizontalPadding = (
        parseFloat(computedStyle.paddingLeft || '0')
        + parseFloat(computedStyle.paddingRight || '0')
        + parseFloat(computedStyle.borderLeftWidth || '0')
        + parseFloat(computedStyle.borderRightWidth || '0')
    );
    const widthPx = Math.min(Math.max(measuredTextWidth + horizontalPadding + 18, 88), 240);
    control.style.width = '100%';
    return `${Math.ceil(widthPx)}px`;
}

function updateRewriteLineBodyLayout(body, control) {
    if (!(body instanceof HTMLElement)) return;
    const widthValue = updateRewriteRoleEditorWidth(control);
    body.style.setProperty('--rewrite-role-width', widthValue);
}

function updateRewriteObservationFieldLayout(field, input, labelText = '') {
    if (!(field instanceof HTMLElement) || !(input instanceof HTMLInputElement)) return;
    const computedStyle = window.getComputedStyle(input);
    const fieldStyle = window.getComputedStyle(field);
    const canvas = updateRewriteObservationFieldLayout._canvas || document.createElement('canvas');
    updateRewriteObservationFieldLayout._canvas = canvas;
    const context = canvas.getContext('2d');
    if (!context) return;
    context.font = computedStyle.font || `${computedStyle.fontSize} ${computedStyle.fontFamily}`;
    const measureSource = String(input.value || '').trim();
    const measuredTextWidth = context.measureText(measureSource || '').width;
    const inputPadding = (
        parseFloat(computedStyle.paddingLeft || '0')
        + parseFloat(computedStyle.paddingRight || '0')
        + parseFloat(computedStyle.borderLeftWidth || '0')
        + parseFloat(computedStyle.borderRightWidth || '0')
    );
    const horizontalPadding = (
        parseFloat(fieldStyle.paddingLeft || '0')
        + parseFloat(fieldStyle.paddingRight || '0')
        + parseFloat(fieldStyle.borderLeftWidth || '0')
        + parseFloat(fieldStyle.borderRightWidth || '0')
    );
    const inputWidthPx = Math.min(Math.max(measuredTextWidth + inputPadding + 12, 28), 420);
    const labelWidthPx = context.measureText(String(labelText || '').trim()).width;
    const basisPx = Math.min(Math.max(labelWidthPx + inputWidthPx + horizontalPadding + 10, 72), 560);
    const grow = Math.max(Math.round(basisPx), 1);
    input.style.minWidth = `${Math.ceil(inputWidthPx)}px`;
    input.style.width = '100%';
    field.style.flexBasis = `${Math.ceil(basisPx)}px`;
    field.style.flexGrow = String(grow);
    field.style.flexShrink = '1';
}

function updateRewriteFunctionCallTargetWidth(control) {
    if (!(control instanceof HTMLSelectElement)) return;
    const selectedText = String(
        control.options[control.selectedIndex]?.textContent
        || control.value
        || control.getAttribute('placeholder')
        || '请选择调用项',
    ).trim();
    const computedStyle = window.getComputedStyle(control);
    const canvas = updateRewriteFunctionCallTargetWidth._canvas || document.createElement('canvas');
    updateRewriteFunctionCallTargetWidth._canvas = canvas;
    const context = canvas.getContext('2d');
    if (!context) return;
    context.font = computedStyle.font || `${computedStyle.fontSize} ${computedStyle.fontFamily}`;
    const measuredTextWidth = context.measureText(selectedText || '请选择调用项').width;
    const horizontalPadding = (
        parseFloat(computedStyle.paddingLeft || '0')
        + parseFloat(computedStyle.paddingRight || '0')
        + parseFloat(computedStyle.borderLeftWidth || '0')
        + parseFloat(computedStyle.borderRightWidth || '0')
    );
    const widthPx = Math.min(Math.max(measuredTextWidth + horizontalPadding + 22, 104), 196);
    control.style.width = `${Math.ceil(widthPx)}px`;
}

function getRewriteShellGapWidth() {
    if (!rewriteShell) return 0;
    const computedStyle = window.getComputedStyle(rewriteShell);
    const gapValue = computedStyle.columnGap || computedStyle.gap || '0';
    const gapSize = parseFloat(gapValue) || 0;
    return gapSize * 4;
}

function applyRewriteShellLayout() {
    if (!rewriteShell) return;
    if (window.innerWidth <= REWRITE_STACK_BREAKPOINT_PX) {
        rewriteShell.style.removeProperty('--rewrite-shell-left-width');
        rewriteShell.style.removeProperty('--rewrite-shell-right-width');
        if (rewriteShellLeftSplitter) {
            rewriteShellLeftSplitter.setAttribute('aria-valuenow', String(Math.round(rewriteShellLeftWidth)));
        }
        if (rewriteShellRightSplitter) {
            rewriteShellRightSplitter.setAttribute('aria-valuenow', String(Math.round(rewriteShellRightWidth)));
        }
        return;
    }

    const totalWidth = rewriteShell.clientWidth;
    const splitterWidth = (rewriteShellLeftSplitter?.offsetWidth || 0) + (rewriteShellRightSplitter?.offsetWidth || 0);
    const shellGapWidth = getRewriteShellGapWidth();
    const maxLeftByCenter = Math.min(
        REWRITE_SHELL_LEFT_MAX_PX,
        totalWidth - splitterWidth - shellGapWidth - rewriteShellRightWidth - REWRITE_SHELL_CENTER_MIN_PX,
    );
    rewriteShellLeftWidth = Math.min(
        Math.max(rewriteShellLeftWidth, REWRITE_SHELL_LEFT_MIN_PX),
        Math.max(REWRITE_SHELL_LEFT_MIN_PX, maxLeftByCenter),
    );
    const maxRightByCenter = Math.min(
        REWRITE_SHELL_RIGHT_MAX_PX,
        totalWidth - splitterWidth - shellGapWidth - rewriteShellLeftWidth - REWRITE_SHELL_CENTER_MIN_PX,
    );
    rewriteShellRightWidth = Math.min(
        Math.max(rewriteShellRightWidth, REWRITE_SHELL_RIGHT_MIN_PX),
        Math.max(REWRITE_SHELL_RIGHT_MIN_PX, maxRightByCenter),
    );

    rewriteShell.style.setProperty('--rewrite-shell-left-width', `${Math.round(rewriteShellLeftWidth)}px`);
    rewriteShell.style.setProperty('--rewrite-shell-right-width', `${Math.round(rewriteShellRightWidth)}px`);
    if (rewriteShellLeftSplitter) {
        rewriteShellLeftSplitter.setAttribute('aria-valuenow', String(Math.round(rewriteShellLeftWidth)));
    }
    if (rewriteShellRightSplitter) {
        rewriteShellRightSplitter.setAttribute('aria-valuenow', String(Math.round(rewriteShellRightWidth)));
    }
}

function updateRewriteShellWidthFromPointer(side, clientX) {
    if (!rewriteShell || !side) return;
    const shellRect = rewriteShell.getBoundingClientRect();
    const singleSplitterWidth = rewriteShellLeftSplitter?.getBoundingClientRect().width
        || rewriteShellRightSplitter?.getBoundingClientRect().width
        || 0;
    const reservedWidth = (singleSplitterWidth * 2) + getRewriteShellGapWidth();
    if (side === 'left') {
        const maxLeft = Math.min(
            REWRITE_SHELL_LEFT_MAX_PX,
            shellRect.width - reservedWidth - rewriteShellRightWidth - REWRITE_SHELL_CENTER_MIN_PX,
        );
        rewriteShellLeftWidth = Math.min(
            Math.max(clientX - shellRect.left - (singleSplitterWidth / 2), REWRITE_SHELL_LEFT_MIN_PX),
            Math.max(REWRITE_SHELL_LEFT_MIN_PX, maxLeft),
        );
    } else if (side === 'right') {
        const maxRight = Math.min(
            REWRITE_SHELL_RIGHT_MAX_PX,
            shellRect.width - reservedWidth - rewriteShellLeftWidth - REWRITE_SHELL_CENTER_MIN_PX,
        );
        rewriteShellRightWidth = Math.min(
            Math.max(shellRect.right - clientX - (singleSplitterWidth / 2), REWRITE_SHELL_RIGHT_MIN_PX),
            Math.max(REWRITE_SHELL_RIGHT_MIN_PX, maxRight),
        );
    }
    applyRewriteShellLayout();
}

function beginRewriteShellResize(side, event) {
    if (!rewriteShell || activeAppMode !== 'rewrite') return;
    if (window.innerWidth <= REWRITE_STACK_BREAKPOINT_PX) return;
    const splitter = side === 'left' ? rewriteShellLeftSplitter : rewriteShellRightSplitter;
    if (!splitter) return;
    event.preventDefault();
    rewriteShellResizeState = { side, pointerId: event.pointerId };
    splitter.classList.add('is-dragging');
    if (typeof splitter.setPointerCapture === 'function') {
        splitter.setPointerCapture(event.pointerId);
    }
    updateRewriteShellWidthFromPointer(side, event.clientX);
}

function trackRewriteShellResize(event) {
    if (!rewriteShellResizeState) return;
    updateRewriteShellWidthFromPointer(rewriteShellResizeState.side, event.clientX);
}

function endRewriteShellResize(event) {
    if (!rewriteShellResizeState) return;
    const splitter = rewriteShellResizeState.side === 'left' ? rewriteShellLeftSplitter : rewriteShellRightSplitter;
    if (
        splitter
        && typeof splitter.releasePointerCapture === 'function'
        && event?.pointerId !== undefined
        && splitter.hasPointerCapture?.(event.pointerId)
    ) {
        splitter.releasePointerCapture(event.pointerId);
    }
    rewriteShellResizeState = null;
    if (rewriteShellLeftSplitter) rewriteShellLeftSplitter.classList.remove('is-dragging');
    if (rewriteShellRightSplitter) rewriteShellRightSplitter.classList.remove('is-dragging');
}

function applyRewriteWorkbenchRatio() {
    if (!rewriteWorkbench) return;
    if (window.innerWidth <= REWRITE_STACK_BREAKPOINT_PX) {
        rewriteWorkbench.style.removeProperty('--rewrite-left-pane-width');
        rewriteWorkbench.style.removeProperty('--rewrite-right-pane-width');
        if (rewriteSplitter) {
            rewriteSplitter.setAttribute('aria-valuenow', '50');
        }
        return;
    }

    const splitterWidth = rewriteSplitter?.offsetWidth || 0;
    const availableWidth = Math.max(rewriteWorkbench.clientWidth - splitterWidth, 0);
    const normalizedRatio = Math.min(Math.max(rewriteWorkbenchRatio, REWRITE_MIN_PANE_RATIO), REWRITE_MAX_PANE_RATIO);
    const leftWidth = Math.max(Math.round(availableWidth * normalizedRatio), 0);
    const rightWidth = Math.max(availableWidth - leftWidth, 0);
    rewriteWorkbench.style.setProperty('--rewrite-left-pane-width', `${leftWidth}px`);
    rewriteWorkbench.style.setProperty('--rewrite-right-pane-width', `${rightWidth}px`);
    if (rewriteSplitter) {
        rewriteSplitter.setAttribute('aria-valuenow', String(Math.round(normalizedRatio * 100)));
    }
}

function updateRewriteWorkbenchRatioFromPointer(clientX) {
    if (!rewriteWorkbench) return;
    const rect = rewriteWorkbench.getBoundingClientRect();
    const splitterWidth = rewriteSplitter?.getBoundingClientRect().width || 0;
    const availableWidth = Math.max(rect.width - splitterWidth, 1);
    const offset = clientX - rect.left - (splitterWidth / 2);
    const nextRatio = Math.min(
        Math.max(offset / availableWidth, REWRITE_MIN_PANE_RATIO),
        REWRITE_MAX_PANE_RATIO,
    );
    rewriteWorkbenchRatio = nextRatio;
    applyRewriteWorkbenchRatio();
}

function beginRewriteWorkbenchResize(event) {
    if (!rewriteWorkbench || !rewriteSplitter || activeAppMode !== 'rewrite') return;
    if (window.innerWidth <= REWRITE_STACK_BREAKPOINT_PX) return;
    event.preventDefault();
    rewriteWorkbenchResizeState = { pointerId: event.pointerId };
    rewriteSplitter.classList.add('is-dragging');
    if (typeof rewriteSplitter.setPointerCapture === 'function') {
        rewriteSplitter.setPointerCapture(event.pointerId);
    }
    updateRewriteWorkbenchRatioFromPointer(event.clientX);
}

function trackRewriteWorkbenchResize(event) {
    if (!rewriteWorkbenchResizeState) return;
    updateRewriteWorkbenchRatioFromPointer(event.clientX);
}

function endRewriteWorkbenchResize(event) {
    if (!rewriteWorkbenchResizeState) return;
    if (
        rewriteSplitter
        && typeof rewriteSplitter.releasePointerCapture === 'function'
        && event?.pointerId !== undefined
        && rewriteSplitter.hasPointerCapture?.(event.pointerId)
    ) {
        rewriteSplitter.releasePointerCapture(event.pointerId);
    }
    rewriteWorkbenchResizeState = null;
    if (rewriteSplitter) {
        rewriteSplitter.classList.remove('is-dragging');
    }
}

function collectRewriteAvailableRoles(records = []) {
    const seen = new Set();
    const orderedRoles = [];
    records.forEach((record) => {
        extractRewriteTurns(record)
            .map((item, index) => normalizeRewriteLine(item, index + 1))
            .filter(Boolean)
            .forEach((line) => {
                const role = String(line.role || '').trim();
                if (!role || seen.has(role)) return;
                seen.add(role);
                orderedRoles.push(role);
            });
    });
    if (!orderedRoles.length) {
        return ['用户', '客服', '系统', 'function_call', 'observation'];
    }
    ['function_call', 'observation'].forEach((role) => {
        if (seen.has(role)) return;
        seen.add(role);
        orderedRoles.push(role);
    });
    return orderedRoles;
}

function evaluateRewriteRoleAlternation(lines = []) {
    const functionCallConflicts = lines
        .map((line, index) => ({ line, index }))
        .filter(({ line }) => isRewriteFunctionCallRole(line?.role || ''))
        .map(({ line, index }) => {
            const previousLine = index > 0 ? lines[index - 1] : null;
            const previousRole = normalizeRewriteSpeaker(previousLine?.role || '');
            const previousText = String(previousLine?.text || '').trim();
            if (previousRole === '用户' && previousText) {
                return null;
            }
            return {
                index,
                previousIndex: index - 1,
            };
        })
        .filter(Boolean);

    const normalizedLines = lines
        .map((line, index) => ({
            index,
            role: normalizeRewriteSpeaker(line?.role || ''),
            text: String(line?.text || '').trim(),
        }))
        .filter((line) => line.text && line.role && line.role !== '系统');

    if (normalizedLines.length < 2) {
        if (functionCallConflicts.length) {
            const [firstConflict] = functionCallConflicts;
            const conflictIndexes = functionCallConflicts.flatMap((item) => (
                item.previousIndex >= 0 ? [item.previousIndex, item.index] : [item.index]
            ));
            const conflictItems = functionCallConflicts.map((item) => ({
                message: item.previousIndex >= 0
                    ? `第 ${item.index + 1} 行 function_call 上一行必须是“用户”`
                    : `第 ${item.index + 1} 行 function_call 前缺少用户行`,
                indexes: item.previousIndex >= 0 ? [item.previousIndex, item.index] : [item.index],
            }));
            return {
                state: 'error',
                badge: '存在结构错误',
                text: firstConflict.previousIndex >= 0
                    ? `第 ${firstConflict.index + 1} 行 function_call 上一行必须是“用户”。`
                    : `第 ${firstConflict.index + 1} 行 function_call 前缺少用户行。`,
                conflictIndexes: [...new Set(conflictIndexes)],
                conflictMessages: conflictItems.map((item) => item.message),
                conflictItems,
            };
        }
        return {
            state: 'warning',
            badge: '待形成交替',
            text: '当前有效对话行不足 2 行，暂时无法判断是否交替。',
            conflictIndexes: [],
            conflictMessages: [],
            conflictItems: [],
        };
    }

    const repeatedPairs = [];
    for (let index = 1; index < normalizedLines.length; index += 1) {
        if (normalizedLines[index].role === normalizedLines[index - 1].role) {
            repeatedPairs.push([normalizedLines[index - 1], normalizedLines[index]]);
        }
    }

    if (!repeatedPairs.length && !functionCallConflicts.length) {
        return {
            state: 'good',
            badge: '角色交替正常',
            text: `当前共检查 ${normalizedLines.length} 行有效对话，未发现连续同角色。`,
            conflictIndexes: [],
            conflictMessages: [],
            conflictItems: [],
        };
    }

    const repeatedPairItems = repeatedPairs.map(([left, right]) => ({
        message: `第 ${left.index + 1} 行和第 ${right.index + 1} 行连续为“${right.role}”`,
        indexes: [left.index, right.index],
        type: 'role-repeat',
    }));
    const functionCallItems = functionCallConflicts.map((item) => ({
        message: item.previousIndex >= 0
            ? `第 ${item.index + 1} 行 function_call 上一行必须是“用户”`
            : `第 ${item.index + 1} 行 function_call 前缺少用户行`,
        indexes: item.previousIndex >= 0 ? [item.previousIndex, item.index] : [item.index],
        type: 'function-call-placement',
    }));
    const conflictItems = [...repeatedPairItems, ...functionCallItems];
    const conflictIndexes = [...new Set(conflictItems.flatMap((item) => item.indexes))];
    const [firstConflict] = conflictItems;
    return {
        state: 'error',
        badge: '存在结构/交替异常',
        text: firstConflict.type === 'function-call-placement'
            ? firstConflict.message
            : `${firstConflict.message}，当前不满足交替。`,
        conflictIndexes,
        conflictMessages: conflictItems.map((item) => item.message),
        conflictItems,
    };
}

function focusRewriteConflictLines(indexes = []) {
    if (!rewriteDialogueOutput || !indexes.length) return;
    rewriteDialogueOutput
        .querySelectorAll('.rewrite-line-card.is-conflict-focus')
        .forEach((node) => node.classList.remove('is-conflict-focus'));
    const targetCards = indexes
        .map((index) => rewriteDialogueOutput.querySelector(`.rewrite-line-card[data-line-index="${index}"]`))
        .filter(Boolean);
    if (!targetCards.length) return;
    targetCards[0].scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
    targetCards.forEach((card) => card.classList.add('is-conflict-focus'));
    if (rewriteConflictFocusTimer) {
        window.clearTimeout(rewriteConflictFocusTimer);
    }
    rewriteConflictFocusTimer = window.setTimeout(() => {
        targetCards.forEach((card) => card.classList.remove('is-conflict-focus'));
        rewriteConflictFocusTimer = null;
    }, 1800);
}

function updateRewriteAlternationStatus(lines = []) {
    if (!rewriteAlternationBadge || !rewriteAlternationText) return;
    const summary = evaluateRewriteRoleAlternation(lines);
    rewriteAlternationBadge.textContent = summary.badge;
    rewriteAlternationText.textContent = summary.text;
    rewriteAlternationBadge.classList.remove('is-good', 'is-warning', 'is-error');
    rewriteAlternationBadge.classList.add(
        summary.state === 'good' ? 'is-good' : summary.state === 'error' ? 'is-error' : 'is-warning',
    );
    if (rewriteAlternationList) {
        clearElement(rewriteAlternationList);
        (summary.conflictItems || []).forEach((conflict) => {
            const item = document.createElement('button');
            item.type = 'button';
            item.className = 'rewrite-status-item';
            item.textContent = conflict.message;
            item.addEventListener('click', () => {
                focusRewriteConflictLines(conflict.indexes);
            });
            rewriteAlternationList.appendChild(item);
        });
    }
    return summary;
}

function buildRewriteInitialEditableLines(record) {
    const normalizedLines = extractRewriteTurns(record)
        .map((item, index) => normalizeRewriteLine(item, index + 1))
        .filter(Boolean)
        .map((entry) => createRewriteEditableLine(entry));
    return normalizedLines.length
        ? normalizedLines
        : [createRewriteEditableLine({ tone: 'system', role: '', text: '' })];
}

function buildRewriteSubmittedEditableLines(record) {
    const rewrited = Array.isArray(record?.rewrited) ? record.rewrited : [];
    const normalizedLines = rewrited
        .map((item) => {
            if (!item || typeof item !== 'object') return null;
            const role = String(item.from ?? '').trim();
            let text = '';
            if (isRewriteObservationRole(role)) {
                text = serializeRewriteObservationPayload(item.value || {});
            } else if (isRewriteFunctionCallRole(role)) {
                text = typeof item.value === 'string'
                    ? item.value
                    : JSON.stringify(item.value ?? '');
            } else {
                text = String(item.value ?? '');
            }
            return createRewriteEditableLine({
                tone: inferRewriteToneFromRole(role, 'system'),
                role,
                text,
            });
        })
        .filter(Boolean);
    return normalizedLines.length ? normalizedLines : null;
}

function buildRewriteEditableLinesForDisplay(record) {
    const submittedLines = buildRewriteSubmittedEditableLines(record);
    if (submittedLines?.length) {
        return submittedLines;
    }
    const normalizedLines = extractRewriteTurns(record)
        .map((item, index) => normalizeRewriteLine(item, index + 1))
        .filter(Boolean)
        .map((entry) => createRewriteEditableLine(entry));
    return normalizedLines.length
        ? normalizedLines
        : [createRewriteEditableLine({ tone: 'system', role: '', text: '' })];
}

function getRewriteEditableLines(record, recordIndex = rewriteSelectedIndex) {
    const cacheKey = Number(recordIndex);
    if (!Number.isInteger(cacheKey) || cacheKey < 0) return [];
    if (rewriteRecordEditCache.has(cacheKey)) {
        return rewriteRecordEditCache.get(cacheKey) || [];
    }

    const editableLines = buildRewriteEditableLinesForDisplay(record);
    rewriteRecordEditCache.set(cacheKey, cloneRewriteLines(editableLines));
    return editableLines;
}

function updateRewriteRecordLines(recordIndex, nextLines) {
    rewriteRecordEditCache.set(Number(recordIndex), cloneRewriteLines(nextLines));
}

function getRewriteRecordHistory(recordIndex) {
    const normalizedIndex = Number(recordIndex);
    if (!rewriteRecordHistoryCache.has(normalizedIndex)) {
        rewriteRecordHistoryCache.set(normalizedIndex, { undoStack: [], redoStack: [] });
    }
    return rewriteRecordHistoryCache.get(normalizedIndex);
}

function updateRewriteHistoryButtons() {
    const hasSelection = Number.isInteger(rewriteSelectedIndex) && rewriteSelectedIndex >= 0;
    const history = hasSelection ? getRewriteRecordHistory(rewriteSelectedIndex) : null;
    if (rewriteSubmitButton) rewriteSubmitButton.disabled = !hasSelection;
    if (rewriteExportButton) rewriteExportButton.disabled = rewriteRecords.length < 1;
    if (rewriteResetButton) rewriteResetButton.disabled = !hasSelection;
    if (rewriteUndoButton) rewriteUndoButton.disabled = !hasSelection || !history || history.undoStack.length < 1;
    if (rewriteRedoButton) rewriteRedoButton.disabled = !hasSelection || !history || history.redoStack.length < 1;
}

function parseRewriteFunctionCallValue(text = '') {
    const normalizedText = String(text || '').trim();
    if (!normalizedText) return '';
    try {
        return JSON.parse(normalizedText);
    } catch (error) {
        return normalizedText;
    }
}

function serializeRewriteSubmissionLine(line) {
    const role = String(line?.role ?? '').trim();
    const text = String(line?.text ?? '').trim();
    if (!role && !text) return null;
    let value = text;
    if (isRewriteObservationRole(role)) {
        value = JSON.parse(serializeRewriteObservationPayload(parseRewriteObservationPayload(text)));
    } else if (isRewriteFunctionCallRole(role)) {
        value = parseRewriteFunctionCallValue(text);
    }
    return {
        from: role,
        value,
    };
}

function buildRewriteSubmissionPayloadFromLines(lines = []) {
    return lines
        .map((line) => serializeRewriteSubmissionLine(line))
        .filter(Boolean);
}

function rewriteSubmissionSignature(items = []) {
    return JSON.stringify(items ?? []);
}

function cloneRewriteRecordData(value) {
    return value === undefined ? undefined : JSON.parse(JSON.stringify(value));
}

function getRewriteRecordStatus(record) {
    const recordIndex = rewriteRecords.indexOf(record);
    const currentLines = recordIndex >= 0
        ? getRewriteEditableLines(record, recordIndex)
        : buildRewriteInitialEditableLines(record);
    const initialLines = buildRewriteInitialEditableLines(record);
    const currentSignature = rewriteSubmissionSignature(buildRewriteSubmissionPayloadFromLines(currentLines));
    const initialSignature = rewriteSubmissionSignature(buildRewriteSubmissionPayloadFromLines(initialLines));
    const submittedSignature = Array.isArray(record?.rewrited)
        ? rewriteSubmissionSignature(record.rewrited)
        : '';

    if (!submittedSignature && currentSignature === initialSignature) {
        return '未标注';
    }
    if (submittedSignature && currentSignature === submittedSignature) {
        return '已提交';
    }
    return '未提交';
}

function summarizeRewriteRecordStatuses() {
    return rewriteRecords.reduce((summary, record) => {
        const status = getRewriteRecordStatus(record);
        if (status === '已提交') {
            summary.submitted += 1;
        } else if (status === '未提交') {
            summary.unsubmitted += 1;
        } else {
            summary.unannotated += 1;
        }
        return summary;
    }, {
        submitted: 0,
        unsubmitted: 0,
        unannotated: 0,
    });
}

function closeRewriteExportModal() {
    if (!rewriteExportModal) return;
    rewriteExportModal.classList.add('hidden');
    rewriteExportModal.setAttribute('aria-hidden', 'true');
    rewritePendingExportAction = null;
}

function openRewriteExportModal(statusSummary) {
    if (!rewriteExportModal || !rewriteExportSummary || !rewriteExportStats) return;
    clearElement(rewriteExportStats);
    rewriteExportSummary.textContent = '当前文件中存在未提交或未标注数据。强制导出时，只有“已提交”的数据会保留 rewrited，其余记录将按原始导入内容导出。';
    appendDataItem(rewriteExportStats, '已提交', String(statusSummary.submitted));
    appendDataItem(rewriteExportStats, '未提交', String(statusSummary.unsubmitted));
    appendDataItem(rewriteExportStats, '未标注', String(statusSummary.unannotated));
    rewriteExportModal.classList.remove('hidden');
    rewriteExportModal.setAttribute('aria-hidden', 'false');
}

function buildRewriteExportRecords() {
    return rewriteRecords.map((record, index) => {
        const status = getRewriteRecordStatus(record);
        const currentRecord = cloneRewriteRecordData(record);
        const importedRecord = cloneRewriteRecordData(rewriteImportedRecords[index]);
        if (status === '已提交') {
            return currentRecord;
        }
        return importedRecord ?? currentRecord;
    });
}

function submitCurrentRewriteRecord() {
    if (!Number.isInteger(rewriteSelectedIndex) || rewriteSelectedIndex < 0) return;
    const record = rewriteRecords[rewriteSelectedIndex];
    if (!record || typeof record !== 'object') return;
    const lines = getRewriteEditableLines(record, rewriteSelectedIndex);
    const validation = evaluateRewriteRoleAlternation(lines);
    if (validation.state !== 'good') {
        const details = Array.isArray(validation.conflictMessages) && validation.conflictMessages.length
            ? `\n\n${validation.conflictMessages.join('\n')}`
            : '';
        window.alert(`当前数据未通过提交校验：${validation.text}${details}`);
        return;
    }
    const rewrited = buildRewriteSubmissionPayloadFromLines(lines);
    record.rewrited = rewrited;
    renderRewriteRecordState(rewriteSelectedIndex);
    if (rewriteUploadStatus) {
        rewriteUploadStatus.textContent = `当前记录已提交改写，rewrited 共写入 ${rewrited.length} 条。`;
    }
}

function buildRewriteRecordFromSessionEntries() {
    if (!Array.isArray(sessionTerminalEntries) || sessionTerminalEntries.length < 1) return null;
    const dialogueProcess = [];
    sessionTerminalEntries.forEach((entry) => {
        if (!entry || typeof entry !== 'object') return;
        if (entry.entry_type === 'turn') {
            dialogueProcess.push({
                round_label: entry.round_label || '',
                speaker: entry.speaker || '',
                text: entry.text || '',
            });
            return;
        }
        const rawText = String(entry.text || '').trim();
        if (!rawText) return;
        if (rawText.startsWith('function_call:')) {
            dialogueProcess.push({
                display_kind: 'function_call',
                speaker: 'function_call',
                text: rawText,
            });
            return;
        }
        if (rawText.startsWith('observation:')) {
            dialogueProcess.push({
                display_kind: 'observation',
                speaker: 'observation',
                text: rawText,
            });
        }
    });
    if (!dialogueProcess.length) return null;
    return {
        session_id: currentSessionId || `manual-${Date.now()}`,
        id: currentSessionId || `manual-${Date.now()}`,
        dialogue_process: dialogueProcess,
        source: 'manual_test',
    };
}

function appendCurrentSessionToRewriteMode() {
    const record = buildRewriteRecordFromSessionEntries();
    if (!record) {
        window.alert('当前测试会话没有可转入改写模式的对话内容。');
        return;
    }
    const incomingId = resolveRewriteRecordId(record);
    if (incomingId) {
        const duplicated = rewriteRecords.some((item) => resolveRewriteRecordId(item) === incomingId);
        if (duplicated) {
            showRewriteTransferNotice(`未转入改写模式：记录 id「${incomingId}」已存在。`);
            return;
        }
    }
    rewriteImportedRecords.push(cloneRewriteRecordData(record));
    rewriteRecords.push(cloneRewriteRecordData(record));
    if (!rewriteSourceName) {
        rewriteSourceName = 'manual_session_export.json';
    }
    if (!rewriteSourceFormat) {
        rewriteSourceFormat = 'json';
    }
    rewriteAvailableRoles = collectRewriteAvailableRoles(rewriteRecords);
    dismissReview();
    setAppMode('rewrite');
    renderRewriteFileInfo();
    renderRewriteRecordList();
    const targetIndex = rewriteRecords.length - 1;
    setRewriteUploadStatus(`已将测试数据追加到改写模式，共 ${rewriteRecords.length} 条记录。`);
    selectRewriteRecord(targetIndex);
}

function buildRewriteExportContent() {
    const exportRecords = buildRewriteExportRecords();
    const format = String(rewriteSourceFormat || '').trim().toLowerCase() === 'jsonl' ? 'jsonl' : 'json';
    if (format === 'jsonl') {
        return exportRecords.map((record) => JSON.stringify(record)).join('\n');
    }
    return JSON.stringify(exportRecords, null, 2);
}

function buildRewriteExportFileName() {
    const sourceName = String(rewriteSourceName || 'rewrite_export').trim();
    const baseName = (sourceName.replace(/\.[^.]+$/, '') || 'rewrite_export').replace(/[\\/:*?"<>|]+/g, '_');
    const extension = String(rewriteSourceFormat || '').trim().toLowerCase() === 'jsonl' ? 'jsonl' : 'json';
    return `${baseName}_rewrited.${extension}`;
}

function exportRewriteFile() {
    if (!rewriteRecords.length) return;
    const statusSummary = summarizeRewriteRecordStatuses();
    if (statusSummary.unsubmitted > 0 || statusSummary.unannotated > 0) {
        rewritePendingExportAction = () => {
            closeRewriteExportModal();
            exportRewriteFileWithCurrentState();
        };
        openRewriteExportModal(statusSummary);
        return;
    }
    exportRewriteFileWithCurrentState();
}

function exportRewriteFileWithCurrentState() {
    if (!rewriteRecords.length) return;
    const statusSummary = summarizeRewriteRecordStatuses();
    if (statusSummary.unsubmitted > 0 || statusSummary.unannotated > 0) {
        // Export is intentionally selective; non-submitted records fall back to imported content.
        if (rewriteUploadStatus) {
            rewriteUploadStatus.textContent = '存在未提交或未标注数据，导出文件中仅保留已提交记录的 rewrited。';
        }
    }
    const content = buildRewriteExportContent();
    const fileName = buildRewriteExportFileName();
    const blob = new Blob([content], {
        type: String(rewriteSourceFormat || '').trim().toLowerCase() === 'jsonl'
            ? 'application/x-ndjson;charset=utf-8'
            : 'application/json;charset=utf-8',
    });
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = objectUrl;
    anchor.download = fileName;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => {
        URL.revokeObjectURL(objectUrl);
    }, 0);
    if (rewriteUploadStatus) {
        rewriteUploadStatus.textContent = `已导出编辑后文件：${fileName}`;
    }
}

function pushRewriteUndoSnapshot(recordIndex, linesSnapshot) {
    const history = getRewriteRecordHistory(recordIndex);
    const normalizedSnapshot = cloneRewriteLines(linesSnapshot);
    const signature = rewriteLinesSignature(normalizedSnapshot);
    const previousSnapshot = history.undoStack[history.undoStack.length - 1];
    if (previousSnapshot && rewriteLinesSignature(previousSnapshot) === signature) {
        return;
    }
    history.undoStack.push(normalizedSnapshot);
    if (history.undoStack.length > REWRITE_HISTORY_LIMIT) {
        history.undoStack = history.undoStack.slice(-REWRITE_HISTORY_LIMIT);
    }
    history.redoStack = [];
    updateRewriteHistoryButtons();
}

function applyRewriteLineMutation(recordIndex, nextLines, { pushHistory = true, previousLines = null } = {}) {
    const normalizedIndex = Number(recordIndex);
    const currentLines = previousLines ? cloneRewriteLines(previousLines) : cloneRewriteLines(
        getRewriteEditableLines(rewriteRecords[normalizedIndex], normalizedIndex),
    );
    const normalizedNextLines = cloneRewriteLines(nextLines);
    if (rewriteLinesSignature(currentLines) === rewriteLinesSignature(normalizedNextLines)) {
        return false;
    }
    if (pushHistory) {
        pushRewriteUndoSnapshot(normalizedIndex, currentLines);
    }
    updateRewriteRecordLines(normalizedIndex, normalizedNextLines);
    updateRewriteHistoryButtons();
    return true;
}

function beginRewriteEditSession(recordIndex, lineId, field) {
    const normalizedIndex = Number(recordIndex);
    if (normalizedIndex < 0 || !lineId || !field) return;
    if (
        rewriteActiveEditSession
        && rewriteActiveEditSession.recordIndex === normalizedIndex
        && rewriteActiveEditSession.lineId === lineId
        && rewriteActiveEditSession.field === field
    ) {
        return;
    }
    const currentLines = cloneRewriteLines(getRewriteEditableLines(rewriteRecords[normalizedIndex], normalizedIndex));
    rewriteActiveEditSession = {
        recordIndex: normalizedIndex,
        lineId,
        field,
        snapshot: currentLines,
        signature: rewriteLinesSignature(currentLines),
    };
}

function endRewriteEditSession({ force = false } = {}) {
    if (!rewriteActiveEditSession) return;
    const session = rewriteActiveEditSession;
    rewriteActiveEditSession = null;
    if (!force) {
        const currentLines = cloneRewriteLines(getRewriteEditableLines(rewriteRecords[session.recordIndex], session.recordIndex));
        if (rewriteLinesSignature(currentLines) !== session.signature) {
            pushRewriteUndoSnapshot(session.recordIndex, session.snapshot);
        }
    }
    updateRewriteHistoryButtons();
}

function undoRewriteChange() {
    if (!Number.isInteger(rewriteSelectedIndex) || rewriteSelectedIndex < 0) return;
    endRewriteEditSession({ force: false });
    const history = getRewriteRecordHistory(rewriteSelectedIndex);
    if (!history.undoStack.length) return;
    const currentLines = cloneRewriteLines(getRewriteEditableLines(rewriteRecords[rewriteSelectedIndex], rewriteSelectedIndex));
    history.redoStack.push(currentLines);
    const previousLines = history.undoStack.pop();
    updateRewriteRecordLines(rewriteSelectedIndex, previousLines);
    renderRewriteRecordState(rewriteSelectedIndex);
    updateRewriteHistoryButtons();
}

function redoRewriteChange() {
    if (!Number.isInteger(rewriteSelectedIndex) || rewriteSelectedIndex < 0) return;
    endRewriteEditSession({ force: false });
    const history = getRewriteRecordHistory(rewriteSelectedIndex);
    if (!history.redoStack.length) return;
    const currentLines = cloneRewriteLines(getRewriteEditableLines(rewriteRecords[rewriteSelectedIndex], rewriteSelectedIndex));
    history.undoStack.push(currentLines);
    const nextLines = history.redoStack.pop();
    updateRewriteRecordLines(rewriteSelectedIndex, nextLines);
    renderRewriteRecordState(rewriteSelectedIndex);
    updateRewriteHistoryButtons();
}

function resetRewriteRecordToInitial(recordIndex = rewriteSelectedIndex) {
    const normalizedIndex = Number(recordIndex);
    if (!Number.isInteger(normalizedIndex) || normalizedIndex < 0 || normalizedIndex >= rewriteRecords.length) return;
    endRewriteEditSession({ force: false });
    const record = rewriteRecords[normalizedIndex];
    if (!record) return;
    const currentLines = getRewriteEditableLines(record, normalizedIndex);
    const initialLines = buildRewriteInitialEditableLines(record);
    const didMutate = applyRewriteLineMutation(normalizedIndex, initialLines, {
        pushHistory: true,
        previousLines: currentLines,
    });
    if (!didMutate) return;
    renderRewriteRecordState(normalizedIndex);
}

function insertRewriteEmptyLine(recordIndex, anchorIndex, position = 'after') {
    const record = rewriteRecords[recordIndex];
    if (!record) return;
    const currentLines = [...getRewriteEditableLines(record, recordIndex)];
    const insertIndex = position === 'before' ? anchorIndex : anchorIndex + 1;
    currentLines.splice(insertIndex, 0, createRewriteEditableLine({
        tone: 'system',
        role: '',
        text: '',
    }));
    applyRewriteLineMutation(recordIndex, currentLines, {
        pushHistory: true,
        previousLines: getRewriteEditableLines(record, recordIndex),
    });
    renderRewriteRecordState(recordIndex);
    const insertedLine = currentLines[insertIndex];
    window.requestAnimationFrame(() => {
        const roleEditor = rewriteDialogueOutput.querySelector(`[data-line-id="${insertedLine.id}"] .rewrite-role-editor`);
        if (roleEditor instanceof HTMLSelectElement) {
            roleEditor.focus();
        }
    });
}

function deleteRewriteLine(recordIndex, lineId) {
    const record = rewriteRecords[recordIndex];
    if (!record || !lineId) return;
    const currentLines = [...getRewriteEditableLines(record, recordIndex)];
    if (currentLines.length <= 1) {
        currentLines[0] = createRewriteEditableLine({
            tone: currentLines[0]?.tone || 'system',
            role: currentLines[0]?.role || '',
            text: '',
        });
    } else {
        const targetIndex = currentLines.findIndex((line) => line.id === lineId);
        if (targetIndex < 0) return;
        currentLines.splice(targetIndex, 1);
    }
    applyRewriteLineMutation(recordIndex, currentLines, {
        pushHistory: true,
        previousLines: getRewriteEditableLines(record, recordIndex),
    });
    renderRewriteRecordState(recordIndex);
}

function updateRewriteLineText(recordIndex, lineId, text) {
    const record = rewriteRecords[recordIndex];
    if (!record) return;
    const currentLines = [...getRewriteEditableLines(record, recordIndex)];
    const target = currentLines.find((line) => line.id === lineId);
    if (!target) return;
    target.text = String(text || '');
    applyRewriteLineMutation(recordIndex, currentLines, {
        pushHistory: false,
        previousLines: getRewriteEditableLines(record, recordIndex),
    });
    updateRewriteAlternationStatus(currentLines);
}

function updateRewriteLineRole(recordIndex, lineId, role) {
    const record = rewriteRecords[recordIndex];
    if (!record) return;
    const currentLines = [...getRewriteEditableLines(record, recordIndex)];
    const target = currentLines.find((line) => line.id === lineId);
    if (!target) return;
    const normalizedRole = String(role || '').trim();
    if (!normalizedRole || !rewriteAvailableRoles.includes(normalizedRole)) return;
    target.role = normalizedRole;
    if (isRewriteFunctionCallRole(normalizedRole)) {
        const targetType = inferRewriteFunctionCallTarget(target.text);
        target.text = targetType === REWRITE_FUNCTION_CALL_ADDRESS_TARGET ? target.text : '';
    } else if (isRewriteObservationRole(normalizedRole)) {
        target.text = serializeRewriteObservationPayload(parseRewriteObservationPayload(target.text));
    }
    target.tone = inferRewriteToneFromRole(target.role, target.tone);
    applyRewriteLineMutation(recordIndex, currentLines, {
        pushHistory: true,
        previousLines: getRewriteEditableLines(record, recordIndex),
    });
    updateRewriteAlternationStatus(currentLines);
}

function updateRewriteFunctionCallTarget(recordIndex, lineId, targetType) {
    const record = rewriteRecords[recordIndex];
    if (!record) return;
    const currentLines = [...getRewriteEditableLines(record, recordIndex)];
    const targetLine = currentLines.find((line) => line.id === lineId);
    if (!targetLine || !isRewriteFunctionCallRole(targetLine.role)) return;
    const normalizedTarget = String(targetType || '').trim();
    targetLine.text = normalizedTarget === REWRITE_FUNCTION_CALL_ADDRESS_TARGET
        ? REWRITE_FUNCTION_CALL_ADDRESS_PAYLOAD
        : '';
    applyRewriteLineMutation(recordIndex, currentLines, {
        pushHistory: true,
        previousLines: getRewriteEditableLines(record, recordIndex),
    });
    renderRewriteRecordState(recordIndex);
}

function updateRewriteObservationField(recordIndex, lineId, field, value) {
    const record = rewriteRecords[recordIndex];
    if (!record) return;
    const currentLines = [...getRewriteEditableLines(record, recordIndex)];
    const targetLine = currentLines.find((line) => line.id === lineId);
    if (!targetLine || !isRewriteObservationRole(targetLine.role)) return;
    const nextPayload = {
        ...parseRewriteObservationPayload(targetLine.text),
        [field]: String(value ?? ''),
    };
    targetLine.text = serializeRewriteObservationPayload(nextPayload);
    applyRewriteLineMutation(recordIndex, currentLines, {
        pushHistory: false,
        previousLines: getRewriteEditableLines(record, recordIndex),
    });
}

function buildRewriteAddressObservationContextLines(recordIndex, functionCallLineId) {
    const record = rewriteRecords[recordIndex];
    if (!record) return [];
    const currentLines = getRewriteEditableLines(record, recordIndex);
    const stopIndex = currentLines.findIndex((line) => line.id === functionCallLineId);
    if (stopIndex < 0) return [];
    return currentLines
        .slice(0, stopIndex)
        .map((line) => ({
            role: normalizeRewriteSpeaker(line?.role || ''),
            text: String(line?.text || '').trim(),
        }))
        .filter((line) => line.text && (line.role === '用户' || line.role === '客服'))
        .map((line) => `${line.role}：${line.text}`);
}

async function generateRewriteObservationLine(recordIndex, functionCallLineId) {
    const record = rewriteRecords[recordIndex];
    if (!record) return;
    if (rewriteObservationLoadingLineIds.has(functionCallLineId)) return;
    const currentLines = [...getRewriteEditableLines(record, recordIndex)];
    const functionCallIndex = currentLines.findIndex((line) => line.id === functionCallLineId);
    if (functionCallIndex < 0) return;
    const functionCallLine = currentLines[functionCallIndex];
    if (!isRewriteFunctionCallRole(functionCallLine.role)) return;
    if (inferRewriteFunctionCallTarget(functionCallLine.text) !== REWRITE_FUNCTION_CALL_ADDRESS_TARGET) {
        window.alert('请先为 function_call 选择“地址”调用项。');
        return;
    }

    const dialogueLines = buildRewriteAddressObservationContextLines(recordIndex, functionCallLineId);
    if (!dialogueLines.length) {
        window.alert('请先在 function_call 上方保留用户/客服对话内容。');
        return;
    }

    rewriteObservationLoadingLineIds.add(functionCallLineId);
    renderRewriteRecordState(recordIndex);
    try {
        const data = await apiFetch('/api/rewrite/address-observation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dialogue_lines: dialogueLines }),
        });
        const observation = data?.observation ?? {};
        const observationText = serializeRewriteObservationPayload(observation);
        const nextLines = [...currentLines];
        let observationIndex = functionCallIndex + 1;
        const nextLine = nextLines[observationIndex];
        if (nextLine && isRewriteObservationRole(nextLine.role)) {
            nextLine.text = observationText;
        } else {
            nextLines.splice(observationIndex, 0, createRewriteEditableLine({
                tone: 'system',
                role: 'observation',
                text: observationText,
            }));
        }
        observationIndex = functionCallIndex + 1;
        while (nextLines[observationIndex + 1] && String(nextLines[observationIndex + 1].metaType || '') === 'observation-summary') {
            nextLines.splice(observationIndex + 1, 1);
        }
        applyRewriteLineMutation(recordIndex, nextLines, {
            pushHistory: true,
            previousLines: getRewriteEditableLines(record, recordIndex),
        });
        renderRewriteRecordState(recordIndex);
    } catch (error) {
        window.alert(error?.message || '生成 observation 失败，请稍后重试。');
    } finally {
        rewriteObservationLoadingLineIds.delete(functionCallLineId);
        renderRewriteRecordState(recordIndex);
    }
}

function renderRewriteRecordState(recordIndex) {
    const record = rewriteRecords[recordIndex];
    if (!record) return;
    const lines = getRewriteEditableLines(record, recordIndex);
    renderRewriteRecordList();
    renderRewriteRecordInfo(record);
    renderRewriteOriginalData(record);
    renderRewriteDialogue(record);
    updateRewriteAlternationStatus(lines);
    updateRewriteHistoryButtons();
}

function maybeAutoScrollRewriteRegion(clientY) {
    if (!rewriteScrollRegion || !rewriteDragState) return;
    const rect = rewriteScrollRegion.getBoundingClientRect();
    if (clientY < rect.top || clientY > rect.bottom) return;
    const distanceToTop = clientY - rect.top;
    const distanceToBottom = rect.bottom - clientY;
    if (distanceToTop < REWRITE_DRAG_SCROLL_EDGE_PX) {
        const ratio = (REWRITE_DRAG_SCROLL_EDGE_PX - distanceToTop) / REWRITE_DRAG_SCROLL_EDGE_PX;
        rewriteScrollRegion.scrollTop -= Math.ceil(REWRITE_DRAG_SCROLL_STEP_PX * Math.max(ratio, 0.35));
    } else if (distanceToBottom < REWRITE_DRAG_SCROLL_EDGE_PX) {
        const ratio = (REWRITE_DRAG_SCROLL_EDGE_PX - distanceToBottom) / REWRITE_DRAG_SCROLL_EDGE_PX;
        rewriteScrollRegion.scrollTop += Math.ceil(REWRITE_DRAG_SCROLL_STEP_PX * Math.max(ratio, 0.35));
    }
}

function moveRewriteLine(recordIndex, sourceLineId, targetLineId, position = 'after') {
    if (!sourceLineId || !targetLineId || sourceLineId === targetLineId) return;
    const record = rewriteRecords[recordIndex];
    if (!record) return;
    const currentLines = [...getRewriteEditableLines(record, recordIndex)];
    const sourceIndex = currentLines.findIndex((line) => line.id === sourceLineId);
    const targetIndex = currentLines.findIndex((line) => line.id === targetLineId);
    if (sourceIndex < 0 || targetIndex < 0) return;

    const [movedLine] = currentLines.splice(sourceIndex, 1);
    let insertionIndex = targetIndex;
    if (sourceIndex < targetIndex) {
        insertionIndex -= 1;
    }
    if (position === 'after') {
        insertionIndex += 1;
    }
    insertionIndex = Math.max(0, Math.min(insertionIndex, currentLines.length));
    currentLines.splice(insertionIndex, 0, movedLine);
    applyRewriteLineMutation(recordIndex, currentLines, {
        pushHistory: true,
        previousLines: getRewriteEditableLines(record, recordIndex),
    });
    renderRewriteRecordState(recordIndex);
}

function moveRewriteLineToEnd(recordIndex, sourceLineId) {
    if (!sourceLineId) return;
    const record = rewriteRecords[recordIndex];
    if (!record) return;
    const currentLines = [...getRewriteEditableLines(record, recordIndex)];
    const sourceIndex = currentLines.findIndex((line) => line.id === sourceLineId);
    if (sourceIndex < 0 || sourceIndex === currentLines.length - 1) return;
    const [movedLine] = currentLines.splice(sourceIndex, 1);
    currentLines.push(movedLine);
    applyRewriteLineMutation(recordIndex, currentLines, {
        pushHistory: true,
        previousLines: getRewriteEditableLines(record, recordIndex),
    });
    renderRewriteRecordState(recordIndex);
}

function findRewritePreferenceSampleRecord(payload) {
    const coarseRecords = normalizeRewriteRecordsPayloadWithPreference(payload, '');
    return coarseRecords.find((item) => item && typeof item === 'object' && !Array.isArray(item)) || null;
}

function detectRewriteCandidateKeys(record, candidates, matcher) {
    if (!record || typeof record !== 'object' || Array.isArray(record)) return [];
    return candidates.filter((key) => {
        if (!Object.prototype.hasOwnProperty.call(record, key)) return false;
        const value = record[key];
        return typeof matcher === 'function' ? matcher(value) : true;
    });
}

async function resolveRewriteImportPreferences(payload) {
    const sampleRecord = findRewritePreferenceSampleRecord(payload);
    rewriteIdKeyPreference = '';
    rewriteDialogueKeyPreference = '';
    if (!sampleRecord) return;

    const availableKeys = Object.keys(sampleRecord);
    const matchedIdKeys = detectRewriteCandidateKeys(sampleRecord, REWRITE_RECORD_ID_KEYS, (value) => String(value ?? '').trim());
    if (matchedIdKeys.length === 1) {
        rewriteIdKeyPreference = matchedIdKeys[0];
    } else {
        rewriteIdKeyPreference = await openRewriteKeyPrompt({
            title: '指定记录 ID 键名',
            summary: matchedIdKeys.length > 1
                ? '当前记录里命中了多个编号候选键，请手动指定哪一个键表示记录 id。'
                : '当前记录里没有命中默认编号候选键，请手动输入表示记录 id 的键名。',
            label: '记录 id 键名',
            placeholder: '例如：id / unique_id / 接入单号',
            candidateKeys: availableKeys,
            validate: (value) => {
                if (!value) return '请输入表示记录 id 的键名。';
                if (!availableKeys.includes(value)) return '输入的键名不在当前记录中，请重新输入。';
                return '';
            },
        });
    }

    const matchedDialogueKeys = detectRewriteCandidateKeys(
        sampleRecord,
        REWRITE_DIALOGUE_KEYS,
        (value) => (
            (Array.isArray(value) && value.some((item) => isPotentialRewriteTurn(item)))
            || (typeof value === 'string' && value.trim())
        ),
    );
    if (matchedDialogueKeys.length === 1) {
        rewriteDialogueKeyPreference = matchedDialogueKeys[0];
    } else {
        rewriteDialogueKeyPreference = await openRewriteKeyPrompt({
            title: '指定对话内容键名',
            summary: matchedDialogueKeys.length > 1
                ? '当前记录里命中了多个对话候选键，请手动指定哪一个键保存了对话内容。'
                : '当前记录里没有命中默认对话候选键，请手动输入保存对话内容的键名。',
            label: '对话内容键名',
            placeholder: '例如：dialogue_process / 对话记录',
            candidateKeys: availableKeys,
            validate: (value) => {
                if (!value) return '请输入保存对话内容的键名。';
                if (!availableKeys.includes(value)) return '输入的键名不在当前记录中，请重新输入。';
                const candidateValue = sampleRecord[value];
                const isValid = (
                    (Array.isArray(candidateValue) && candidateValue.some((item) => isPotentialRewriteTurn(item)))
                    || (typeof candidateValue === 'string' && candidateValue.trim())
                );
                return isValid ? '' : '该键对应的值不是可识别的对话内容。';
            },
        });
    }
}

function buildRewriteRecordTitle(record, index) {
    const preferred = resolveRewriteRecordId(record);
    if (preferred) return preferred;
    return `记录 ${index + 1}`;
}

function resolveRewriteRecordId(record) {
    if (!record || typeof record !== 'object') return '';
    const preferred = [
        rewriteIdKeyPreference ? record[rewriteIdKeyPreference] : '',
        ...REWRITE_RECORD_ID_KEYS.map((key) => record[key]),
    ].find((value) => String(value || '').trim());
    return preferred ? String(preferred).trim() : '';
}

function showRewriteTransferNotice(message) {
    if (!rewriteTransferNotice) return;
    rewriteTransferNotice.textContent = String(message || '').trim();
    rewriteTransferNotice.classList.remove('hidden');
    rewriteTransferNotice.classList.add('is-visible');
    if (rewriteTransferNoticeTimer) {
        window.clearTimeout(rewriteTransferNoticeTimer);
    }
    rewriteTransferNoticeTimer = window.setTimeout(() => {
        rewriteTransferNotice.classList.remove('is-visible');
        rewriteTransferNotice.classList.add('hidden');
        rewriteTransferNoticeTimer = null;
    }, 3000);
}

function buildRewriteSourceTitle() {
    const fileName = String(rewriteSourceName || '').trim();
    if (!fileName) return '请先上传对话文件';
    return fileName.replace(/\.[^.]+$/, '') || fileName;
}

function buildRewriteRecordMeta(record) {
    const recordIndex = rewriteRecords.indexOf(record);
    const turns = recordIndex >= 0
        ? getRewriteEditableLines(record, recordIndex)
        : extractRewriteTurns(record);
    const sourceValidation = evaluateRewriteRoleAlternation(buildRewriteInitialEditableLines(record));
    return {
        turns: turns.length,
        status: getRewriteRecordStatus(record),
        sourceValidation,
        hasSourceIssue: sourceValidation.state !== 'good',
    };
}

function buildRewriteRecordSearchText(record, index) {
    const meta = buildRewriteRecordMeta(record);
    const searchParts = [
        buildRewriteRecordTitle(record, index),
        String(index + 1),
        meta.status,
    ];
    if (record && typeof record === 'object') {
        [
            ...REWRITE_RECORD_ID_KEYS.map((key) => record[key]),
            record.rounds_used,
        ].forEach((value) => {
            const normalized = String(value ?? '').trim();
            if (normalized) {
                searchParts.push(normalized);
            }
        });
    }
    return searchParts.join(' ').toLowerCase();
}

function buildRewriteStatusClass(status = '') {
    const normalizedStatus = String(status || '').trim();
    if (normalizedStatus === '已提交') return 'is-submitted';
    if (normalizedStatus === '未提交') return 'is-pending';
    return 'is-unannotated';
}

function getFilteredRewriteRecordIndexes() {
    const query = String(rewriteRecordSearchQuery || '').trim().toLowerCase();
    if (!query) {
        return rewriteRecords.map((_, index) => index);
    }
    return rewriteRecords
        .map((record, index) => ({ record, index }))
        .filter(({ record, index }) => buildRewriteRecordSearchText(record, index).includes(query))
        .map(({ index }) => index);
}

function renderRewriteRecordList() {
    clearElement(rewriteRecordList);
    if (!rewriteRecords.length) {
        rewriteRecordList.innerHTML = '<div class="terminal-hint">导入文件后显示记录列表</div>';
        if (rewriteRecordSearchStatus) {
            rewriteRecordSearchStatus.textContent = '输入后实时筛选，回车跳到首条匹配记录。';
        }
        return;
    }

    const matchedIndexes = getFilteredRewriteRecordIndexes();
    if (rewriteRecordSearchStatus) {
        const query = String(rewriteRecordSearchQuery || '').trim();
        rewriteRecordSearchStatus.textContent = query
            ? `当前匹配 ${matchedIndexes.length} 条记录，回车跳到首条匹配。`
            : `当前共 ${rewriteRecords.length} 条记录，输入后实时筛选。`;
    }
    if (!matchedIndexes.length) {
        rewriteRecordList.innerHTML = '<div class="terminal-hint">没有匹配到对应记录。</div>';
        return;
    }

    matchedIndexes.forEach((index) => {
        const record = rewriteRecords[index];
        const meta = buildRewriteRecordMeta(record);
        const statusClass = buildRewriteStatusClass(meta.status);
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'scenario-item';
        if (meta.hasSourceIssue) {
            button.classList.add('is-invalid-source');
            button.title = `原始对话未通过当前结构校验：${meta.sourceValidation.text}`;
        }
        if (index === rewriteSelectedIndex) {
            button.classList.add('active');
        }
        button.innerHTML = `
            <span class="scenario-title">${escapeHtml(buildRewriteRecordTitle(record, index))}</span>
            <span class="scenario-meta">第 ${index + 1} 条</span>
            <span class="scenario-meta">轮次/行数：${meta.turns}</span>
            <span class="scenario-issue ${statusClass}">状态：${escapeHtml(meta.status)}</span>
        `;
        button.addEventListener('click', () => {
            selectRewriteRecord(index);
        });
        rewriteRecordList.appendChild(button);
    });
}

function renderRewriteFileInfo() {
    clearElement(rewriteFileInfo);
    if (!rewriteRecords.length) {
        rewriteFileInfo.innerHTML = '<p class="terminal-hint">导入文件后显示</p>';
        return;
    }
    appendDataItem(rewriteFileInfo, '文件名', rewriteSourceName || '-');
    appendDataItem(rewriteFileInfo, '格式', rewriteSourceFormat || '-');
    appendDataItem(rewriteFileInfo, '记录数', String(rewriteRecords.length));
}

function renderRewriteRecordInfo(record) {
    clearElement(rewriteRecordInfo);
    if (!record) {
        rewriteRecordInfo.innerHTML = '<p class="terminal-hint">选择记录后显示</p>';
        return;
    }

    appendDataItem(rewriteRecordInfo, '标题', buildRewriteRecordTitle(record, rewriteSelectedIndex));
    const meta = buildRewriteRecordMeta(record);
    appendDataItem(rewriteRecordInfo, '轮次/行数', String(meta.turns));
    appendDataItem(rewriteRecordInfo, '状态', meta.status);

    if (record && typeof record === 'object') {
        [
            ...(rewriteIdKeyPreference && Object.prototype.hasOwnProperty.call(record, rewriteIdKeyPreference)
                ? [[rewriteIdKeyPreference, record[rewriteIdKeyPreference]]]
                : []),
            ...REWRITE_RECORD_ID_KEYS.map((key) => [key, record[key]]),
            ['rounds_used', record.rounds_used],
        ].forEach(([key, value]) => {
            const normalized = String(value ?? '').trim();
            if (normalized) {
                appendDataItem(rewriteRecordInfo, key, normalized);
            }
        });
    }
}

function renderRewriteOriginalData(record) {
    if (!rewriteOriginalOutput) return;
    clearElement(rewriteOriginalOutput);
    if (!record) {
        rewriteOriginalOutput.innerHTML = '<p class="terminal-hint">选择记录后显示原始对话内容</p>';
        return;
    }

    const lines = extractRewriteOriginalLines(record);
    if (!lines.length) {
        rewriteOriginalOutput.innerHTML = '<p class="terminal-hint">当前记录里没有找到可渲染的原始对话内容。</p>';
        return;
    }

    lines.forEach((entry, index) => {
        const row = document.createElement('article');
        row.className = `rewrite-original-line ${entry.tone || 'system'}`;
        const displayText = stripRewriteLinePrefix(entry.text || '');

        const lineIndex = document.createElement('span');
        lineIndex.className = 'rewrite-original-index';
        lineIndex.textContent = `${index + 1}.`;

        const role = document.createElement('span');
        role.className = 'rewrite-original-role';
        role.textContent = `${entry.role || defaultRewriteRoleForTone(entry.tone)}:`;

        const text = document.createElement('span');
        text.className = 'rewrite-original-text';
        text.textContent = displayText;

        row.setAttribute('aria-label', `第 ${index + 1} 行`);
        row.appendChild(lineIndex);
        row.appendChild(role);
        row.appendChild(text);
        rewriteOriginalOutput.appendChild(row);
    });
}

function renderRewriteDialogue(record) {
    clearElement(rewriteDialogueOutput);
    const recordIndex = rewriteSelectedIndex;
    const lines = getRewriteEditableLines(record, recordIndex);
    const alternationSummary = evaluateRewriteRoleAlternation(lines);
    const conflictIndexSet = new Set(alternationSummary.conflictIndexes || []);
    if (!lines.length) {
        rewriteDialogueOutput.classList.remove('rewrite-dialogue-canvas');
        rewriteDialogueOutput.ondragover = null;
        rewriteDialogueOutput.ondrop = null;
        if (rewriteScrollRegion) rewriteScrollRegion.ondragover = null;
        rewriteDialogueOutput.innerHTML = '<p class="terminal-hint">当前记录里没有找到可渲染的对话数组。</p>';
        return;
    }

    rewriteDialogueOutput.classList.add('rewrite-dialogue-canvas');
    lines.forEach((entry, index) => {
        const card = document.createElement('article');
        card.className = `rewrite-line-card ${entry.tone || 'system'}`;
        if (conflictIndexSet.has(index)) {
            card.classList.add('is-role-conflict');
        }
        card.dataset.lineId = entry.id;
        card.dataset.lineIndex = String(index);

        const toolbar = document.createElement('div');
        toolbar.className = 'rewrite-line-toolbar';

        const meta = document.createElement('div');
        meta.className = 'rewrite-line-meta';
        meta.textContent = `第 ${index + 1} 行`;

        const actions = document.createElement('div');
        actions.className = 'rewrite-line-actions';

        const addBeforeButton = document.createElement('button');
        addBeforeButton.type = 'button';
        addBeforeButton.className = 'rewrite-line-action-btn';
        addBeforeButton.textContent = '↑插';
        addBeforeButton.addEventListener('click', () => {
            insertRewriteEmptyLine(recordIndex, index, 'before');
        });

        const addAfterButton = document.createElement('button');
        addAfterButton.type = 'button';
        addAfterButton.className = 'rewrite-line-action-btn';
        addAfterButton.textContent = '↓插';
        addAfterButton.addEventListener('click', () => {
            insertRewriteEmptyLine(recordIndex, index, 'after');
        });

        const deleteButton = document.createElement('button');
        deleteButton.type = 'button';
        deleteButton.className = 'rewrite-line-action-btn';
        deleteButton.textContent = '删除';
        deleteButton.addEventListener('click', () => {
            deleteRewriteLine(recordIndex, entry.id);
        });

        const dragHandle = document.createElement('div');
        dragHandle.className = 'rewrite-line-drag-handle';
        dragHandle.textContent = '拖拽';
        dragHandle.draggable = true;
        dragHandle.addEventListener('dragstart', (event) => {
            rewriteDragState = { lineId: entry.id, sourceIndex: index };
            card.classList.add('is-dragging');
            if (event.dataTransfer) {
                event.dataTransfer.effectAllowed = 'move';
                event.dataTransfer.setData('text/plain', entry.id);
            }
        });
        dragHandle.addEventListener('dragend', () => {
            rewriteDragState = null;
            rewriteDialogueOutput
                .querySelectorAll('.rewrite-line-card')
                .forEach((node) => node.classList.remove('is-dragging', 'is-drop-target-before', 'is-drop-target-after'));
        });

        actions.appendChild(addBeforeButton);
        actions.appendChild(addAfterButton);
        actions.appendChild(deleteButton);
        actions.appendChild(dragHandle);
        toolbar.appendChild(meta);
        toolbar.appendChild(actions);

        const body = document.createElement('div');
        body.className = 'rewrite-line-body';
        if (isRewriteFunctionCallRole(entry.role)) {
            body.classList.add('is-function-call');
        } else if (isRewriteObservationRole(entry.role)) {
            body.classList.add('is-observation');
        }

        const roleEditor = document.createElement('select');
        roleEditor.className = 'rewrite-role-editor';
        const placeholderOption = document.createElement('option');
        placeholderOption.value = '';
        placeholderOption.textContent = '请选择';
        placeholderOption.selected = !String(entry.role ?? '').trim();
        roleEditor.appendChild(placeholderOption);
        rewriteAvailableRoles.forEach((roleOption) => {
            const option = document.createElement('option');
            option.value = roleOption;
            option.textContent = roleOption;
            option.selected = roleOption === (entry.role ?? defaultRewriteRoleForTone(entry.tone));
            roleEditor.appendChild(option);
        });
        updateRewriteLineBodyLayout(body, roleEditor);
        roleEditor.addEventListener('change', (event) => {
            updateRewriteLineBodyLayout(body, event.target);
            updateRewriteLineRole(recordIndex, entry.id, event.target.value);
            renderRewriteRecordState(recordIndex);
        });

        let contentNode = null;
        if (isRewriteFunctionCallRole(entry.role)) {
            const functionCallBody = document.createElement('div');
            functionCallBody.className = 'rewrite-function-call-body';

            const functionCallTarget = document.createElement('select');
            functionCallTarget.className = 'rewrite-role-editor rewrite-function-call-target';
            const emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = '请选择调用项';
            functionCallTarget.appendChild(emptyOption);
            const addressOption = document.createElement('option');
            addressOption.value = REWRITE_FUNCTION_CALL_ADDRESS_TARGET;
            addressOption.textContent = REWRITE_FUNCTION_CALL_ADDRESS_LABEL;
            functionCallTarget.appendChild(addressOption);
            functionCallTarget.value = inferRewriteFunctionCallTarget(entry.text);
            updateRewriteFunctionCallTargetWidth(functionCallTarget);
            functionCallTarget.addEventListener('change', (event) => {
                updateRewriteFunctionCallTargetWidth(event.target);
                updateRewriteFunctionCallTarget(recordIndex, entry.id, event.target.value);
            });

            const readonlyEditor = document.createElement('textarea');
            readonlyEditor.className = 'rewrite-line-editor is-readonly is-function-call-payload';
            readonlyEditor.rows = 1;
            readonlyEditor.readOnly = true;
            readonlyEditor.value = entry.text || '';
            readonlyEditor.placeholder = '选择调用项后自动填充 function_call 参数';

            const generateButton = document.createElement('button');
            generateButton.type = 'button';
            generateButton.className = 'rewrite-line-action-btn rewrite-line-action-btn--accent';
            const isObservationLoading = rewriteObservationLoadingLineIds.has(entry.id);
            generateButton.textContent = isObservationLoading ? '*' : '调用';
            if (isObservationLoading) {
                generateButton.classList.add('is-loading');
            }
            generateButton.disabled = isObservationLoading || functionCallTarget.value !== REWRITE_FUNCTION_CALL_ADDRESS_TARGET;
            generateButton.addEventListener('click', () => {
                generateRewriteObservationLine(recordIndex, entry.id);
            });

            actions.appendChild(generateButton);
            functionCallBody.appendChild(functionCallTarget);
            functionCallBody.appendChild(readonlyEditor);
            contentNode = functionCallBody;
        } else if (isRewriteObservationRole(entry.role)) {
            const observation = parseRewriteObservationPayload(entry.text);
            const observationBody = document.createElement('div');
            observationBody.className = 'rewrite-observation-body';

            [
                ['address', 'address', observation.address, '填写 observation 的地址结果'],
                ['error_code', 'error_code', observation.error_code, '填写 error_code'],
                ['error_msg', 'error_msg', observation.error_msg, '填写 error_msg'],
            ].forEach(([fieldKey, labelText, fieldValue, placeholder]) => {
                const field = document.createElement('label');
                field.className = `rewrite-observation-field rewrite-observation-field--${fieldKey}`;

                const label = document.createElement('span');
                label.className = 'rewrite-observation-label';
                label.textContent = labelText;

                const input = document.createElement('input');
                input.className = 'rewrite-observation-input';
                input.type = 'text';
                input.value = String(fieldValue ?? '');
                input.placeholder = placeholder;
                updateRewriteObservationFieldLayout(field, input, labelText);
                input.addEventListener('focus', () => {
                    beginRewriteEditSession(recordIndex, entry.id, fieldKey);
                });
                input.addEventListener('input', (event) => {
                    updateRewriteObservationFieldLayout(field, event.target, labelText);
                    updateRewriteObservationField(recordIndex, entry.id, fieldKey, event.target.value);
                });
                input.addEventListener('blur', () => {
                    endRewriteEditSession({ force: false });
                    updateRewriteHistoryButtons();
                });

                field.appendChild(label);
                field.appendChild(input);
                observationBody.appendChild(field);
            });
            contentNode = observationBody;
        } else {
            const editor = document.createElement('textarea');
            editor.className = 'rewrite-line-editor';
            editor.rows = 1;
            editor.value = stripRewriteLinePrefix(entry.text || '');
            editor.placeholder = '空框，可填写改写后的对话内容';
            editor.addEventListener('focus', () => {
                beginRewriteEditSession(recordIndex, entry.id, 'text');
            });
            editor.addEventListener('input', (event) => {
                updateRewriteLineText(recordIndex, entry.id, event.target.value);
            });
            editor.addEventListener('blur', () => {
                endRewriteEditSession({ force: false });
                updateRewriteHistoryButtons();
            });
            contentNode = editor;
        }

        card.addEventListener('dragover', (event) => {
            if (!rewriteDragState || rewriteDragState.lineId === entry.id) return;
            event.preventDefault();
            maybeAutoScrollRewriteRegion(event.clientY);
            const rect = card.getBoundingClientRect();
            const position = event.clientY < (rect.top + rect.height / 2) ? 'before' : 'after';
            card.classList.toggle('is-drop-target-before', position === 'before');
            card.classList.toggle('is-drop-target-after', position === 'after');
        });
        card.addEventListener('dragleave', () => {
            card.classList.remove('is-drop-target-before', 'is-drop-target-after');
        });
        card.addEventListener('drop', (event) => {
            if (!rewriteDragState || rewriteDragState.lineId === entry.id) return;
            event.preventDefault();
            const rect = card.getBoundingClientRect();
            const position = event.clientY < (rect.top + rect.height / 2) ? 'before' : 'after';
            moveRewriteLine(recordIndex, rewriteDragState.lineId, entry.id, position);
            rewriteDragState = null;
        });

        body.appendChild(roleEditor);
        body.appendChild(contentNode);
        card.appendChild(toolbar);
        card.appendChild(body);
        rewriteDialogueOutput.appendChild(card);
    });

    rewriteDialogueOutput.ondragover = (event) => {
        if (!rewriteDragState) return;
        event.preventDefault();
        maybeAutoScrollRewriteRegion(event.clientY);
    };
    rewriteDialogueOutput.ondrop = (event) => {
        const targetCard = event.target.closest('.rewrite-line-card');
        if (!rewriteDragState || targetCard) return;
        event.preventDefault();
        moveRewriteLineToEnd(recordIndex, rewriteDragState.lineId);
        rewriteDragState = null;
    };
    if (rewriteScrollRegion) {
        rewriteScrollRegion.ondragover = (event) => {
            if (!rewriteDragState) return;
            event.preventDefault();
            maybeAutoScrollRewriteRegion(event.clientY);
        };
    }
}

function selectRewriteRecord(index) {
    if (index < 0 || index >= rewriteRecords.length) return;
    endRewriteEditSession({ force: false });
    rewriteSelectedIndex = index;
    const record = rewriteRecords[index];
    rewriteTitle.textContent = buildRewriteSourceTitle();
    rewriteRecordIndicator.textContent = `记录: ${index + 1} / ${rewriteRecords.length}`;
    rewriteCurrentRecordLabel.textContent = `${index + 1} / ${rewriteRecords.length} · ${buildRewriteRecordTitle(record, index)}`;
    rewritePrevButton.disabled = index <= 0;
    rewriteNextButton.disabled = index >= rewriteRecords.length - 1;
    renderRewriteRecordState(index);
    applyRewriteWorkbenchRatio();
}

function selectFirstFilteredRewriteRecord() {
    const matchedIndexes = getFilteredRewriteRecordIndexes();
    if (!matchedIndexes.length) return;
    selectRewriteRecord(matchedIndexes[0]);
}

async function importRewriteFile(file) {
    if (!file) return;
    rewriteRecordEditCache.clear();
    rewriteRecordHistoryCache.clear();
    rewriteActiveEditSession = null;
    const text = await file.text();
    const { parsed, format } = parseRewriteSourcePayload(text, file.name);
    await resolveRewriteImportPreferences(parsed);
    const records = parseRewriteRecords(parsed, { dialogueKeyOverride: rewriteDialogueKeyPreference });
    rewriteImportedRecords = cloneRewriteRecordData(records) || [];
    rewriteRecords = cloneRewriteRecordData(records) || [];
    rewriteAvailableRoles = collectRewriteAvailableRoles(rewriteRecords);
    rewriteSelectedIndex = -1;
    rewriteSourceName = file.name;
    rewriteSourceFormat = format;
    renderRewriteFileInfo();
    renderRewriteRecordList();
    setRewriteUploadStatus(`已导入 ${file.name}，共 ${records.length} 条记录。`);
    selectRewriteRecord(0);
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
    updateModeSwitchButtons();
}

function isReviewModalVisible() {
    return !reviewModal.classList.contains('hidden');
}

function hideReviewModal() {
    reviewModal.classList.add('hidden');
    reviewModal.setAttribute('aria-hidden', 'true');
    updateModeSwitchButtons();
}

function showReviewModal() {
    reviewModal.classList.remove('hidden');
    reviewModal.setAttribute('aria-hidden', 'false');
    updateModeSwitchButtons();
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
    if (!chatMessageMenu || !chatReplyButton || !chatEditButton || !chatRecallButton || !messageId) return;
    const targetMessage = chatMessages.find((message) => Number(message?.id || 0) === Number(messageId || 0));
    if (!targetMessage || targetMessage.recalled) {
        closeChatMessageMenu();
        return;
    }
    const isSelf = Boolean(authenticatedUser && targetMessage.username === authenticatedUser.username);
    chatContextMenuMessageId = Number(messageId || 0);
    chatMessageMenu.classList.remove('hidden');
    chatMessageMenu.setAttribute('aria-hidden', 'false');
    chatReplyButton.disabled = false;
    chatEditButton.disabled = false;
    chatRecallButton.disabled = false;
    chatEditButton.classList.toggle('hidden', !isSelf);
    chatRecallButton.classList.toggle('hidden', !isSelf);

    const menuWidth = Math.max(chatMessageMenu.offsetWidth || 148, 132);
    const menuHeight = Math.max(chatMessageMenu.offsetHeight || (isSelf ? 140 : 54), 48);
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
    chatEditState = null;
    chatReplyState = null;
    endChatLauncherDrag();
    clearChatMessageHold();
    clearChatMentionDropdown();
    closeChatMessageMenu();
    if (chatSendButton) chatSendButton.disabled = false;
    if (chatInput) chatInput.value = '';
    renderChatEditPreview();
    renderChatReplyPreview();
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

function buildChatReplySummary(message) {
    if (!message) return null;
    const isRecalled = Boolean(message.recalled);
    return {
        messageId: Number(message.id || 0),
        author: formatChatUserHandle(message.username),
        text: isRecalled ? '--该条信息已撤回--' : String(message.text || '').trim() || '-',
        recalled: isRecalled,
    };
}

function renderChatEditPreview() {
    if (!chatEditPreview || !chatEditPreviewAuthor || !chatEditPreviewText || !chatSendButton) return;
    const targetMessage = chatMessages.find((message) => Number(message?.id || 0) === Number(chatEditState?.messageId || 0));
    if (!targetMessage || targetMessage.recalled || targetMessage.username !== authenticatedUser?.username) {
        chatEditState = null;
        chatEditPreview.classList.add('hidden');
        chatEditPreviewAuthor.textContent = '正在编辑';
        chatEditPreviewText.textContent = '编辑中的消息内容';
        chatSendButton.textContent = '发送';
        return;
    }
    chatEditPreview.classList.remove('hidden');
    chatEditPreviewAuthor.textContent = '正在编辑自己的消息';
    chatEditPreviewText.textContent = String(targetMessage.text || '').trim() || '-';
    chatSendButton.textContent = '保存';
}

function clearChatEditState({ preserveInput = false } = {}) {
    chatEditState = null;
    if (!preserveInput && chatInput) {
        chatInput.value = '';
    }
    renderChatEditPreview();
}

function setChatEditState(messageId) {
    const targetMessage = chatMessages.find((message) => Number(message?.id || 0) === Number(messageId || 0));
    if (!targetMessage || targetMessage.recalled || targetMessage.username !== authenticatedUser?.username) {
        return;
    }
    chatEditState = { messageId: Number(targetMessage.id || 0) };
    if (chatInput) {
        chatInput.value = String(targetMessage.text || '');
        chatInput.focus();
        const nextCursor = chatInput.value.length;
        chatInput.setSelectionRange(nextCursor, nextCursor);
    }
    clearChatReplyState();
    clearChatMentionDropdown();
    renderChatEditPreview();
}

function getChatReplySummaryByMessageId(messageId) {
    const normalizedMessageId = Number(messageId || 0);
    if (!normalizedMessageId) return null;
    const targetMessage = chatMessages.find((message) => Number(message?.id || 0) === normalizedMessageId);
    return buildChatReplySummary(targetMessage);
}

function renderChatReplyPreview() {
    if (!chatReplyPreview || !chatReplyPreviewAuthor || !chatReplyPreviewText) return;
    const summary = getChatReplySummaryByMessageId(chatReplyState?.messageId || 0);
    if (!summary || summary.recalled) {
        chatReplyState = null;
        chatReplyPreview.classList.add('hidden');
        chatReplyPreviewAuthor.textContent = '回复对象';
        chatReplyPreviewText.textContent = '回复内容';
        return;
    }
    chatReplyPreview.classList.remove('hidden');
    chatReplyPreviewAuthor.textContent = `回复 ${summary.author}`;
    chatReplyPreviewText.textContent = summary.text;
}

function setChatReplyState(messageId) {
    const summary = getChatReplySummaryByMessageId(messageId);
    if (!summary) {
        chatReplyState = null;
    } else {
        chatReplyState = { messageId: summary.messageId };
    }
    if (chatEditState) {
        chatEditState = null;
        renderChatEditPreview();
    }
    renderChatReplyPreview();
}

function clearChatReplyState() {
    chatReplyState = null;
    renderChatReplyPreview();
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
    const messagesById = new Map(chatMessages.map((message) => [Number(message?.id || 0), message]));
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

        const metaTail = document.createElement('span');
        metaTail.className = 'chat-message-meta-tail';
        metaTail.appendChild(author);
        if (message.edited_at) {
            const editedBadge = document.createElement('span');
            editedBadge.className = 'chat-message-edited-badge';
            editedBadge.textContent = '已编辑';
            metaTail.appendChild(editedBadge);
        }

        const text = document.createElement('p');
        text.className = 'chat-message-text';
        text.textContent = isRecalled ? '--该条信息已撤回--' : (message.text || '');
        if (isRecalled) {
            text.classList.add('is-recalled-notice');
        }

        const replyTarget = messagesById.get(Number(message.reply_to_message_id || 0));
        const replySummary = buildChatReplySummary(replyTarget);

        meta.appendChild(sentAt);
        meta.appendChild(metaTail);
        item.appendChild(meta);
        if (replySummary) {
            const reply = document.createElement('div');
            reply.className = 'chat-message-reply';

            const replyAuthor = document.createElement('span');
            replyAuthor.className = 'chat-message-reply-author';
            replyAuthor.textContent = replySummary.author;

            const replyText = document.createElement('span');
            replyText.className = 'chat-message-reply-text';
            replyText.textContent = replySummary.text;

            reply.appendChild(replyAuthor);
            reply.appendChild(replyText);
            item.appendChild(reply);
        }
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
    if (chatReplyState) {
        const replySummary = getChatReplySummaryByMessageId(chatReplyState.messageId);
        if (!replySummary || replySummary.recalled) {
            chatReplyState = null;
        }
    }
    if (chatEditState) {
        const editTarget = chatMessages.find((message) => Number(message?.id || 0) === Number(chatEditState.messageId || 0));
        if (!editTarget || editTarget.recalled || editTarget.username !== authenticatedUser?.username) {
            chatEditState = null;
        }
    }
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
    renderChatEditPreview();
    renderChatReplyPreview();
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
        if (chatEditState?.messageId) {
            const data = await apiFetch(`/api/chat/messages/${chatEditState.messageId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text }),
            });
            clearChatEditState({ preserveInput: true });
            if (chatInput) {
                chatInput.value = '';
            }
            mergeChatState(data, { forceScroll: false });
        } else {
            const data = await apiFetch('/api/chat/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text,
                    reply_to_message_id: Number(chatReplyState?.messageId || 0) || undefined,
                }),
            });
            chatInput.value = '';
            clearChatReplyState();
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
        }
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
    resetRewriteWorkspace();
}

function applyAuthenticatedState(user) {
    authenticatedUser = user;
    authUserName.textContent = user.display_name || user.username;
    authUserMeta.textContent = `备案账号：${user.username}`;
    authGate.classList.add('hidden');
    setAuthError('');
    updateCallStartTimeValidationState();
    updateStartSessionButtonState();
    initializeChatWindow();
    startChatPolling();
    syncAppModeView();
}

function applyLoggedOutState(message = '') {
    authenticatedUser = null;
    authUserName.textContent = '未登录';
    authUserMeta.textContent = '只有备案账号可访问测试台。';
    appShell.classList.add('hidden');
    rewriteShell.classList.add('hidden');
    authGate.classList.remove('hidden');
    stopChatPolling();
    resetChatRuntime();
    chatLauncher.classList.add('hidden');
    chatWindow.classList.add('hidden');
    chatWindow.setAttribute('aria-hidden', 'true');
    setPasswordVisibility(false);
    loginPassword.value = '';
    setAuthError(message);
    activeAppMode = 'manual';
    resetWorkspace();
    updateModeSwitchButtons();
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
modeSwitchButton.addEventListener('click', () => {
    if (modeSwitchButton.disabled) return;
    setAppMode('rewrite');
});
rewriteBackButton.addEventListener('click', () => {
    if (rewriteBackButton.disabled) return;
    setAppMode('manual');
});
rewriteUndoButton.addEventListener('click', () => {
    undoRewriteChange();
});
rewriteRedoButton.addEventListener('click', () => {
    redoRewriteChange();
});
if (rewriteSubmitButton) {
    rewriteSubmitButton.addEventListener('click', () => {
        submitCurrentRewriteRecord();
    });
}
if (rewriteExportButton) {
    rewriteExportButton.addEventListener('click', () => {
        exportRewriteFile();
    });
}
if (rewriteExportCloseButton) {
    rewriteExportCloseButton.addEventListener('click', () => {
        closeRewriteExportModal();
        if (rewriteUploadStatus) {
            rewriteUploadStatus.textContent = '已取消导出，存在未提交或未标注数据。';
        }
    });
}
if (rewriteExportCancelButton) {
    rewriteExportCancelButton.addEventListener('click', () => {
        closeRewriteExportModal();
        if (rewriteUploadStatus) {
            rewriteUploadStatus.textContent = '已取消导出，存在未提交或未标注数据。';
        }
    });
}
if (rewriteExportConfirmButton) {
    rewriteExportConfirmButton.addEventListener('click', () => {
        const pendingAction = rewritePendingExportAction;
        if (typeof pendingAction === 'function') {
            pendingAction();
        } else {
            closeRewriteExportModal();
        }
    });
}
if (rewriteExportModal) {
    rewriteExportModal.addEventListener('click', (event) => {
        if (event.target === rewriteExportModal || event.target.classList.contains('modal-backdrop')) {
            closeRewriteExportModal();
            if (rewriteUploadStatus) {
                rewriteUploadStatus.textContent = '已取消导出，存在未提交或未标注数据。';
            }
        }
    });
}
if (rewriteKeyCloseButton) {
    rewriteKeyCloseButton.addEventListener('click', () => {
        cancelRewriteKeyPrompt();
    });
}
if (rewriteKeyCancelButton) {
    rewriteKeyCancelButton.addEventListener('click', () => {
        cancelRewriteKeyPrompt();
    });
}
if (rewriteKeyConfirmButton) {
    rewriteKeyConfirmButton.addEventListener('click', () => {
        confirmRewriteKeyPrompt();
    });
}
if (rewriteKeyInput) {
    rewriteKeyInput.addEventListener('input', () => {
        if (rewriteKeyError) {
            rewriteKeyError.classList.add('hidden');
        }
    });
    rewriteKeyInput.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            confirmRewriteKeyPrompt();
        }
    });
}
if (rewriteKeyModal) {
    rewriteKeyModal.addEventListener('click', (event) => {
        if (event.target === rewriteKeyModal || event.target.classList.contains('modal-backdrop')) {
            cancelRewriteKeyPrompt();
        }
    });
}
rewriteFileInput.addEventListener('change', async (event) => {
    const [file] = Array.from(event.target.files || []);
    if (!file) return;
    try {
        await importRewriteFile(file);
    } catch (error) {
        resetRewriteWorkspace();
        setRewriteUploadStatus(error.message, { isError: true });
    }
});
if (rewriteRecordSearchInput) {
    rewriteRecordSearchInput.addEventListener('input', (event) => {
        rewriteRecordSearchQuery = String(event.target.value || '');
        renderRewriteRecordList();
    });
    rewriteRecordSearchInput.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter') return;
        event.preventDefault();
        selectFirstFilteredRewriteRecord();
    });
}
rewritePrevButton.addEventListener('click', () => {
    selectRewriteRecord(rewriteSelectedIndex - 1);
});
rewriteNextButton.addEventListener('click', () => {
    selectRewriteRecord(rewriteSelectedIndex + 1);
});
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
    const messageNode = event.target.closest('.chat-message-item');
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
chatReplyButton.addEventListener('click', () => {
    setChatReplyState(chatContextMenuMessageId);
    closeChatMessageMenu();
    chatInput.focus();
});
chatEditButton.addEventListener('click', () => {
    setChatEditState(chatContextMenuMessageId);
    closeChatMessageMenu();
});
chatRecallButton.addEventListener('click', () => {
    recallChatMessage(chatContextMenuMessageId).catch(() => {});
});
chatEditCancelButton.addEventListener('click', () => {
    clearChatEditState();
});
chatReplyCancelButton.addEventListener('click', clearChatReplyState);
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
if (reviewToRewriteButton) {
    reviewToRewriteButton.addEventListener('click', () => {
        appendCurrentSessionToRewriteMode();
    });
}
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
document.addEventListener('keydown', (event) => {
    if (activeAppMode !== 'rewrite') return;
    const isUndo = (event.metaKey || event.ctrlKey) && !event.shiftKey && event.key.toLowerCase() === 'z';
    const isRedo = (event.metaKey || event.ctrlKey) && (
        event.key.toLowerCase() === 'y' || (event.shiftKey && event.key.toLowerCase() === 'z')
    );
    if (!isUndo && !isRedo) return;
    const activeElement = document.activeElement;
    const isRewriteEditor = activeElement && activeElement.closest && activeElement.closest('#rewrite-dialogue-output');
    if (!isRewriteEditor && !rewriteShell.classList.contains('hidden')) {
        event.preventDefault();
        if (isUndo) undoRewriteChange();
        if (isRedo) redoRewriteChange();
        return;
    }
    event.preventDefault();
    if (isUndo) undoRewriteChange();
    if (isRedo) redoRewriteChange();
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
    applyRewriteShellLayout();
    applyRewriteWorkbenchRatio();
});
window.addEventListener('pointermove', updateCursorGlow, { passive: true });
window.addEventListener('pointermove', handleChatLauncherDrag);
window.addEventListener('pointermove', handleChatDrag);
window.addEventListener('pointermove', trackRewriteShellResize);
window.addEventListener('pointermove', trackRewriteWorkbenchResize);
window.addEventListener('pointermove', trackChatMessageHold);
window.addEventListener('pointermove', trackTextMagnifierPointer);
window.addEventListener('pointerup', endChatLauncherDrag);
window.addEventListener('pointerup', endChatDrag);
window.addEventListener('pointerup', endRewriteShellResize);
window.addEventListener('pointerup', endRewriteWorkbenchResize);
window.addEventListener('pointerup', endChatMessageHold);
window.addEventListener('pointerup', endTextMagnifierPress);
window.addEventListener('pointercancel', endTextMagnifierPress);
window.addEventListener('pointercancel', endChatLauncherDrag);
window.addEventListener('pointercancel', endChatDrag);
window.addEventListener('pointercancel', endRewriteShellResize);
window.addEventListener('pointercancel', endRewriteWorkbenchResize);
window.addEventListener('pointercancel', endChatMessageHold);
window.addEventListener('pointerleave', (event) => {
    if (event.target === document.body || event.target === document.documentElement) {
        endChatLauncherDrag(event);
        endChatMessageHold(event);
        endChatDrag(event);
        endRewriteShellResize(event);
        endRewriteWorkbenchResize(event);
        endTextMagnifierPress(event);
    }
});
window.addEventListener('blur', () => {
    endChatLauncherDrag();
    endChatMessageHold();
    endChatDrag();
    endRewriteShellResize();
    endRewriteWorkbenchResize();
    closeChatMessageMenu();
    closeTerminalTurnMenu();
    hideTextMagnifier();
});
if (rewriteSplitter) {
    rewriteSplitter.addEventListener('pointerdown', beginRewriteWorkbenchResize);
    rewriteSplitter.addEventListener('keydown', (event) => {
        if (window.innerWidth <= REWRITE_STACK_BREAKPOINT_PX) return;
        if (event.key === 'ArrowLeft') {
            event.preventDefault();
            rewriteWorkbenchRatio = Math.max(rewriteWorkbenchRatio - 0.03, REWRITE_MIN_PANE_RATIO);
            applyRewriteWorkbenchRatio();
        }
        if (event.key === 'ArrowRight') {
            event.preventDefault();
            rewriteWorkbenchRatio = Math.min(rewriteWorkbenchRatio + 0.03, REWRITE_MAX_PANE_RATIO);
            applyRewriteWorkbenchRatio();
        }
        if (event.key === 'Home') {
            event.preventDefault();
            rewriteWorkbenchRatio = REWRITE_MIN_PANE_RATIO;
            applyRewriteWorkbenchRatio();
        }
        if (event.key === 'End') {
            event.preventDefault();
            rewriteWorkbenchRatio = REWRITE_MAX_PANE_RATIO;
            applyRewriteWorkbenchRatio();
        }
    });
}
if (rewriteShellLeftSplitter) {
    rewriteShellLeftSplitter.addEventListener('pointerdown', (event) => {
        beginRewriteShellResize('left', event);
    });
    rewriteShellLeftSplitter.addEventListener('keydown', (event) => {
        if (window.innerWidth <= REWRITE_STACK_BREAKPOINT_PX) return;
        if (event.key === 'ArrowLeft') {
            event.preventDefault();
            rewriteShellLeftWidth = Math.max(rewriteShellLeftWidth - 20, REWRITE_SHELL_LEFT_MIN_PX);
            applyRewriteShellLayout();
        }
        if (event.key === 'ArrowRight') {
            event.preventDefault();
            rewriteShellLeftWidth = Math.min(rewriteShellLeftWidth + 20, REWRITE_SHELL_LEFT_MAX_PX);
            applyRewriteShellLayout();
        }
    });
}
if (rewriteShellRightSplitter) {
    rewriteShellRightSplitter.addEventListener('pointerdown', (event) => {
        beginRewriteShellResize('right', event);
    });
    rewriteShellRightSplitter.addEventListener('keydown', (event) => {
        if (window.innerWidth <= REWRITE_STACK_BREAKPOINT_PX) return;
        if (event.key === 'ArrowLeft') {
            event.preventDefault();
            rewriteShellRightWidth = Math.min(rewriteShellRightWidth + 20, REWRITE_SHELL_RIGHT_MAX_PX);
            applyRewriteShellLayout();
        }
        if (event.key === 'ArrowRight') {
            event.preventDefault();
            rewriteShellRightWidth = Math.max(rewriteShellRightWidth - 20, REWRITE_SHELL_RIGHT_MIN_PX);
            applyRewriteShellLayout();
        }
    });
}
if (rewriteResetButton) {
    rewriteResetButton.addEventListener('click', () => {
        resetRewriteRecordToInitial(rewriteSelectedIndex);
    });
}
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
resetRewriteWorkspace();
applyRewriteShellLayout();
applyRewriteWorkbenchRatio();
setChatWindowVisibility(chatWindowState.visible !== false, { persist: false });
updateModeSwitchButtons();
syncAppModeView();
checkAuth();

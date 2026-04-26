let selectedScenario = null;
let currentSessionId = null;
let currentSlotKeys = [];
let nextRoundIndex = 1;
let sessionClosed = true;
let sessionBusy = false;
let sessionReviewLocked = false;
let sessionTerminalEntries = [];
let pendingManualUserEntry = null;
let pendingManualIeDisplay = null;
let terminalProcessingState = null;
let reviewPending = false;
let reviewAvailable = false;
let reviewContext = null;
let reviewSourceMode = 'manual';
let authenticatedUser = null;
let sessionStartedAt = '';
let sessionEndedAt = '';
let sessionTimerInterval = null;
let autoKnownAddressValue = '';
let knownAddressExplicitOverride = false;
let autoCallStartTimeValue = '';
let currentAutoModeId = '';
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
let autoModeJobId = '';
let autoModePollTimer = null;
let autoModePollInFlight = false;
let rewriteRecordMenuState = null;
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
let chatMentionUsersCache = [];
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
let availableScenarios = [];
let rewriteRecords = [];
let rewriteImportedRecords = [];
let rewriteRecordOrigins = [];
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
let rewritePendingExportScope = 'all';
let rewriteKeyPromptState = null;
let rewriteTransferNoticeTimer = null;
let blockingActionNoticeTimer = null;
let manualShellLeftHidden = false;
let manualShellRightHidden = false;
let manualShellLeftWidth = 320;
let manualShellRightWidth = 340;
let manualShellResizeState = null;

const authGate = document.getElementById('auth-gate');
const appShell = document.getElementById('app-shell');
const manualLeftPanel = document.getElementById('manual-left-panel');
const manualRightPanel = document.getElementById('manual-right-panel');
const manualLeftSplitter = document.getElementById('manual-left-splitter');
const manualRightSplitter = document.getElementById('manual-right-splitter');
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
const autoModeButton = document.getElementById('auto-mode-btn');
const blockingActionNotice = document.getElementById('blocking-action-notice');
const blockingActionNoticeText = document.getElementById('blocking-action-notice-text');
const blockingActionNoticeCloseButton = document.getElementById('blocking-action-notice-close');
const authUserName = document.getElementById('auth-user-name');
const knownAddressInput = document.getElementById('known-address');
const manualProductCategorySelect = document.getElementById('manual-product-category');
const manualRequestTypeSelect = document.getElementById('manual-request-type');
const historyDeviceBrandSelect = document.getElementById('history-device-brand');
const historyDeviceCategorySelect = document.getElementById('history-device-category');
const historyDevicePurchaseDateInput = document.getElementById('history-device-purchase-date');
const historyDeviceCalendarButton = document.getElementById('history-device-calendar-btn');
const historyDevicePurchaseYearInput = document.getElementById('history-device-purchase-year');
const historyDevicePurchaseMonthInput = document.getElementById('history-device-purchase-month');
const historyDevicePurchaseDayInput = document.getElementById('history-device-purchase-day');
const generateHistoryDeviceDateButton = document.getElementById('generate-history-device-date-btn');
const clearHistoryDeviceButton = document.getElementById('clear-history-device-btn');
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
const reviewChoiceGroup = document.querySelector('.review-choice-group');
const reviewCloseButton = document.getElementById('review-close-btn');
const reviewToggleButton = document.getElementById('review-toggle-btn');
const reviewSummary = document.getElementById('review-summary');
const reviewErrorFields = document.getElementById('review-error-fields');
const failedFlowStageSelect = document.getElementById('failed-flow-stage');
const reviewNotes = document.getElementById('review-notes');
const reviewPersistCheckbox = document.getElementById('review-persist-to-db');
const reviewPersistToggle = reviewPersistCheckbox?.closest('.toggle') || null;
const reviewSubmitButton = document.getElementById('review-submit-btn');
const reviewToRewriteButton = document.getElementById('review-to-rewrite-btn');
const terminalScrollRegion = document.getElementById('terminal-scroll-region');
const terminalOutput = document.getElementById('terminal-output');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-btn');
const scenarioList = document.getElementById('scenario-list');
const addressSlotsContainer = document.getElementById('address-slots-container');
const addressSlotsPanel = document.getElementById('address-slots-panel');
const autoModePreviewContainer = document.getElementById('auto-mode-preview-container');
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
const rewriteRecordMenu = document.getElementById('rewrite-record-menu');
const rewriteRecordReviewButton = document.getElementById('rewrite-record-review-btn');
const rewriteRecordDeleteButton = document.getElementById('rewrite-record-delete-btn');
const chatReplyButton = document.getElementById('chat-reply-btn');
const chatEditButton = document.getElementById('chat-edit-btn');
const chatRecallButton = document.getElementById('chat-recall-btn');
const terminalTurnMenu = document.getElementById('terminal-turn-menu');
const terminalInsertAddressIeButton = document.getElementById('terminal-insert-address-ie-btn');
const terminalInsertTelephoneIeButton = document.getElementById('terminal-insert-telephone-ie-btn');
const terminalRemoveIeButton = document.getElementById('terminal-remove-ie-btn');
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
const rewriteExportScopeChoices = document.getElementById('rewrite-export-scope-choices');
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
const CHAT_LAUNCHER_DRAG_THRESHOLD = 6;
const CHAT_LAUNCHER_DRAG_CLICK_SUPPRESS_MS = 240;
const CHAT_MESSAGE_HOLD_MS = 420;
const CHAT_MESSAGE_HOLD_MOVE_TOLERANCE = 10;
const CHAT_MENTION_OPTION_LIMIT = 12;
const SESSION_INPUT_HISTORY_LIMIT = 50;
const MANUAL_SHELL_LAYOUT_STORAGE_KEY = 'frontend-manual-shell-layout';
const MANUAL_SHELL_LEFT_MIN_PX = 248;
const MANUAL_SHELL_LEFT_MAX_PX = 420;
const MANUAL_SHELL_RIGHT_MIN_PX = 276;
const MANUAL_SHELL_RIGHT_MAX_PX = 460;
const MANUAL_SHELL_CENTER_MIN_PX = 560;
const MANUAL_SHELL_HIDE_THRESHOLD_PX = 92;
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
    'conversations',
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
const REWRITE_FUNCTION_CALL_TELEPHONE_TARGET = 'telephone';
const REWRITE_FUNCTION_CALL_TELEPHONE_LABEL = '电话';
const REWRITE_FUNCTION_CALL_TELEPHONE_PAYLOAD = '[{"name": "ie", "arguments": {"entity_type": "telephone"}}]';
const REWRITE_FUNCTION_CALL_OPTIONS = [
    {
        target: REWRITE_FUNCTION_CALL_ADDRESS_TARGET,
        label: REWRITE_FUNCTION_CALL_ADDRESS_LABEL,
        payload: REWRITE_FUNCTION_CALL_ADDRESS_PAYLOAD,
    },
    {
        target: REWRITE_FUNCTION_CALL_TELEPHONE_TARGET,
        label: REWRITE_FUNCTION_CALL_TELEPHONE_LABEL,
        payload: REWRITE_FUNCTION_CALL_TELEPHONE_PAYLOAD,
    },
];
const AUTHENTICATED_ONLY_ROOTS = [
    appShell,
    rewriteShell,
    rewriteTransferNotice,
    chatLauncher,
    chatMentionDropdown,
    chatMessageMenu,
    rewriteRecordMenu,
    terminalTurnMenu,
    chatWindow,
    reviewModal,
    rewriteExportModal,
    rewriteKeyModal,
    issueReferencePopover,
    textMagnifier,
].filter(Boolean);
const authenticatedUiAnchors = new Map();
const prefersReducedMotionQuery = typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-reduced-motion: reduce)')
    : null;
let prefersReducedMotion = Boolean(prefersReducedMotionQuery?.matches);

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
    const fallback = {
        visible: false,
        width: 384,
        height: 544,
        left: null,
        top: null,
        launcher_left: null,
        launcher_top: null,
        last_read_message_id: 0,
        read_username: '',
    };
    const raw = safeLocalStorageGet(CHAT_WINDOW_STORAGE_KEY);
    if (!raw) return fallback;
    try {
        const parsed = JSON.parse(raw);
        return {
            visible: parsed.visible === true,
            width: Number(parsed.width) || fallback.width,
            height: Number(parsed.height) || fallback.height,
            left: Number.isFinite(Number(parsed.left)) ? Number(parsed.left) : null,
            top: Number.isFinite(Number(parsed.top)) ? Number(parsed.top) : null,
            launcher_left: Number.isFinite(Number(parsed.launcher_left)) ? Number(parsed.launcher_left) : null,
            launcher_top: Number.isFinite(Number(parsed.launcher_top)) ? Number(parsed.launcher_top) : null,
            last_read_message_id: Math.max(Number(parsed.last_read_message_id || 0), 0),
            read_username: String(parsed.read_username || '').trim(),
        };
    } catch (error) {
        return fallback;
    }
}

function persistChatWindowState() {
    if (!chatWindowState) return;
    safeLocalStorageSet(CHAT_WINDOW_STORAGE_KEY, JSON.stringify(chatWindowState));
}

function loadManualShellLayoutState() {
    const raw = safeLocalStorageGet(MANUAL_SHELL_LAYOUT_STORAGE_KEY);
    if (!raw) {
        return {
            leftHidden: false,
            rightHidden: false,
            leftWidth: 320,
            rightWidth: 340,
        };
    }
    try {
        const parsed = JSON.parse(raw);
        return {
            leftHidden: parsed?.leftHidden === true,
            rightHidden: parsed?.rightHidden === true,
            leftWidth: Number.isFinite(Number(parsed?.leftWidth)) ? Number(parsed.leftWidth) : 320,
            rightWidth: Number.isFinite(Number(parsed?.rightWidth)) ? Number(parsed.rightWidth) : 340,
        };
    } catch (error) {
        return {
            leftHidden: false,
            rightHidden: false,
            leftWidth: 320,
            rightWidth: 340,
        };
    }
}

function persistManualShellLayoutState() {
    safeLocalStorageSet(
        MANUAL_SHELL_LAYOUT_STORAGE_KEY,
        JSON.stringify({
            leftHidden: manualShellLeftHidden,
            rightHidden: manualShellRightHidden,
            leftWidth: manualShellLeftWidth,
            rightWidth: manualShellRightWidth,
        }),
    );
}

function setElementInertState(element, inert) {
    if (!element) return;
    if ('inert' in element) {
        element.inert = Boolean(inert);
    }
}

function setAuthenticatedUiMounted(mounted) {
    AUTHENTICATED_ONLY_ROOTS.forEach((element, index) => {
        if (!authenticatedUiAnchors.has(element)) {
            authenticatedUiAnchors.set(element, document.createComment(`authenticated-ui-anchor-${index + 1}`));
        }
        const anchor = authenticatedUiAnchors.get(element);
        if (mounted) {
            if (!element.isConnected && anchor?.parentNode) {
                anchor.parentNode.insertBefore(element, anchor);
            }
            element.removeAttribute('hidden');
            element.removeAttribute('aria-hidden');
            setElementInertState(element, false);
            return;
        }
        if (element.isConnected && element.parentNode) {
            element.parentNode.insertBefore(anchor, element);
            element.remove();
        }
        element.setAttribute('hidden', 'hidden');
        element.setAttribute('aria-hidden', 'true');
        setElementInertState(element, true);
    });
}

function clearChatMentionDropdown() {
    chatMentionState = null;
    chatMentionOptions = [];
    chatMentionActiveIndex = 0;
    chatMentionDropdown.innerHTML = '';
    chatMentionDropdown.classList.add('hidden');
    chatMentionDropdown.setAttribute('aria-hidden', 'true');
}

function normalizeChatMentionUsers(users = []) {
    const uniqueByUsername = new Map();
    users.forEach((user) => {
        const username = String(user?.username || '').trim();
        if (!username) return;
        uniqueByUsername.set(username, {
            username,
            display_name: String(user?.display_name || username).trim() || username,
        });
    });
    return Array.from(uniqueByUsername.values()).sort((left, right) => (
        String(left.display_name || left.username).localeCompare(
            String(right.display_name || right.username),
            'zh-CN',
            { sensitivity: 'base' },
        ) || String(left.username).localeCompare(String(right.username), 'zh-CN', { sensitivity: 'base' })
    ));
}

async function refreshChatMentionUsers() {
    if (!authenticatedUser) {
        chatMentionUsersCache = [];
        return;
    }
    const data = await apiFetch('/api/auth/mention-users');
    chatMentionUsersCache = normalizeChatMentionUsers(Array.isArray(data?.users) ? data.users : []);
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

function ensureChatWindowState() {
    if (!chatWindowState) {
        chatWindowState = loadChatWindowState();
    }
    return chatWindowState;
}

function resolveChatLauncherAnchorRect() {
    const panel = addressSlotsPanel;
    if (!panel || !panel.isConnected) return null;
    const panelStyle = window.getComputedStyle(panel);
    if (panelStyle.display === 'none' || panelStyle.visibility === 'hidden') return null;
    const rect = panel.getBoundingClientRect();
    if (rect.width < 32 || rect.height < 32) return null;
    return rect;
}

function normalizeChatReadState({ persist = false } = {}) {
    const state = ensureChatWindowState();
    const latestId = Math.max(Number(chatLatestMessageId || 0), 0);
    const username = String(authenticatedUser?.username || '').trim();
    let changed = false;
    let nextReadMessageId = Math.max(Number(state.last_read_message_id || 0), 0);
    if (nextReadMessageId > latestId) {
        nextReadMessageId = latestId;
        changed = true;
    }
    if (state.last_read_message_id !== nextReadMessageId) {
        state.last_read_message_id = nextReadMessageId;
        changed = true;
    }
    if (username && state.read_username !== username) {
        state.read_username = username;
        state.last_read_message_id = 0;
        changed = true;
    }
    if (changed && persist) {
        persistChatWindowState();
    }
}

function markChatAsRead(messageId = chatLatestMessageId, { persist = true } = {}) {
    const state = ensureChatWindowState();
    const normalizedMessageId = Math.max(Number(messageId || 0), 0);
    const latestId = Math.max(Number(chatLatestMessageId || 0), 0);
    const nextReadMessageId = Math.min(normalizedMessageId, latestId);
    const username = String(authenticatedUser?.username || '').trim();
    const changed = state.last_read_message_id !== nextReadMessageId || state.read_username !== username;
    state.last_read_message_id = nextReadMessageId;
    state.read_username = username;
    if (changed && persist) {
        persistChatWindowState();
    }
}

function getUnreadChatMessages() {
    if (!authenticatedUser) return [];
    normalizeChatReadState();
    const lastReadMessageId = Math.max(Number(chatWindowState?.last_read_message_id || 0), 0);
    const currentUsername = String(authenticatedUser?.username || '').trim();
    return chatMessages.filter((message) => {
        if (!message || message.recalled) return false;
        const messageId = Math.max(Number(message.id || 0), 0);
        if (messageId <= lastReadMessageId) return false;
        return String(message.username || '').trim() !== currentUsername;
    });
}

function recomputeChatAttentionState({ persistReadState = false } = {}) {
    if (!authenticatedUser) {
        chatUnreadCount = 0;
        chatMentionAlertActive = false;
        updateChatLauncher();
        return;
    }
    if (chatWindowState?.visible !== false) {
        markChatAsRead(chatLatestMessageId, { persist: persistReadState });
        chatUnreadCount = 0;
        chatMentionAlertActive = false;
        updateChatLauncher();
        return;
    }
    const unreadMessages = getUnreadChatMessages();
    const currentUsername = String(authenticatedUser?.username || '').trim();
    chatUnreadCount = unreadMessages.length;
    chatMentionAlertActive = unreadMessages.some((message) => (
        extractMentionedUsernames(message.text || '').has(currentUsername)
    ));
    updateChatLauncher();
}

function resolveChatLauncherRect() {
    const bounds = getChatViewportBounds();
    const launcherWidth = Math.max(chatLauncher.offsetWidth || 172, 120);
    const launcherHeight = Math.max(chatLauncher.offsetHeight || 50, 40);
    const maxLeft = Math.max(CHAT_VIEWPORT_MARGIN, bounds.width - launcherWidth - CHAT_VIEWPORT_MARGIN);
    const maxTop = Math.max(CHAT_VIEWPORT_MARGIN, bounds.height - launcherHeight - CHAT_VIEWPORT_MARGIN);
    const hasStoredPosition = Number.isFinite(chatWindowState?.launcher_left) && Number.isFinite(chatWindowState?.launcher_top);
    if (hasStoredPosition) {
        return {
            left: clamp(Number(chatWindowState.launcher_left), CHAT_VIEWPORT_MARGIN, maxLeft),
            top: clamp(Number(chatWindowState.launcher_top), CHAT_VIEWPORT_MARGIN, maxTop),
        };
    }
    const anchorRect = resolveChatLauncherAnchorRect();
    if (anchorRect) {
        return {
            left: clamp(
                anchorRect.left + ((anchorRect.width - launcherWidth) / 2),
                CHAT_VIEWPORT_MARGIN,
                maxLeft,
            ),
            top: clamp(
                anchorRect.top + ((anchorRect.height - launcherHeight) / 2),
                CHAT_VIEWPORT_MARGIN,
                maxTop,
            ),
        };
    }
    const left = clamp(bounds.width - launcherWidth - 20, CHAT_VIEWPORT_MARGIN, maxLeft);
    const top = clamp(bounds.height - launcherHeight - 20, CHAT_VIEWPORT_MARGIN, maxTop);
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
    ensureChatWindowState();
    chatWindowState.visible = Boolean(visible);
    const shouldShow = Boolean(authenticatedUser) && Boolean(visible);
    chatWindow.classList.toggle('hidden', !shouldShow);
    chatWindow.setAttribute('aria-hidden', shouldShow ? 'false' : 'true');
    if (shouldShow) {
        applyChatWindowRect();
        markChatAsRead(chatLatestMessageId, { persist: false });
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
    if (!cursorTrailCanvas || !cursorTrailContext || prefersReducedMotion) return;
    const dpr = window.devicePixelRatio || 1;
    const width = Math.max(Math.floor(window.innerWidth * dpr), 1);
    const height = Math.max(Math.floor(window.innerHeight * dpr), 1);
    if (cursorTrailCanvas.width === width && cursorTrailCanvas.height === height) return;
    cursorTrailCanvas.width = width;
    cursorTrailCanvas.height = height;
    cursorTrailContext.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function ensureCursorTrailAnimation() {
    if (cursorTrailAnimationId !== null || !cursorTrailContext || prefersReducedMotion) return;
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
    if (prefersReducedMotion) return;
    cursorTrailTarget = { x: event.clientX, y: event.clientY };
    if (!cursorTrailInitialized) {
        cursorTrailPosition = { ...cursorTrailTarget };
        cursorTrailInitialized = true;
    }
    cursorTrailVisible = true;
    ensureCursorTrailAnimation();
}

function hideCursorGlow() {
    if (prefersReducedMotion) return;
    cursorTrailVisible = false;
    ensureCursorTrailAnimation();
}

function applyReducedMotionPreference(enabled) {
    prefersReducedMotion = Boolean(enabled);
    if (!prefersReducedMotion) return;
    cursorTrailVisible = false;
    cursorTrailInitialized = false;
    cursorTrailTarget = { x: -320, y: -320 };
    cursorTrailPosition = { x: -320, y: -320 };
    cursorTrailPoints = [];
    cursorTrailLastTimestamp = 0;
    if (cursorTrailAnimationId !== null) {
        window.cancelAnimationFrame(cursorTrailAnimationId);
        cursorTrailAnimationId = null;
    }
    if (cursorTrailContext && cursorTrailCanvas) {
        cursorTrailContext.clearRect(0, 0, window.innerWidth, window.innerHeight);
    }
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
    const line = isTerminalProcessingText(normalizedText)
        ? buildTerminalProcessingLine(normalizedText, { animate: true })
        : document.createElement('div');
    if (!isTerminalProcessingText(normalizedText)) {
        line.className = `terminal-line ${tone}`;
        line.textContent = normalizedText;
    }
    terminalOutput.appendChild(line);
    terminalScrollRegion.scrollTop = terminalScrollRegion.scrollHeight;
}

function setTerminalProcessingState(state = null) {
    terminalProcessingState = state && state.active
        ? {
            active: true,
            title: String(state.title || '').trim() || '处理中',
            detail: String(state.detail || '').trim(),
        }
        : null;
    renderTerminalEntries(sessionTerminalEntries);
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
    closeRewriteRecordMenu();
    rewriteRecords = [];
    rewriteImportedRecords = [];
    rewriteRecordOrigins = [];
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

function closeRewriteRecordMenu() {
    rewriteRecordMenuState = null;
    if (!rewriteRecordMenu) return;
    rewriteRecordMenu.classList.add('hidden');
    rewriteRecordMenu.setAttribute('aria-hidden', 'true');
    rewriteRecordMenu.style.left = '';
    rewriteRecordMenu.style.top = '';
}

function openRewriteRecordMenu(recordIndex, clientX, clientY) {
    if (!rewriteRecordMenu || !Number.isInteger(recordIndex) || recordIndex < 0 || recordIndex >= rewriteRecords.length) {
        closeRewriteRecordMenu();
        return;
    }
    rewriteRecordMenuState = { recordIndex };
    const menuWidth = Math.max(rewriteRecordMenu.offsetWidth || 160, 140);
    const menuHeight = Math.max(rewriteRecordMenu.offsetHeight || 56, 48);
    const left = Math.min(clientX, window.innerWidth - menuWidth - 12);
    const top = Math.min(clientY, window.innerHeight - menuHeight - 12);
    rewriteRecordMenu.style.left = `${Math.max(12, left)}px`;
    rewriteRecordMenu.style.top = `${Math.max(12, top)}px`;
    rewriteRecordMenu.classList.remove('hidden');
    rewriteRecordMenu.setAttribute('aria-hidden', 'false');
}

function updateModeSwitchButtons() {
    const canSwitch = Boolean(authenticatedUser) && !isReviewModalVisible();
    if (modeSwitchButton) modeSwitchButton.disabled = !canSwitch;
    if (rewriteBackButton) rewriteBackButton.disabled = !canSwitch;
}

function getManualShellGapWidth() {
    if (!appShell) return 0;
    const computedStyle = window.getComputedStyle(appShell);
    const gapValue = computedStyle.columnGap || computedStyle.gap || '0';
    const gapSize = parseFloat(gapValue) || 0;
    return gapSize * 4;
}

function applyManualShellLayoutState() {
    if (!appShell) return;
    const shouldUseResponsiveStack = window.innerWidth <= 1200;
    if (shouldUseResponsiveStack) {
        appShell.style.removeProperty('--manual-shell-left-width');
        appShell.style.removeProperty('--manual-shell-right-width');
    } else {
        const leftWidth = manualShellLeftHidden ? 0 : manualShellLeftWidth;
        const rightWidth = manualShellRightHidden ? 0 : manualShellRightWidth;
        appShell.style.setProperty('--manual-shell-left-width', `${Math.round(leftWidth)}px`);
        appShell.style.setProperty('--manual-shell-right-width', `${Math.round(rightWidth)}px`);
    }
    appShell.classList.toggle('manual-hide-left', manualShellLeftHidden);
    appShell.classList.toggle('manual-hide-right', manualShellRightHidden);
    if (manualLeftPanel) {
        manualLeftPanel.classList.toggle('is-manual-panel-collapsed', manualShellLeftHidden);
        manualLeftPanel.setAttribute('aria-hidden', manualShellLeftHidden ? 'true' : 'false');
    }
    if (manualRightPanel) {
        manualRightPanel.classList.toggle('is-manual-panel-collapsed', manualShellRightHidden);
        manualRightPanel.setAttribute('aria-hidden', manualShellRightHidden ? 'true' : 'false');
    }
    if (manualLeftSplitter) {
        manualLeftSplitter.classList.toggle('is-panel-hidden', manualShellLeftHidden);
        manualLeftSplitter.setAttribute(
            'aria-label',
            manualShellLeftHidden ? '向右拖拽显示左侧配置栏' : '调整左侧配置栏宽度',
        );
        manualLeftSplitter.setAttribute(
            'aria-valuenow',
            String(Math.round(manualShellLeftHidden ? 0 : manualShellLeftWidth)),
        );
    }
    if (manualRightSplitter) {
        manualRightSplitter.classList.toggle('is-panel-hidden', manualShellRightHidden);
        manualRightSplitter.setAttribute(
            'aria-label',
            manualShellRightHidden ? '向左拖拽显示右侧状态栏' : '调整右侧状态栏宽度',
        );
        manualRightSplitter.setAttribute(
            'aria-valuenow',
            String(Math.round(manualShellRightHidden ? 0 : manualShellRightWidth)),
        );
    }
}

function applyManualShellWidthConstraints() {
    if (!appShell || window.innerWidth <= 1200) return;
    const shellRect = appShell.getBoundingClientRect();
    const totalWidth = shellRect.width;
    const splitterWidth = (manualLeftSplitter?.offsetWidth || 0) + (manualRightSplitter?.offsetWidth || 0);
    const reservedWidth = splitterWidth + getManualShellGapWidth();

    manualShellLeftWidth = Math.min(
        Math.max(manualShellLeftWidth, MANUAL_SHELL_LEFT_MIN_PX),
        MANUAL_SHELL_LEFT_MAX_PX,
    );
    manualShellRightWidth = Math.min(
        Math.max(manualShellRightWidth, MANUAL_SHELL_RIGHT_MIN_PX),
        MANUAL_SHELL_RIGHT_MAX_PX,
    );

    if (!manualShellLeftHidden && !manualShellRightHidden) {
        const maxLeft = Math.max(
            MANUAL_SHELL_LEFT_MIN_PX,
            totalWidth - reservedWidth - manualShellRightWidth - MANUAL_SHELL_CENTER_MIN_PX,
        );
        manualShellLeftWidth = Math.min(manualShellLeftWidth, maxLeft);
        const maxRight = Math.max(
            MANUAL_SHELL_RIGHT_MIN_PX,
            totalWidth - reservedWidth - manualShellLeftWidth - MANUAL_SHELL_CENTER_MIN_PX,
        );
        manualShellRightWidth = Math.min(manualShellRightWidth, maxRight);
    }
}

function updateManualShellWidthFromPointer(side, clientX) {
    if (!appShell) return;
    const shellRect = appShell.getBoundingClientRect();
    const totalWidth = shellRect.width;
    const reservedWidth = (
        (manualLeftSplitter?.offsetWidth || 0)
        + (manualRightSplitter?.offsetWidth || 0)
        + getManualShellGapWidth()
    );

    if (side === 'left') {
        const rawWidth = clientX - shellRect.left;
        if (rawWidth <= MANUAL_SHELL_HIDE_THRESHOLD_PX) {
            manualShellLeftHidden = true;
        } else {
            manualShellLeftHidden = false;
            const maxLeft = Math.max(
                MANUAL_SHELL_LEFT_MIN_PX,
                totalWidth
                    - reservedWidth
                    - (manualShellRightHidden ? 0 : manualShellRightWidth)
                    - MANUAL_SHELL_CENTER_MIN_PX,
            );
            manualShellLeftWidth = Math.min(
                Math.max(rawWidth, MANUAL_SHELL_LEFT_MIN_PX),
                Math.min(MANUAL_SHELL_LEFT_MAX_PX, maxLeft),
            );
        }
    }

    if (side === 'right') {
        const rawWidth = shellRect.right - clientX;
        if (rawWidth <= MANUAL_SHELL_HIDE_THRESHOLD_PX) {
            manualShellRightHidden = true;
        } else {
            manualShellRightHidden = false;
            const maxRight = Math.max(
                MANUAL_SHELL_RIGHT_MIN_PX,
                totalWidth
                    - reservedWidth
                    - (manualShellLeftHidden ? 0 : manualShellLeftWidth)
                    - MANUAL_SHELL_CENTER_MIN_PX,
            );
            manualShellRightWidth = Math.min(
                Math.max(rawWidth, MANUAL_SHELL_RIGHT_MIN_PX),
                Math.min(MANUAL_SHELL_RIGHT_MAX_PX, maxRight),
            );
        }
    }

    applyManualShellWidthConstraints();
    applyManualShellLayoutState();
}

function beginManualShellResize(side, event) {
    if (!appShell || activeAppMode !== 'manual' || isReviewModalVisible() || window.innerWidth <= 1200) return;
    event.preventDefault();
    manualShellResizeState = { side, pointerId: event.pointerId };
    const splitter = side === 'left' ? manualLeftSplitter : manualRightSplitter;
    splitter?.classList.add('is-dragging');
    if (typeof splitter?.setPointerCapture === 'function') {
        splitter.setPointerCapture(event.pointerId);
    }
    updateManualShellWidthFromPointer(side, event.clientX);
}

function handleManualShellResize(event) {
    if (!manualShellResizeState || event.pointerId !== manualShellResizeState.pointerId) return;
    updateManualShellWidthFromPointer(manualShellResizeState.side, event.clientX);
}

function endManualShellResize(event) {
    if (!manualShellResizeState || (event && event.pointerId !== manualShellResizeState.pointerId)) return;
    const splitter = manualShellResizeState.side === 'left' ? manualLeftSplitter : manualRightSplitter;
    if (
        splitter
        && typeof splitter.releasePointerCapture === 'function'
        && event
        && splitter.hasPointerCapture?.(event.pointerId)
    ) {
        splitter.releasePointerCapture(event.pointerId);
    }
    manualShellResizeState = null;
    manualLeftSplitter?.classList.remove('is-dragging');
    manualRightSplitter?.classList.remove('is-dragging');
    persistManualShellLayoutState();
}

function isTestAdminUser() {
    return String(authenticatedUser?.display_name || '').trim() === '测试管理员';
}

function closeBlockingActionNotice() {
    if (!blockingActionNotice) return;
    blockingActionNotice.classList.add('hidden');
    blockingActionNotice.setAttribute('hidden', 'hidden');
    blockingActionNotice.setAttribute('aria-hidden', 'true');
    if (blockingActionNoticeTimer !== null) {
        window.clearTimeout(blockingActionNoticeTimer);
        blockingActionNoticeTimer = null;
    }
}

function showBlockingActionNotice(message = '请先选择场景。') {
    if (!blockingActionNotice || !blockingActionNoticeText) return;
    blockingActionNoticeText.textContent = String(message || '').trim() || '请先选择场景。';
    blockingActionNotice.classList.remove('hidden');
    blockingActionNotice.removeAttribute('hidden');
    blockingActionNotice.setAttribute('aria-hidden', 'false');
    if (blockingActionNoticeTimer !== null) {
        window.clearTimeout(blockingActionNoticeTimer);
    }
    blockingActionNoticeTimer = window.setTimeout(() => {
        closeBlockingActionNotice();
    }, 3000);
}

function setSoftDisabledButton(button, active) {
    if (!button) return;
    const isSoftDisabled = Boolean(active);
    button.classList.toggle('is-soft-disabled', isSoftDisabled);
    button.dataset.softDisabled = isSoftDisabled ? 'true' : 'false';
    button.setAttribute('aria-disabled', isSoftDisabled ? 'true' : 'false');
    if (isSoftDisabled) {
        button.removeAttribute('disabled');
    }
}

function updateAutoModeButtonState() {
    if (!autoModeButton) return;
    const shouldShow = Boolean(authenticatedUser) && activeAppMode === 'manual' && isTestAdminUser();
    autoModeButton.classList.toggle('hidden', !shouldShow);
    autoModeButton.disabled = !shouldShow
        || sessionBusy
        || (currentSessionId && !sessionClosed)
        || hasBlockingReviewPending()
        || isReviewModalVisible()
        || !isCallStartTimeValid();
    setSoftDisabledButton(autoModeButton, false);
}

function syncAppModeView() {
    const authenticated = Boolean(authenticatedUser);
    const showManual = authenticated && activeAppMode === 'manual';
    const showRewrite = authenticated && activeAppMode === 'rewrite';
    applyManualShellWidthConstraints();
    applyManualShellLayoutState();
    setAuthenticatedUiMounted(authenticated);
    authGate.classList.toggle('hidden', authenticated);
    authGate.toggleAttribute('hidden', authenticated);
    authGate.setAttribute('aria-hidden', authenticated ? 'true' : 'false');
    appShell.classList.toggle('hidden', !showManual);
    rewriteShell.classList.toggle('hidden', !showRewrite);

    const showChatWindow = authenticated && chatWindowState?.visible !== false;
    chatWindow.classList.toggle('hidden', !showChatWindow);
    chatWindow.setAttribute('aria-hidden', showChatWindow ? 'false' : 'true');
    if (showChatWindow) {
        applyChatWindowRect();
    }
    updateChatLauncher();
    updateModeSwitchButtons();
    updateAutoModeButtonState();
    updateRewriteHistoryButtons();
    if (showRewrite) {
        window.requestAnimationFrame(() => {
            applyRewriteShellLayout();
            applyRewriteWorkbenchRatio();
        });
    }
    if (authenticated && !showChatWindow) {
        window.requestAnimationFrame(() => {
            applyChatLauncherRect();
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

function createScenarioListItem(scenario, index) {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'scenario-item';
    item.dataset.scenarioIndex = String(index);
    if (selectedScenario?.id === scenario.id) {
        item.classList.add('active');
    }

    const title = document.createElement('span');
    title.className = 'scenario-title';
    title.textContent = String(scenario.product || '-');

    const metaId = document.createElement('span');
    metaId.className = 'scenario-meta';
    metaId.textContent = String(scenario.id || `场景 ${index + 1}`);

    const metaRequest = document.createElement('span');
    metaRequest.className = 'scenario-meta';
    metaRequest.textContent = `${scenario.request || '-'} | max_turns=${scenario.max_turns || '-'}`;

    const issue = document.createElement('span');
    issue.className = 'scenario-issue';
    issue.textContent = String(scenario.issue || '未填写故障描述');

    item.append(title, metaId, metaRequest, issue);
    item.addEventListener('click', () => {
        selectScenario(scenario);
    });
    return item;
}

function renderScenarioList() {
    syncManualScenarioSelection({ refreshKnownAddress: true });
}

function getManualRequestLabel(requestType) {
    return String(requestType || '').trim() === 'installation' ? '安装' : '维修';
}

function getManualMaxRoundsValue() {
    return 32;
}

function sanitizeManualMaxRoundsInput() {
    return getManualMaxRoundsValue();
}

function historyDeviceCategoryOptionsForBrand(brand) {
    const normalizedBrand = String(brand || '').trim();
    if (!normalizedBrand) {
        return [''];
    }
    if (['COLMO', '真暖', '真省', '雪焰', '暖家', '煤改电', '真享'].includes(normalizedBrand)) {
        return ['家用空气能热水机'];
    }
    if (normalizedBrand === '烈焰') {
        return ['空气能热水机'];
    }
    return ['', '家用空气能热水机', '空气能热水机'];
}

function syncHistoryDeviceCategoryOptions() {
    if (!historyDeviceCategorySelect) return;
    const currentValue = historyDeviceCategorySelect.value;
    const options = historyDeviceCategoryOptionsForBrand(historyDeviceBrandSelect?.value || '');
    historyDeviceCategorySelect.innerHTML = '';
    options.forEach((value) => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = value || '未知';
        historyDeviceCategorySelect.append(option);
    });
    if (options.includes(currentValue)) {
        historyDeviceCategorySelect.value = currentValue;
    } else {
        historyDeviceCategorySelect.value = options[0] || '';
    }
}

function formatDateForInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function randomHistoryDevicePurchaseDate() {
    const now = new Date();
    const end = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const start = new Date(Math.max(2018, now.getFullYear() - 7), 0, 1);
    const span = Math.max(1, end.getTime() - start.getTime());
    return formatDateForInput(new Date(start.getTime() + Math.floor(Math.random() * span)));
}

function parseHistoryDeviceDateParts() {
    const year = String(historyDevicePurchaseYearInput?.value || '').trim();
    const month = String(historyDevicePurchaseMonthInput?.value || '').trim();
    const day = String(historyDevicePurchaseDayInput?.value || '').trim();
    return { year, month, day };
}

function isValidHistoryDeviceDateParts(year, month, day) {
    if (!/^\d{4}$/.test(year) || !/^\d{1,2}$/.test(month) || !/^\d{1,2}$/.test(day)) return false;
    const yearNumber = Number(year);
    const monthNumber = Number(month);
    const dayNumber = Number(day);
    if (monthNumber < 1 || monthNumber > 12 || dayNumber < 1) return false;
    const maxDay = new Date(yearNumber, monthNumber, 0).getDate();
    return dayNumber <= maxDay;
}

function syncHistoryDeviceDateValueFromParts() {
    if (!historyDevicePurchaseDateInput) return '';
    const { year, month, day } = parseHistoryDeviceDateParts();
    if (!isValidHistoryDeviceDateParts(year, month, day)) {
        historyDevicePurchaseDateInput.value = '';
        return '';
    }
    const normalized = `${year}-${String(Number(month)).padStart(2, '0')}-${String(Number(day)).padStart(2, '0')}`;
    historyDevicePurchaseDateInput.value = normalized;
    return normalized;
}

function setHistoryDeviceDateParts(dateValue) {
    const match = String(dateValue || '').trim().match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) {
        if (historyDevicePurchaseYearInput) historyDevicePurchaseYearInput.value = '';
        if (historyDevicePurchaseMonthInput) historyDevicePurchaseMonthInput.value = '';
        if (historyDevicePurchaseDayInput) historyDevicePurchaseDayInput.value = '';
        if (historyDevicePurchaseDateInput) historyDevicePurchaseDateInput.value = '';
        return;
    }
    const [, year, month, day] = match;
    if (historyDevicePurchaseYearInput) historyDevicePurchaseYearInput.value = year;
    if (historyDevicePurchaseMonthInput) historyDevicePurchaseMonthInput.value = String(Number(month));
    if (historyDevicePurchaseDayInput) historyDevicePurchaseDayInput.value = String(Number(day));
    if (historyDevicePurchaseDateInput) historyDevicePurchaseDateInput.value = `${year}-${month}-${day}`;
}

function openHistoryDeviceCalendarPicker() {
    if (!historyDevicePurchaseDateInput) return;
    const currentValue = syncHistoryDeviceDateValueFromParts();
    if (currentValue) {
        historyDevicePurchaseDateInput.value = currentValue;
    }
    if (typeof historyDevicePurchaseDateInput.showPicker === 'function') {
        historyDevicePurchaseDateInput.showPicker();
        return;
    }
    historyDevicePurchaseDateInput.focus();
    historyDevicePurchaseDateInput.click();
}

function clearHistoryDeviceConfig() {
    if (historyDeviceBrandSelect) historyDeviceBrandSelect.value = '';
    syncHistoryDeviceCategoryOptions();
    setHistoryDeviceDateParts('');
    syncManualScenarioSelection({ refreshKnownAddress: false });
}

function getHistoryDeviceConfig() {
    return {
        brand: String(historyDeviceBrandSelect?.value || '').trim(),
        category: String(historyDeviceCategorySelect?.value || '').trim(),
        purchase_date: String(historyDevicePurchaseDateInput?.value || '').trim(),
    };
}

function getKnownAddressPayloadValue({ includeAutoPrefill = true } = {}) {
    const value = String(knownAddressInput?.value || '').trim();
    if (
        !includeAutoPrefill
        && value
        && value === String(autoKnownAddressValue || '').trim()
        && !knownAddressExplicitOverride
    ) {
        return '';
    }
    return value;
}

function buildConfiguredScenarioSelection() {
    const productCategory = String(manualProductCategorySelect?.value || '空气能热水机').trim() || '空气能热水机';
    const requestType = String(manualRequestTypeSelect?.value || 'fault').trim() === 'installation'
        ? 'installation'
        : 'fault';
    const requestLabel = getManualRequestLabel(requestType);
    const maxTurns = getManualMaxRoundsValue();
    const productKeyMap = {
        '空气能热水机': 'air_energy',
        '热水器': 'water_heater',
        '燃气热水器': 'gas_water_heater',
        '电热水器': 'electric_water_heater',
    };
    const productKey = productKeyMap[productCategory] || 'air_energy';
    return {
        id: `manual-config-${productKey}-${requestType}`,
        scenario_id: `manual_config_${productKey}_${requestType}`,
        product: `美的 ${productCategory}`,
        request: requestType,
        issue: `美的${productCategory}需要${requestLabel}`,
        max_turns: maxTurns,
        product_category: productCategory,
        request_type: requestType,
    };
}

function syncManualScenarioSelection(options = {}) {
    const { refreshKnownAddress = false } = options;
    selectedScenario = buildConfiguredScenarioSelection();
    updateStartSessionButtonState();
    if (refreshKnownAddress && authenticatedUser) {
        hydrateKnownAddressPrefill(false);
    }
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
    const matchedOption = REWRITE_FUNCTION_CALL_OPTIONS.find((option) => option.payload === normalizedText);
    return matchedOption ? matchedOption.target : '';
}

function getRewriteObservationFieldSpecs(payload = {}, targetType = '') {
    const normalizedTarget = String(targetType || '').trim();
    if (
        normalizedTarget === REWRITE_FUNCTION_CALL_TELEPHONE_TARGET
        || Object.prototype.hasOwnProperty.call(payload, 'telephone')
        || Object.prototype.hasOwnProperty.call(payload, 'numberType')
    ) {
        return [
            ['telephone', 'telephone', payload.telephone, '填写 observation 的电话结果'],
            ['numberType', 'numberType', payload.numberType, '填写 numberType'],
            ['error_code', 'error_code', payload.error_code, '填写 error_code'],
            ['error_msg', 'error_msg', payload.error_msg, '填写 error_msg'],
        ];
    }
    return [
        ['address', 'address', payload.address, '填写 observation 的地址结果'],
        ['error_code', 'error_code', payload.error_code, '填写 error_code'],
        ['error_msg', 'error_msg', payload.error_msg, '填写 error_msg'],
    ];
}

function createDefaultRewriteObservationPayload(targetType = '') {
    return Object.fromEntries(
        getRewriteObservationFieldSpecs({}, targetType).map(([fieldKey]) => [fieldKey, '']),
    );
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
            return Object.fromEntries(
                Object.entries(parsed).map(([key, value]) => [key, value == null ? '' : String(value)]),
            );
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
    const parsedPayload = payload && typeof payload === 'object' && !Array.isArray(payload)
        ? payload
        : {};
    const targetType = Object.prototype.hasOwnProperty.call(parsedPayload, 'telephone')
        || Object.prototype.hasOwnProperty.call(parsedPayload, 'numberType')
        ? REWRITE_FUNCTION_CALL_TELEPHONE_TARGET
        : REWRITE_FUNCTION_CALL_ADDRESS_TARGET;
    const normalizedPayload = {};
    getRewriteObservationFieldSpecs(parsedPayload, targetType).forEach(([fieldKey]) => {
        if (fieldKey === 'error_code') {
            const rawErrorCode = String(parsedPayload.error_code ?? '').trim();
            normalizedPayload.error_code = /^-?\d+$/.test(rawErrorCode) ? Number(rawErrorCode) : rawErrorCode;
            return;
        }
        normalizedPayload[fieldKey] = String(parsedPayload[fieldKey] ?? '').trim();
    });
    return JSON.stringify(normalizedPayload);
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

function inferRewriteRecordOrigin(record) {
    const source = String(record?.source || '').trim();
    if (source === 'manual_test' || source === 'auto_mode') return 'test';
    return 'file';
}

function getRewriteRecordOrigin(index) {
    const origin = String(rewriteRecordOrigins[index] || '').trim();
    if (origin === 'file' || origin === 'test') return origin;
    return inferRewriteRecordOrigin(rewriteRecords[index]);
}

function getRewriteOriginIndexes(origin) {
    return rewriteRecords
        .map((_, index) => index)
        .filter((index) => getRewriteRecordOrigin(index) === origin);
}

function summarizeRewriteRecordOrigins(indexes = rewriteRecords.map((_, index) => index)) {
    return indexes.reduce((summary, index) => {
        const origin = getRewriteRecordOrigin(index);
        if (origin === 'test') {
            summary.test += 1;
        } else {
            summary.file += 1;
        }
        return summary;
    }, { file: 0, test: 0 });
}

function hasMixedRewriteRecordOrigins() {
    const summary = summarizeRewriteRecordOrigins();
    return summary.file > 0 && summary.test > 0;
}

function getRewriteExportScopeLabel(scope = 'all') {
    if (scope === 'file') return '上传文件';
    if (scope === 'test') return '测试转改写';
    return '全部记录';
}

function getRewriteExportIndexes(scope = 'all') {
    if (scope === 'file') return getRewriteOriginIndexes('file');
    if (scope === 'test') return getRewriteOriginIndexes('test');
    return rewriteRecords.map((_, index) => index);
}

function syncRewriteImportedRecordsFallback() {
    rewriteImportedRecords = rewriteRecords.map((record, index) => (
        cloneRewriteRecordData(rewriteImportedRecords[index]) ?? cloneRewriteRecordData(record)
    ));
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

function summarizeRewriteRecordStatuses(scope = 'all') {
    return getRewriteExportIndexes(scope).reduce((summary, index) => {
        const record = rewriteRecords[index];
        const status = getRewriteRecordStatus(record);
        if (status === '已提交') {
            summary.submitted += 1;
        } else if (status === '未提交') {
            summary.unsubmitted += 1;
        } else {
            summary.unannotated += 1;
        }
        summary.total += 1;
        return summary;
    }, {
        total: 0,
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
    rewritePendingExportScope = 'all';
    if (rewriteExportScopeChoices) {
        rewriteExportScopeChoices.classList.add('hidden');
    }
    if (rewriteExportConfirmButton) {
        rewriteExportConfirmButton.classList.remove('hidden');
    }
}

function openRewriteExportScopeModal() {
    if (!rewriteExportModal || !rewriteExportSummary || !rewriteExportStats) return;
    clearElement(rewriteExportStats);
    rewritePendingExportAction = null;
    rewritePendingExportScope = 'all';
    const originSummary = summarizeRewriteRecordOrigins();
    rewriteExportSummary.textContent = '当前右侧同时存在上传文件数据和测试转改写数据，请选择本次导出范围。';
    appendDataItem(rewriteExportStats, '上传文件', `${originSummary.file} 条`);
    appendDataItem(rewriteExportStats, '测试转改写', `${originSummary.test} 条`);
    if (rewriteExportScopeChoices) {
        rewriteExportScopeChoices.classList.remove('hidden');
    }
    if (rewriteExportConfirmButton) {
        rewriteExportConfirmButton.classList.add('hidden');
    }
    rewriteExportModal.classList.remove('hidden');
    rewriteExportModal.setAttribute('aria-hidden', 'false');
}

function openRewriteExportModal(statusSummary, scope = 'all') {
    if (!rewriteExportModal || !rewriteExportSummary || !rewriteExportStats) return;
    clearElement(rewriteExportStats);
    rewritePendingExportScope = scope;
    rewriteExportSummary.textContent = `当前导出范围为“${getRewriteExportScopeLabel(scope)}”，其中存在未提交或未标注数据。强制导出时，只有“已提交”的数据会保留 rewrited，其余记录将按原始导入内容导出。`;
    appendDataItem(rewriteExportStats, '导出范围', getRewriteExportScopeLabel(scope));
    appendDataItem(rewriteExportStats, '记录数', String(statusSummary.total));
    appendDataItem(rewriteExportStats, '已提交', String(statusSummary.submitted));
    appendDataItem(rewriteExportStats, '未提交', String(statusSummary.unsubmitted));
    appendDataItem(rewriteExportStats, '未标注', String(statusSummary.unannotated));
    if (rewriteExportScopeChoices) {
        rewriteExportScopeChoices.classList.add('hidden');
    }
    if (rewriteExportConfirmButton) {
        rewriteExportConfirmButton.classList.remove('hidden');
    }
    rewriteExportModal.classList.remove('hidden');
    rewriteExportModal.setAttribute('aria-hidden', 'false');
}

function buildRewriteExportRecords(scope = 'all') {
    return getRewriteExportIndexes(scope).map((index) => {
        const record = rewriteRecords[index];
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
    const recordId = resolveRewriteRecordId(record) || `第 ${rewriteSelectedIndex + 1} 条记录`;
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
        rewriteUploadStatus.textContent = `${recordId} 已提交，共 ${lines.length} 行对话。`;
    }
}

function buildRewriteRecordFromSessionEntries() {
    if (!Array.isArray(sessionTerminalEntries) || sessionTerminalEntries.length < 1) return null;
    const conversations = [];
    sessionTerminalEntries.forEach((entry) => {
        if (!entry || typeof entry !== 'object') return;
        if (entry.entry_type === 'turn') {
            const normalizedRole = normalizeRewriteSpeaker(entry.speaker || '') || String(entry.speaker || '').trim();
            const normalizedText = String(entry.text || '').trim();
            if (!normalizedRole || !normalizedText) return;
            conversations.push({
                role: normalizedRole,
                content: normalizedText,
            });
            return;
        }
        const rawText = String(entry.text || '').trim();
        if (!rawText) return;
        if (rawText.startsWith('function_call:')) {
            conversations.push({
                role: 'function_call',
                content: rawText,
            });
            return;
        }
        if (rawText.startsWith('observation:')) {
            conversations.push({
                role: 'observation',
                content: rawText,
            });
        }
    });
    if (!conversations.length) return null;
    const autoRecordId = String(currentAutoModeId || '').trim();
    const recordId = currentSessionId || autoRecordId || `manual-${Date.now()}`;
    return {
        session_id: currentSessionId || '',
        auto_mode_id: autoRecordId,
        id: recordId,
        conversations,
        source: autoRecordId && !currentSessionId ? 'auto_mode' : 'manual_test',
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
    rewriteRecordOrigins.push('test');
    if (!rewriteSourceName) {
        rewriteSourceName = record.source === 'auto_mode' ? 'auto_mode_export.jsonl' : 'manual_session_export.jsonl';
    }
    if (!rewriteSourceFormat) {
        rewriteSourceFormat = 'jsonl';
    }
    rewriteAvailableRoles = collectRewriteAvailableRoles(rewriteRecords);
    reviewPending = false;
    dismissReview();
    setAppMode('rewrite');
    renderRewriteFileInfo();
    renderRewriteRecordList();
    const targetIndex = rewriteRecords.length - 1;
    setRewriteUploadStatus(
        `${record.source === 'auto_mode' ? '已将自动模式数据' : '已将测试数据'}追加到改写模式，共 ${rewriteRecords.length} 条记录。`
    );
    selectRewriteRecord(targetIndex);
}

function getRewriteExportFormat(scope = 'all') {
    if (scope === 'test') return 'jsonl';
    if (scope === 'all') {
        const originSummary = summarizeRewriteRecordOrigins(getRewriteExportIndexes(scope));
        if (originSummary.test > 0 && originSummary.file === 0) return 'jsonl';
        if (originSummary.test > 0 && originSummary.file > 0) return 'jsonl';
    }
    return String(rewriteSourceFormat || '').trim().toLowerCase() === 'jsonl' ? 'jsonl' : 'json';
}

function buildRewriteExportContent(scope = 'all') {
    const exportRecords = buildRewriteExportRecords(scope);
    const format = getRewriteExportFormat(scope);
    if (format === 'jsonl') {
        return exportRecords.map((record) => JSON.stringify(record)).join('\n');
    }
    return JSON.stringify(exportRecords, null, 2);
}

function buildRewriteExportFileName(scope = 'all') {
    const sourceName = String(rewriteSourceName || 'rewrite_export').trim();
    const baseName = (sourceName.replace(/\.[^.]+$/, '') || 'rewrite_export').replace(/[\\/:*?"<>|]+/g, '_');
    const extension = getRewriteExportFormat(scope);
    const scopeSuffix = scope === 'file'
        ? 'file'
        : scope === 'test'
            ? 'test'
            : hasMixedRewriteRecordOrigins()
                ? 'all'
                : '';
    return `${baseName}${scopeSuffix ? `_${scopeSuffix}` : ''}_rewrited.${extension}`;
}

function exportRewriteFile() {
    if (!rewriteRecords.length) return;
    if (hasMixedRewriteRecordOrigins()) {
        openRewriteExportScopeModal();
        return;
    }
    exportRewriteScopeWithValidation('all');
}

function exportRewriteScopeWithValidation(scope = 'all') {
    const indexes = getRewriteExportIndexes(scope);
    if (!indexes.length) {
        if (rewriteUploadStatus) {
            rewriteUploadStatus.textContent = `${getRewriteExportScopeLabel(scope)}没有可导出的记录。`;
        }
        return;
    }
    const statusSummary = summarizeRewriteRecordStatuses(scope);
    if (statusSummary.unsubmitted > 0 || statusSummary.unannotated > 0) {
        rewritePendingExportAction = () => {
            closeRewriteExportModal();
            exportRewriteFileWithCurrentState(scope);
        };
        openRewriteExportModal(statusSummary, scope);
        return;
    }
    closeRewriteExportModal();
    exportRewriteFileWithCurrentState(scope);
}

function exportRewriteFileWithCurrentState(scope = 'all') {
    if (!rewriteRecords.length) return;
    const statusSummary = summarizeRewriteRecordStatuses(scope);
    if (statusSummary.unsubmitted > 0 || statusSummary.unannotated > 0) {
        // Export is intentionally selective; non-submitted records fall back to imported content.
        if (rewriteUploadStatus) {
            rewriteUploadStatus.textContent = `${getRewriteExportScopeLabel(scope)}存在未提交或未标注数据，导出文件中仅保留已提交记录的 rewrited。`;
        }
    }
    const content = buildRewriteExportContent(scope);
    const fileName = buildRewriteExportFileName(scope);
    const format = getRewriteExportFormat(scope);
    const blob = new Blob([content], {
        type: format === 'jsonl'
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
        rewriteUploadStatus.textContent = `已导出${getRewriteExportScopeLabel(scope)}：${fileName}`;
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
        const matchedOption = REWRITE_FUNCTION_CALL_OPTIONS.find((option) => option.target === targetType);
        target.text = matchedOption ? matchedOption.payload : '';
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
    const matchedOption = REWRITE_FUNCTION_CALL_OPTIONS.find((option) => option.target === normalizedTarget);
    targetLine.text = matchedOption ? matchedOption.payload : '';
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

function buildRewriteObservationContextLines(recordIndex, functionCallLineId) {
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
    const targetType = inferRewriteFunctionCallTarget(functionCallLine.text);
    if (!targetType) {
        window.alert('请先为 function_call 选择调用项。');
        return;
    }

    const dialogueLines = buildRewriteObservationContextLines(recordIndex, functionCallLineId);
    if (!dialogueLines.length) {
        window.alert('请先在 function_call 上方保留用户/客服对话内容。');
        return;
    }

    rewriteObservationLoadingLineIds.add(functionCallLineId);
    renderRewriteRecordState(recordIndex);
    try {
        const data = await apiFetch('/api/rewrite/ie-observation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ entity_type: targetType, dialogue_lines: dialogueLines }),
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

function buildRewriteRecordButton(index) {
    const record = rewriteRecords[index];
    const meta = buildRewriteRecordMeta(record);
    const statusClass = buildRewriteStatusClass(meta.status);
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'scenario-item';
    button.dataset.recordIndex = String(index);
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
    return button;
}

function appendRewriteRecordGroup(container, { title, indexes, total }) {
    const section = document.createElement('section');
    section.className = 'rewrite-record-group';
    const header = document.createElement('div');
    header.className = 'rewrite-record-group-header';
    header.innerHTML = `
        <span>${escapeHtml(title)}</span>
        <span>${indexes.length} / ${total}</span>
    `;
    const list = document.createElement('div');
    list.className = 'rewrite-record-group-list';
    if (indexes.length) {
        indexes.forEach((index) => {
            list.appendChild(buildRewriteRecordButton(index));
        });
    } else {
        list.innerHTML = '<div class="terminal-hint">没有匹配记录。</div>';
    }
    section.appendChild(header);
    section.appendChild(list);
    container.appendChild(section);
}

function renderRewriteRecordList() {
    clearElement(rewriteRecordList);
    rewriteRecordList.classList.remove('has-groups');
    if (!rewriteRecords.length) {
        rewriteRecordList.innerHTML = '<div class="terminal-hint">导入文件后显示记录列表</div>';
        if (rewriteRecordSearchStatus) {
            rewriteRecordSearchStatus.textContent = '输入后实时筛选，回车跳到首条匹配记录。';
        }
        return;
    }

    const matchedIndexes = getFilteredRewriteRecordIndexes();
    const originSummary = summarizeRewriteRecordOrigins();
    const isMixed = originSummary.file > 0 && originSummary.test > 0;
    if (rewriteRecordSearchStatus) {
        const query = String(rewriteRecordSearchQuery || '').trim();
        if (isMixed) {
            const matchedOriginSummary = summarizeRewriteRecordOrigins(matchedIndexes);
            rewriteRecordSearchStatus.textContent = query
                ? `当前匹配 ${matchedIndexes.length} 条，上传文件 ${matchedOriginSummary.file} 条，测试转改写 ${matchedOriginSummary.test} 条。`
                : `当前共 ${rewriteRecords.length} 条，上传文件 ${originSummary.file} 条，测试转改写 ${originSummary.test} 条。`;
        } else {
            rewriteRecordSearchStatus.textContent = query
                ? `当前匹配 ${matchedIndexes.length} 条记录，回车跳到首条匹配。`
                : `当前共 ${rewriteRecords.length} 条记录，输入后实时筛选。`;
        }
    }
    if (!matchedIndexes.length) {
        rewriteRecordList.innerHTML = '<div class="terminal-hint">没有匹配到对应记录。</div>';
        return;
    }

    if (isMixed) {
        rewriteRecordList.classList.add('has-groups');
        const groupContainer = document.createElement('div');
        groupContainer.className = 'rewrite-record-groups';
        appendRewriteRecordGroup(groupContainer, {
            title: '上传文件',
            indexes: matchedIndexes.filter((index) => getRewriteRecordOrigin(index) === 'file'),
            total: originSummary.file,
        });
        appendRewriteRecordGroup(groupContainer, {
            title: '测试转改写',
            indexes: matchedIndexes.filter((index) => getRewriteRecordOrigin(index) === 'test'),
            total: originSummary.test,
        });
        rewriteRecordList.appendChild(groupContainer);
        return;
    }

    matchedIndexes.forEach((index) => {
        rewriteRecordList.appendChild(buildRewriteRecordButton(index));
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
    const originSummary = summarizeRewriteRecordOrigins();
    if (originSummary.file > 0 && originSummary.test > 0) {
        appendDataItem(rewriteFileInfo, '上传文件', `${originSummary.file} 条`);
        appendDataItem(rewriteFileInfo, '测试转改写', `${originSummary.test} 条`);
    }
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
            REWRITE_FUNCTION_CALL_OPTIONS.forEach((option) => {
                const optionNode = document.createElement('option');
                optionNode.value = option.target;
                optionNode.textContent = option.label;
                functionCallTarget.appendChild(optionNode);
            });
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
            generateButton.disabled = isObservationLoading || !functionCallTarget.value;
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

            getRewriteObservationFieldSpecs(observation).forEach(([fieldKey, labelText, fieldValue, placeholder]) => {
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
    closeRewriteRecordMenu();
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

function rebuildRewriteIndexedCache(cache, removedIndex) {
    const nextCache = new Map();
    cache.forEach((value, key) => {
        const numericKey = Number(key);
        if (!Number.isInteger(numericKey)) return;
        if (numericKey === removedIndex) return;
        const nextKey = numericKey > removedIndex ? numericKey - 1 : numericKey;
        nextCache.set(nextKey, value);
    });
    return nextCache;
}

function applyRewriteEmptyState() {
    rewriteSelectedIndex = -1;
    if (rewriteTitle) rewriteTitle.textContent = buildRewriteSourceTitle();
    if (rewriteRecordIndicator) rewriteRecordIndicator.textContent = '记录: -';
    if (rewriteCurrentRecordLabel) rewriteCurrentRecordLabel.textContent = '未选择记录';
    if (rewritePrevButton) rewritePrevButton.disabled = true;
    if (rewriteNextButton) rewriteNextButton.disabled = true;
    renderRewriteRecordList();
    renderRewriteRecordInfo(null);
    renderRewriteOriginalData(null);
    if (rewriteDialogueOutput) {
        rewriteDialogueOutput.classList.remove('rewrite-dialogue-canvas');
        rewriteDialogueOutput.innerHTML = '<p class="terminal-hint">导入文件后显示对话内容</p>';
    }
    updateRewriteAlternationStatus([]);
    updateRewriteHistoryButtons();
}

function deleteRewriteRecord(recordIndex) {
    if (!Number.isInteger(recordIndex) || recordIndex < 0 || recordIndex >= rewriteRecords.length) return;
    closeRewriteRecordMenu();
    endRewriteEditSession({ force: true });
    rewriteRecords.splice(recordIndex, 1);
    if (recordIndex < rewriteImportedRecords.length) {
        rewriteImportedRecords.splice(recordIndex, 1);
    }
    if (recordIndex < rewriteRecordOrigins.length) {
        rewriteRecordOrigins.splice(recordIndex, 1);
    }
    const nextEditCache = rebuildRewriteIndexedCache(rewriteRecordEditCache, recordIndex);
    const nextHistoryCache = rebuildRewriteIndexedCache(rewriteRecordHistoryCache, recordIndex);
    rewriteRecordEditCache.clear();
    rewriteRecordHistoryCache.clear();
    nextEditCache.forEach((value, key) => rewriteRecordEditCache.set(key, value));
    nextHistoryCache.forEach((value, key) => rewriteRecordHistoryCache.set(key, value));
    rewriteAvailableRoles = collectRewriteAvailableRoles(rewriteRecords);

    if (!rewriteRecords.length) {
        setRewriteUploadStatus('当前记录已删除，暂无可编辑记录。');
        applyRewriteEmptyState();
        renderRewriteFileInfo();
        return;
    }

    const nextIndex = Math.min(recordIndex, rewriteRecords.length - 1);
    rewriteSelectedIndex = -1;
    renderRewriteFileInfo();
    renderRewriteRecordList();
    setRewriteUploadStatus(`已删除 1 条记录，当前剩余 ${rewriteRecords.length} 条。`);
    selectRewriteRecord(nextIndex);
}

async function submitRewriteRecordReview(recordIndex) {
    if (!Number.isInteger(recordIndex) || recordIndex < 0 || recordIndex >= rewriteRecords.length) return;
    const record = rewriteRecords[recordIndex];
    if (!record || typeof record !== 'object') return;
    const recordId = resolveRewriteRecordId(record);
    if (!recordId) {
        showRewriteTransferNotice('提交评审失败：当前记录缺少 id。');
        return;
    }
    const status = getRewriteRecordStatus(record);
    if (status !== '已提交') {
        showRewriteTransferNotice(`提交评审失败：记录 ${recordId} 当前状态为“${status}”，请先完成提交。`);
        return;
    }
    const lines = getRewriteEditableLines(record, recordIndex);
    const validation = evaluateRewriteRoleAlternation(lines);
    if (validation.state !== 'good') {
        const details = Array.isArray(validation.conflictMessages) && validation.conflictMessages.length
            ? `：${validation.conflictMessages.join('；')}`
            : `：${validation.text}`;
        showRewriteTransferNotice(`提交评审失败${details}`);
        if (recordIndex !== rewriteSelectedIndex) {
            selectRewriteRecord(recordIndex);
        }
        focusRewriteConflictLines(validation.conflictIndexes || []);
        return;
    }

    closeRewriteRecordMenu();
    try {
        const payloadRecord = cloneRewriteRecordData(record) || {};
        payloadRecord.id = recordId;
        const data = await apiFetch('/api/rewrite/review', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                record_id: recordId,
                record: payloadRecord,
            }),
        });
        setRewriteUploadStatus(`记录 ${recordId} 已提交评审并写入独立 SQLite。`);
        showRewriteTransferNotice(`记录 ${data.record_id} 已提交评审。`);
    } catch (error) {
        showRewriteTransferNotice(error.message || '提交评审失败，请稍后重试。');
    }
}

async function importRewriteFile(file) {
    if (!file) return;
    const preservedTestRecords = [];
    const preservedTestImportedRecords = [];
    rewriteRecords.forEach((record, index) => {
        if (getRewriteRecordOrigin(index) !== 'test') return;
        preservedTestRecords.push(cloneRewriteRecordData(record));
        preservedTestImportedRecords.push(cloneRewriteRecordData(rewriteImportedRecords[index]) ?? cloneRewriteRecordData(record));
    });
    const text = await file.text();
    const { parsed, format } = parseRewriteSourcePayload(text, file.name);
    await resolveRewriteImportPreferences(parsed);
    const records = parseRewriteRecords(parsed, { dialogueKeyOverride: rewriteDialogueKeyPreference });
    const importedFileRecords = cloneRewriteRecordData(records) || [];
    rewriteRecordEditCache.clear();
    rewriteRecordHistoryCache.clear();
    rewriteActiveEditSession = null;
    rewriteImportedRecords = [
        ...(cloneRewriteRecordData(records) || []),
        ...preservedTestImportedRecords,
    ];
    rewriteRecords = [
        ...importedFileRecords,
        ...preservedTestRecords,
    ];
    rewriteRecordOrigins = [
        ...importedFileRecords.map(() => 'file'),
        ...preservedTestRecords.map(() => 'test'),
    ];
    syncRewriteImportedRecordsFallback();
    rewriteAvailableRoles = collectRewriteAvailableRoles(rewriteRecords);
    rewriteSelectedIndex = -1;
    rewriteSourceName = file.name;
    rewriteSourceFormat = format;
    renderRewriteFileInfo();
    renderRewriteRecordList();
    const extraMessage = preservedTestRecords.length
        ? `；已保留测试转改写 ${preservedTestRecords.length} 条`
        : '';
    setRewriteUploadStatus(`已导入 ${file.name}，共 ${records.length} 条记录${extraMessage}。`);
    if (rewriteRecords.length) {
        selectRewriteRecord(0);
    } else {
        applyRewriteEmptyState();
    }
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

function openTerminalTurnMenu({ roundIndex, hasIeDisplay, clientX, clientY }) {
    if (!terminalTurnMenu || !terminalInsertAddressIeButton || !terminalInsertTelephoneIeButton || !terminalRemoveIeButton) return;
    terminalTurnMenuState = {
        roundIndex: Number(roundIndex || 0),
        hasIeDisplay: Boolean(hasIeDisplay),
    };
    terminalInsertAddressIeButton.textContent = hasIeDisplay ? '替换为地址抽取' : '地址抽取';
    terminalInsertTelephoneIeButton.textContent = hasIeDisplay ? '替换为电话抽取' : '电话抽取';
    terminalRemoveIeButton.textContent = '移除抽取';
    terminalRemoveIeButton.hidden = !hasIeDisplay;
    terminalRemoveIeButton.classList.toggle('hidden', !hasIeDisplay);
    terminalTurnMenu.style.left = `${Math.max(16, Math.min(clientX, window.innerWidth - 252))}px`;
    terminalTurnMenu.style.top = `${Math.max(16, Math.min(clientY, window.innerHeight - 148))}px`;
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
        && !sessionBusy
        && !hasBlockingReviewPending()
        && !isReviewModalVisible()
        && isCallStartTimeValid();
    startSessionButton.disabled = !canStart;
    setSoftDisabledButton(startSessionButton, false);
    updateAutoModeButtonState();
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

async function hydrateKnownAddressPrefill(force = false, options = {}) {
    if (!authenticatedUser || !selectedScenario) return;
    const { explicit = false, autoMode = false } = options;
    const currentValue = knownAddressInput.value.trim();
    if (knownAddressExplicitOverride && !explicit && (!force || currentValue || !autoMode)) return;
    if (!force && currentValue && currentValue !== autoKnownAddressValue) return;
    const scenarioId = selectedScenario.id;
    try {
        const params = new URLSearchParams({ scenario_id: scenarioId });
        if (autoMode) {
            params.set('auto_mode', 'true');
        }
        const data = await apiFetch(`/api/mock-known-address?${params.toString()}`);
        if (!selectedScenario || selectedScenario.id !== scenarioId) return;
        autoKnownAddressValue = String(data.known_address || '').trim();
        knownAddressInput.value = autoKnownAddressValue;
        knownAddressExplicitOverride = Boolean(explicit);
    } catch (error) {
        if (authenticatedUser) {
            appendTerminalLine(`[系统错误] 预填已知地址失败：${error.message}`, 'error');
        }
    }
}

async function randomizeManualSessionInputsBeforeStart(options = {}) {
    const { autoMode = false } = options;
    selectedScenario = buildConfiguredScenarioSelection();
    prefillMockCallStartTime(true);
    updateCallStartTimeValidationState();
    await hydrateKnownAddressPrefill(true, { autoMode });
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
    appendSummaryChip(
        sessionContextSummary,
        '诉求类型',
        getManualRequestLabel(request.request_type) || request.request_type || '-',
    );
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
        ['姓名', customer.full_name],
        ['姓氏', customer.surname],
        ['性别', hiddenContext.gender || customer.gender],
        ['联系电话', customer.phone],
        ['真实地址', customer.address],
    ].forEach(([key, value]) => appendContextItem(sessionCustomerContainer, key, value));

    [
        ['诉求类型', getManualRequestLabel(request.request_type) || request.request_type],
        ['问题描述', request.issue],
        ['期望处理', request.desired_resolution],
        ['可服务时间', request.availability],
    ].forEach(([key, value]) => appendContextItem(sessionRequestContainer, key, value));

    const visiblePersonaFields = [
        ['用户画像', customer.persona],
        ['说话风格', customer.speech_style],
        ...PERSONA_HIDDEN_CONTEXT_FIELDS
        .map(([key, label]) => [label, hiddenContext[key]])
    ]
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

function isTerminalProcessingText(text = '') {
    const normalized = String(text || '').trim();
    return (
        normalized === '自动模式正在逐轮生成，请稍候...'
        || normalized === '正在初始化手工测试会话...'
    );
}

function buildTerminalProcessingLine(text = '', { animate = true } = {}) {
    const processingLine = document.createElement('div');
    processingLine.className = 'terminal-line system terminal-processing-line';

    const label = document.createElement('span');
    label.className = 'terminal-processing-label';
    label.classList.toggle('is-static', !animate);
    const title = String(text || '').trim() || '正在处理';
    label.textContent = /(\.\.\.|…)$/.test(title) ? title : `${title}...`;

    processingLine.appendChild(label);
    return processingLine;
}

function terminalIePayloadForEntityType(entityType = 'addressInfo') {
    const normalized = String(entityType || '').trim();
    if (normalized === 'telephone' || normalized === 'telephone_number') {
        return REWRITE_FUNCTION_CALL_TELEPHONE_PAYLOAD;
    }
    return REWRITE_FUNCTION_CALL_ADDRESS_PAYLOAD;
}

function terminalEntriesWithPendingIeDisplay(entries = []) {
    const renderedEntries = Array.isArray(entries) ? [...entries] : [];
    if (!pendingManualIeDisplay || !pendingManualIeDisplay.enabled) {
        return renderedEntries;
    }

    const targetRoundIndex = Number(pendingManualIeDisplay.roundIndex || 0);
    if (!targetRoundIndex) return renderedEntries;

    const nextEntries = [];
    let inserted = false;
    let suppressIeLinesForTarget = false;
    renderedEntries.forEach((entry) => {
        const entryRoundIndex = Number(entry.round_index || entry.round_count_snapshot || 0);
        if (
            entry.entry_type === 'turn'
            && entry.tone === 'user'
            && Number(entry.round_index || 0) === targetRoundIndex
        ) {
            nextEntries.push({
                ...entry,
                has_address_ie_display: true,
            });
            nextEntries.push({
                entry_type: 'message',
                tone: 'system',
                text: `function_call: ${terminalIePayloadForEntityType(pendingManualIeDisplay.entityType)}`,
                round_count_snapshot: targetRoundIndex,
                is_pending_ie_function_call: true,
            });
            inserted = true;
            suppressIeLinesForTarget = true;
            return;
        }

        if (
            suppressIeLinesForTarget
            && entry.entry_type === 'message'
            && entryRoundIndex === targetRoundIndex
            && (
                String(entry.text || '').trim().startsWith('function_call:')
                || String(entry.text || '').trim().startsWith('observation:')
            )
        ) {
            return;
        }

        if (entry.entry_type === 'turn' && entryRoundIndex !== targetRoundIndex) {
            suppressIeLinesForTarget = false;
        }
        nextEntries.push(entry);
    });

    return inserted ? nextEntries : renderedEntries;
}

function appendTerminalTurnLabel(target, entry) {
    const rawLabel = String(entry?.round_label || '').trim();
    const hasModelMarker = Boolean(entry?.model_intent_inference_attempted) || rawLabel.endsWith('*');
    const baseLabel = hasModelMarker ? rawLabel.replace(/\*+$/, '') : rawLabel;
    target.appendChild(document.createTextNode(`[${baseLabel}`));
    if (hasModelMarker) {
        const marker = document.createElement('span');
        marker.className = 'terminal-model-marker';
        marker.classList.toggle('is-unapplied', Boolean(entry?.model_intent_inference_unapplied));
        marker.textContent = '*';
        marker.title = entry?.model_intent_inference_unapplied
            ? '已调用模型，但模型结果未被流程采纳'
            : '已调用模型并采纳模型判断';
        target.appendChild(marker);
    }
    target.appendChild(document.createTextNode(']'));
}

function renderTerminalEntries(entries = []) {
    terminalOutput.innerHTML = '';
    const baseEntries = Array.isArray(entries) ? [...entries] : [];
    if (pendingManualUserEntry && currentSessionId && !sessionClosed) {
        baseEntries.push(pendingManualUserEntry);
    }
    const renderedEntries = terminalEntriesWithPendingIeDisplay(baseEntries);
    terminalOutput.classList.toggle(
        'is-processing-only',
        Boolean(terminalProcessingState?.active) && renderedEntries.length === 0,
    );
    renderedEntries.forEach((entry) => {
        if (isTerminalProcessingText(entry.text || '')) {
            terminalOutput.appendChild(
                buildTerminalProcessingLine(entry.text || '', { animate: !sessionClosed || sessionBusy }),
            );
            return;
        }

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
                appendTerminalTurnLabel(labelTrigger, entry);
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
                const isWaitingOnIe = Boolean(
                    pendingManualIeDisplay?.enabled
                    && Number(pendingManualIeDisplay.roundIndex || 0) === Number(entry.round_index || 0),
                );
                if (entry.is_pending_reply && !isWaitingOnIe) {
                    textNode.classList.add('is-awaiting-response');
                    textNode.dataset.scanText = textNode.textContent;
                    line.classList.add('is-awaiting-response');
                }
                line.appendChild(textNode);
            } else if (shouldOfferIssueReference(entry)) {
                const trigger = document.createElement('button');
                trigger.type = 'button';
                trigger.className = 'terminal-reference-trigger';
                appendTerminalTurnLabel(trigger, entry);
                trigger.appendChild(document.createTextNode(` ${entry.speaker}: ${entry.text}`));
                trigger.dataset.referenceTrigger = 'fault-issue-categories';
                line.appendChild(trigger);
            } else {
                appendTerminalTurnLabel(line, entry);
                line.appendChild(document.createTextNode(` ${entry.speaker}: ${entry.text}`));
            }
        } else {
            if (entry.is_pending_ie_function_call) {
                line.classList.add('terminal-ie-pending-line');
                const label = document.createElement('span');
                label.className = 'terminal-processing-label terminal-ie-pending-label';
                label.textContent = entry.text || '';
                line.appendChild(label);
            } else {
                line.textContent = entry.text || '';
            }
        }

        terminalOutput.appendChild(line);
    });

    if (terminalProcessingState?.active) {
        terminalOutput.appendChild(buildTerminalProcessingLine(terminalProcessingState.title, { animate: true }));
    }

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

function setSessionIdIndicator(sessionId, options = {}) {
    const indicator = document.getElementById('session-id-indicator');
    if (!indicator || !sessionIdCopyButton) return;
    const {
        label = 'Session ID',
        titleReady = '点击复制完整 Session ID',
        titleEmpty = '启动会话后可复制 Session ID',
    } = options;
    const normalized = String(sessionId || '').trim();
    indicator.textContent = normalized || '-';
    sessionIdCopyButton.disabled = !normalized;
    sessionIdCopyButton.title = normalized ? titleReady : titleEmpty;
    sessionIdCopyButton.dataset.sessionId = normalized;
    sessionIdCopyButton.dataset.copied = 'false';
    sessionIdCopyButton.dataset.label = label;
    const labelNode = sessionIdCopyButton.querySelector('.session-id-copy-label');
    if (labelNode) labelNode.textContent = label;
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
        if (currentLabelNode) currentLabelNode.textContent = sessionIdCopyButton.dataset.label || 'Session ID';
        sessionIdCopyButton.dataset.copied = 'false';
        sessionIdCopyFeedbackTimer = null;
    }, 1600);
}

function updateInputAvailability(enabled) {
    const endButton = document.getElementById('end-session-btn');
    const hasRunningManualSession = Boolean(currentSessionId) && !sessionClosed;
    const hasRunningAutoMode = Boolean(autoModeJobId) && !sessionClosed;
    const canInteract = enabled
        && !sessionBusy
        && !reviewPending
        && !isReviewModalVisible()
        && Boolean(authenticatedUser)
        && !sessionReviewLocked;
    userInput.disabled = !canInteract;
    sendButton.disabled = !canInteract;
    if (endButton) {
        endButton.disabled = (!hasRunningManualSession && !hasRunningAutoMode)
            || !authenticatedUser
            || sessionBusy
            || sessionReviewLocked;
        endButton.textContent = hasRunningAutoMode ? '强制结束自动模式' : '强制结束会话';
        endButton.title = hasRunningAutoMode ? '强制中断当前自动模式任务' : '强制结束当前手工测试会话';
    }
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

function showPendingManualUserEntry(text, options = {}) {
    const { awaitingResponse = true } = options;
    const normalizedText = String(text || '').trim();
    if (!normalizedText || !currentSessionId || sessionClosed) {
        pendingManualUserEntry = null;
        return;
    }
    pendingManualUserEntry = {
        entry_type: 'turn',
        tone: 'user',
        round_index: Number(nextRoundIndex || 1),
        round_label: String(nextRoundIndex || 1),
        speaker: '用户',
        text: normalizedText,
        has_address_ie_display: false,
        is_pending_reply: Boolean(awaitingResponse),
    };
    renderTerminalEntries(sessionTerminalEntries);
}

function clearPendingManualUserEntry() {
    if (!pendingManualUserEntry) return;
    pendingManualUserEntry = null;
    renderTerminalEntries(sessionTerminalEntries);
}

function hasBlockingReviewPending() {
    return reviewPending && !sessionClosed;
}

function clearClosedSessionReviewBeforeNewRun() {
    if (reviewPending && sessionClosed) {
        resetReviewState();
    }
}

function resetReviewState() {
    reviewPending = false;
    reviewAvailable = false;
    reviewContext = null;
    reviewSourceMode = 'manual';
    hideReviewModal();
    document.querySelectorAll('input[name="review-correctness"]').forEach((input) => {
        input.checked = false;
    });
    reviewErrorFields.classList.add('hidden');
    reviewChoiceGroup?.classList.remove('hidden');
    reviewPersistToggle?.classList.remove('hidden');
    reviewSubmitButton?.classList.remove('hidden');
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
    const reviewIdentifier = String(data?.session_id || data?.auto_mode_id || '').trim();
    if (!data.review_required || !reviewIdentifier) return;
    reviewPending = blocking;
    reviewAvailable = true;
    reviewContext = data;
    reviewCloseButton.disabled = false;
    syncReviewModalMode(data);
    const isAutoModeReview = String(data?.mode || '').trim() === 'auto_mode';
    if (data?.review_submitted) {
        reviewSummary.textContent = isAutoModeReview
            ? `自动模式评审已提交。Auto ID: ${reviewIdentifier}。如需继续处理这段对话，仍可点击下方“提交改写模式”。`
            : `评审已提交。Session ID: ${reviewIdentifier}。如需继续处理这段对话，仍可点击下方“提交改写模式”。`;
    } else if (isAutoModeReview) {
        reviewSummary.textContent = `自动模式已结束。Auto ID: ${reviewIdentifier}。如需继续处理这段对话，请点击下方“提交改写模式”。`;
    } else {
        reviewSummary.textContent = data.status === 'completed'
            ? `会话已正常结束。Session ID: ${currentSessionId}。如需继续处理这段对话，可点击下方“提交改写模式”；否则请标记当前测试流程是否正确。`
            : `会话已结束。Session ID: ${currentSessionId}。如需继续处理这段对话，可点击下方“提交改写模式”；否则请标记当前测试流程是否正确，并在有问题时指出出错流程。`;
    }
    if (reviewToRewriteButton) {
        reviewToRewriteButton.textContent = '提交改写模式';
        reviewToRewriteButton.title = '将当前测试生成的对话直接送到改写模式继续编辑';
    }
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
    const reviewIdentifier = String(data?.session_id || data?.auto_mode_id || '').trim();
    if (!data.review_required || !reviewIdentifier) return;
    reviewPending = false;
    reviewAvailable = true;
    reviewContext = data;
    syncReviewModalMode(data);
    updateReviewToggleButton();
}

function applySessionView(data) {
    if (!data || !data.session_id) return;

    stopAutoModePolling();
    pendingManualUserEntry = null;
    pendingManualIeDisplay = null;
    currentSessionId = data.session_id;
    currentAutoModeId = '';
    autoModeJobId = '';
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
    updateAutoModePreview([]);
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
        title.textContent = '请配置产品和诉求并启动会话';
        return;
    }
    const productCategory = String(scenario?.product?.category || '').trim();
    const productModel = String(scenario?.product?.model || '').trim();
    const descriptor = [productCategory, productModel].filter(Boolean).join(' ');
    title.textContent = `${scenario.scenario_id} | ${String(scenario?.product?.brand || '').trim()} ${descriptor}`.trim();
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

function updateAutoModePreview(lines = []) {
    if (!autoModePreviewContainer) return;
    const normalizedLines = Array.isArray(lines)
        ? lines.map((line) => String(line || '').trim()).filter(Boolean)
        : [];
    if (!normalizedLines.length) {
        autoModePreviewContainer.innerHTML = '<p class="terminal-hint">点击自动模式后显示</p>';
        return;
    }
    autoModePreviewContainer.innerHTML = '';
    normalizedLines.forEach((line) => {
        const item = document.createElement('div');
        item.className = 'data-item auto-mode-preview-item';
        const separatorIndex = line.search(/[：:]/);
        const key = separatorIndex > 0 ? line.slice(0, separatorIndex).trim() : '预演';
        const value = separatorIndex > 0 ? line.slice(separatorIndex + 1).trim() : line;
        const keyNode = document.createElement('span');
        keyNode.className = 'data-key';
        keyNode.textContent = key;
        const valueNode = document.createElement('span');
        valueNode.className = 'data-value filled';
        valueNode.textContent = value;
        item.append(keyNode, valueNode);
        autoModePreviewContainer.appendChild(item);
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
    const sourceUsers = chatMentionUsersCache.length ? chatMentionUsersCache : chatOnlineUsersCache;
    const uniqueByUsername = new Map();
    sourceUsers.forEach((user) => {
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
    if (event.target.closest('.chat-launcher-unread')) return;
    event.preventDefault();
    const currentLeft = parseFloat(chatLauncher.style.left);
    const currentTop = parseFloat(chatLauncher.style.top);
    const fallbackRect = resolveChatLauncherRect();
    chatLauncherDragState = {
        pointerId: event.pointerId,
        offsetX: event.clientX - (Number.isFinite(currentLeft) ? currentLeft : fallbackRect.left),
        offsetY: event.clientY - (Number.isFinite(currentTop) ? currentTop : fallbackRect.top),
        startX: event.clientX,
        startY: event.clientY,
        dragged: false,
    };
}

function handleChatLauncherDrag(event) {
    if (!chatLauncherDragState || event.pointerId !== chatLauncherDragState.pointerId) return;
    const movedX = event.clientX - chatLauncherDragState.startX;
    const movedY = event.clientY - chatLauncherDragState.startY;
    if (!chatLauncherDragState.dragged) {
        if (Math.hypot(movedX, movedY) < CHAT_LAUNCHER_DRAG_THRESHOLD) return;
        chatLauncherDragState.dragged = true;
    }
    const bounds = getChatViewportBounds();
    const width = Math.max(chatLauncher.offsetWidth || 172, 120);
    const height = Math.max(chatLauncher.offsetHeight || 50, 40);
    const nextLeft = clamp(event.clientX - chatLauncherDragState.offsetX, CHAT_VIEWPORT_MARGIN, bounds.width - width - CHAT_VIEWPORT_MARGIN);
    const nextTop = clamp(event.clientY - chatLauncherDragState.offsetY, CHAT_VIEWPORT_MARGIN, bounds.height - height - CHAT_VIEWPORT_MARGIN);
    chatLauncher.style.left = `${nextLeft}px`;
    chatLauncher.style.top = `${nextTop}px`;
    chatLauncher.style.right = 'auto';
    chatLauncher.style.bottom = 'auto';
}

function endChatLauncherDrag(event) {
    if (!chatLauncherDragState || (event && event.pointerId !== chatLauncherDragState.pointerId)) return;
    const dragged = chatLauncherDragState.dragged === true;
    chatLauncherDragState = null;
    if (!dragged) return;
    chatLauncherSuppressClickUntil = Date.now() + CHAT_LAUNCHER_DRAG_CLICK_SUPPRESS_MS;
    syncChatLauncherStateFromDom();
    persistChatWindowState();
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
    chatMentionUsersCache = [];
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
    const derivedLatestMessageId = Math.max(serverLatest, ...chatMessages.map((item) => Number(item.id || 0)));
    chatLatestMessageId = shouldReplaceMessages
        ? derivedLatestMessageId
        : Math.max(previousLatest, derivedLatestMessageId);
    chatSnapshotRevision = serverSnapshotRevision;
    if (serverReset) {
        markChatAsRead(chatLatestMessageId, { persist: false });
    }

    renderChatMessages({ forceScroll: forceScroll || isInitialSnapshot });
    renderChatEditPreview();
    renderChatReplyPreview();
    chatStateInitialized = true;
    recomputeChatAttentionState({ persistReadState: true });
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
    if (chatWindowState.read_username && chatWindowState.read_username !== String(authenticatedUser?.username || '').trim()) {
        chatWindowState.last_read_message_id = 0;
    }
    chatWindowState.read_username = String(authenticatedUser?.username || '').trim();
    chatWindowState.visible = false;
    chatWindowState.launcher_left = null;
    chatWindowState.launcher_top = null;
    persistChatWindowState();
    applyChatWindowRect();
    setChatWindowVisibility(false, { persist: false });
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
    availableScenarios = [];
    currentSessionId = null;
    stopAutoModePolling();
    currentAutoModeId = '';
    currentSlotKeys = [];
    sessionClosed = true;
    sessionBusy = false;
    sessionReviewLocked = false;
    sessionTerminalEntries = [];
    pendingManualUserEntry = null;
    terminalProcessingState = null;
    sessionStartedAt = '';
    sessionEndedAt = '';
    autoKnownAddressValue = '';
    knownAddressExplicitOverride = false;
    autoCallStartTimeValue = '';
    stopSessionTimer();
    refreshSessionTimerDisplay();
    hideIssueReferencePopover();
    hideTextMagnifier();
    resetReviewState();
    updateScenarioHeader(null);
    updateSessionContext(null, {});
    updateInspector({}, {});
    updateAutoModePreview([]);
    setSessionStatus('idle');
    setSessionIdIndicator('');
    setNextRound(1);
    updateInputAvailability(false);
    knownAddressInput.value = '';
    callStartTimeInput.value = '';
    useSessionStartTimeCheckbox.checked = false;
    prefillMockCallStartTime(true);
    updateCallStartTimeValidationState();
    sanitizeManualMaxRoundsInput();
    updateStartSessionButtonState();
    renderScenarioList();
    document.getElementById('terminal-output').innerHTML = '';
    resetRewriteWorkspace();
}

function applyAuthenticatedState(user) {
    authenticatedUser = user;
    authUserName.textContent = `测试管理员: ${user.username || '-'}`;
    setAuthError('');
    updateCallStartTimeValidationState();
    sanitizeManualMaxRoundsInput();
    syncManualScenarioSelection();
    updateStartSessionButtonState();
    initializeChatWindow();
    refreshChatMentionUsers().catch(() => {});
    startChatPolling();
    syncAppModeView();
}

function applyLoggedOutState(message = '') {
    authenticatedUser = null;
    closeBlockingActionNotice();
    stopAutoModePolling();
    authUserName.textContent = '未登录';
    stopChatPolling();
    resetChatRuntime();
    setPasswordVisibility(false);
    loginPassword.value = '';
    setAuthError(message);
    activeAppMode = 'manual';
    resetWorkspace();
    syncAppModeView();
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
    const unauthorizedMode = String(options?.unauthorizedMode || 'logout').trim();
    const requestOptions = { ...options };
    delete requestOptions.unauthorizedMode;
    const response = await fetch(url, requestOptions);
    const data = await safeJson(response);
    if (response.status === 401) {
        if (unauthorizedMode !== 'ignore') {
            applyLoggedOutState(data.detail || '登录状态已失效，请重新登录。');
        }
        throw new Error(data.detail || '请先登录');
    }
    if (!response.ok) {
        throw new Error(data.detail || '请求失败');
    }
    return data;
}

async function loadScenarios() {
    availableScenarios = [];
    renderScenarioList();
}

function selectScenario(scenario) {
    closeBlockingActionNotice();
    selectedScenario = scenario;
    renderScenarioList();
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
            unauthorizedMode: 'ignore',
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
        prepareOptionalReview({
            ...(reviewContext || {}),
            review_required: true,
            session_id: data.session_id || currentSessionId,
            mode: reviewSourceMode || 'manual',
            review_submitted: true,
        });
        hideReviewModal();
        updateReviewToggleButton();
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

function syncReviewModalMode(data = {}) {
    const isAutoModeReview = String(data?.mode || reviewSourceMode || '').trim() === 'auto_mode';
    const reviewSubmitted = Boolean(data?.review_submitted);
    reviewSourceMode = isAutoModeReview ? 'auto_mode' : 'manual';
    reviewChoiceGroup?.classList.toggle('hidden', isAutoModeReview || reviewSubmitted);
    reviewPersistToggle?.classList.toggle('hidden', isAutoModeReview || reviewSubmitted);
    reviewSubmitButton?.classList.toggle('hidden', isAutoModeReview || reviewSubmitted);
    reviewSubmitButton.disabled = reviewSubmitted;
    if (isAutoModeReview || reviewSubmitted) {
        reviewErrorFields.classList.add('hidden');
    }
    if (isAutoModeReview) {
        document.querySelectorAll('input[name="review-correctness"]').forEach((input) => {
            input.checked = false;
        });
    }
}

async function startSession() {
    if (hasBlockingReviewPending()) {
        appendTerminalLine('请先完成上一条测试记录的评审；如已关闭弹窗，可点击“打开评审”继续。', 'error');
        return;
    }
    clearClosedSessionReviewBeforeNewRun();

    await randomizeManualSessionInputsBeforeStart({ autoMode: false });
    if (!updateCallStartTimeValidationState()) {
        updateStartSessionButtonState();
        return;
    }
    const historyDeviceConfig = getHistoryDeviceConfig();
    const payload = {
        scenario_id: '',
        auto_generate_hidden_settings: document.getElementById('auto-hidden-settings').checked,
        product_category: selectedScenario.product_category,
        request_type: selectedScenario.request_type,
        history_device_brand: historyDeviceConfig.brand,
        history_device_category: historyDeviceConfig.category,
        history_device_purchase_date: historyDeviceConfig.purchase_date,
        known_address: getKnownAddressPayloadValue({ includeAutoPrefill: true }),
        ivr_utterance: '空气能热水器需要维修',
        call_start_time: callStartTimeInput.value.trim(),
        use_session_start_time_as_call_start_time: useSessionStartTimeCheckbox.checked,
        max_rounds: getManualMaxRoundsValue(),
        persist_to_db: document.getElementById('persist-to-db').checked,
    };

    const output = document.getElementById('terminal-output');
    output.innerHTML = '';
    pendingManualIeDisplay = null;
    if (payload.auto_generate_hidden_settings) {
        setTerminalProcessingState({
            active: true,
            title: '正在生成隐藏设定',
            detail: '系统正在构建本次会话的人设、地址计划和隐藏上下文，请稍候。',
        });
    } else {
        appendTerminalLine('正在初始化手工测试会话...', 'system');
    }
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
        setTerminalProcessingState(null);
        applySessionView(data);
    } catch (error) {
        setTerminalProcessingState(null);
        currentSessionId = null;
        currentSlotKeys = [];
        sessionClosed = true;
        sessionTerminalEntries = [];
        pendingManualIeDisplay = null;
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

function applyAutoModeView(data) {
    autoModeJobId = String(data?.job_id || autoModeJobId || '').trim();
    currentAutoModeId = String(data?.auto_mode_id || currentAutoModeId || '').trim();
    currentSessionId = null;
    currentSlotKeys = Object.keys(data?.collected_slots || {});
    sessionClosed = Boolean(data?.session_closed);
    sessionTerminalEntries = Array.isArray(data?.terminal_entries) ? data.terminal_entries : [];
    sessionReviewLocked = false;
    sessionStartedAt = String(data?.started_at || '').trim();
    sessionEndedAt = String(data?.ended_at || '').trim();
    resetReviewState();
    setSessionStatus(data?.status || 'completed');
    setSessionIdIndicator(data?.auto_mode_id || '', {
        label: 'Auto ID',
        titleReady: '点击复制完整自动模式 ID',
        titleEmpty: '自动模式启动后可复制 Auto ID',
    });
    setNextRound(Number(data?.next_round_index || 1) || 1);
    updateScenarioHeader(data?.scenario || null);
    updateSessionContext(data?.scenario || null, data?.session_config || {});
    updateInspector(data?.collected_slots || {}, data?.runtime_state || {}, data?.scenario || null);
    updateAutoModePreview(data?.auto_mode_preview_lines || []);
    renderTerminalEntries(sessionTerminalEntries);
    hideIssueReferencePopover();
    closeTerminalTurnMenu();
    syncSessionTimer();
    updateInputAvailability(false);
    if (Boolean(data?.session_closed) && Boolean(data?.job_done)) {
        resetReviewState();
        openReviewModal(
            {
                review_required: true,
                mode: 'auto_mode',
                auto_mode_id: data?.auto_mode_id || autoModeJobId,
                status: data?.status || 'completed',
                review_options: [],
                persist_to_db_default: false,
            },
            { blocking: false },
        );
    }
}

function stopAutoModePolling() {
    autoModeJobId = '';
    autoModePollInFlight = false;
    if (autoModePollTimer !== null) {
        window.clearTimeout(autoModePollTimer);
        autoModePollTimer = null;
    }
}

function scheduleAutoModePoll(delayMs = 700) {
    if (!autoModeJobId) return;
    if (autoModePollTimer !== null) {
        window.clearTimeout(autoModePollTimer);
    }
    autoModePollTimer = window.setTimeout(() => {
        autoModePollTimer = null;
        void pollAutoModeJob();
    }, delayMs);
}

async function pollAutoModeJob() {
    if (!autoModeJobId || autoModePollInFlight) return;
    autoModePollInFlight = true;
    let errorMessage = '';
    try {
        const data = await apiFetch(`/api/session/auto-mode/${encodeURIComponent(autoModeJobId)}`);
        applyAutoModeView(data);
        if (data?.job_done) {
            stopAutoModePolling();
            setSessionBusyState(false);
            return;
        }
        scheduleAutoModePoll();
    } catch (error) {
        errorMessage = error.message;
        stopAutoModePolling();
        setSessionBusyState(false);
    } finally {
        autoModePollInFlight = false;
        if (errorMessage) {
            appendTerminalLine(`[系统错误] ${errorMessage}`, 'error');
        }
    }
}

async function runAutoMode() {
    if (!isTestAdminUser()) return;
    if (hasBlockingReviewPending()) {
        appendTerminalLine('请先完成上一条测试记录的评审；如已关闭弹窗，可点击“打开评审”继续。', 'error');
        return;
    }
    if (currentSessionId && !sessionClosed) {
        appendTerminalLine('请先结束当前手工测试会话，再执行自动模式。', 'error');
        return;
    }
    clearClosedSessionReviewBeforeNewRun();

    await randomizeManualSessionInputsBeforeStart({ autoMode: true });
    if (!updateCallStartTimeValidationState()) {
        updateStartSessionButtonState();
        return;
    }
    const historyDeviceConfig = getHistoryDeviceConfig();
    const autoGenerateHiddenSettings = document.getElementById('auto-hidden-settings').checked;
    const payload = {
        scenario_id: '',
        auto_generate_hidden_settings: autoGenerateHiddenSettings,
        product_category: selectedScenario.product_category,
        request_type: selectedScenario.request_type,
        history_device_brand: historyDeviceConfig.brand,
        history_device_category: historyDeviceConfig.category,
        history_device_purchase_date: historyDeviceConfig.purchase_date,
        known_address: getKnownAddressPayloadValue({ includeAutoPrefill: true }),
        ivr_utterance: '空气能热水器需要维修',
        call_start_time: callStartTimeInput.value.trim(),
        use_session_start_time_as_call_start_time: useSessionStartTimeCheckbox.checked,
        max_rounds: getManualMaxRoundsValue(),
        persist_to_db: document.getElementById('persist-to-db').checked,
    };

    stopAutoModePolling();
    terminalOutput.innerHTML = '';
    if (payload.auto_generate_hidden_settings) {
        setTerminalProcessingState({
            active: true,
            title: '正在生成隐藏设定',
            detail: '自动模式正在准备用户画像、地址回答计划和隐藏上下文，随后将开始逐轮生成。',
        });
    } else {
        appendTerminalLine('正在执行自动模式...', 'system');
    }
    setSessionBusyState(true);
    let errorMessage = '';
    try {
        const data = await apiFetch('/api/session/auto-mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        setTerminalProcessingState(null);
        applyAutoModeView(data);
        if (data?.job_done) {
            stopAutoModePolling();
            setSessionBusyState(false);
        } else {
            autoModeJobId = String(data?.job_id || '').trim();
            scheduleAutoModePoll();
            setSessionBusyState(false);
        }
    } catch (error) {
        setTerminalProcessingState(null);
        errorMessage = error.message;
        stopAutoModePolling();
        setSessionBusyState(false);
    } finally {
        if (errorMessage) {
            appendTerminalLine(`[系统错误] ${errorMessage}`, 'error');
        }
    }
}

async function forceEndSession() {
    if (autoModeJobId && !sessionClosed) {
        setSessionBusyState(true);
        let errorMessage = '';
        try {
            const data = await apiFetch(`/api/session/auto-mode/${encodeURIComponent(autoModeJobId)}/abort`, {
                method: 'POST',
            });
            applyAutoModeView(data);
            if (data?.job_done) {
                stopAutoModePolling();
                setSessionBusyState(false);
            } else {
                scheduleAutoModePoll(450);
                setSessionBusyState(false);
            }
        } catch (error) {
            errorMessage = error.message;
            setSessionBusyState(false);
        } finally {
            if (errorMessage) {
                appendTerminalLine(`[系统错误] ${errorMessage}`, 'error');
            }
        }
        return;
    }

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
    showPendingManualUserEntry(rawText, { awaitingResponse: false });
    setSessionBusyState(true);
    let errorMessage = '';
    try {
        try {
            const pendingIe = await apiFetch('/api/session/pending-ie', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: currentSessionId, text: rawText }),
            });
            const pendingIeEntityType = String(pendingIe?.entity_type || '').trim();
            if (pendingIeEntityType) {
                pendingManualIeDisplay = {
                    enabled: true,
                    roundIndex: Number(pendingIe?.round_index || nextRoundIndex || 1),
                    entityType: pendingIeEntityType,
                };
            } else if (pendingManualUserEntry) {
                pendingManualUserEntry.is_pending_reply = true;
            }
        } catch (_pendingError) {
            if (pendingManualUserEntry) {
                pendingManualUserEntry.is_pending_reply = true;
            }
        }
        renderTerminalEntries(sessionTerminalEntries);
        const data = await apiFetch('/api/session/respond', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: currentSessionId, text: rawText }),
        });
        applySessionView(data);
    } catch (error) {
        errorMessage = error.message;
    } finally {
        if (errorMessage) {
            clearPendingManualUserEntry();
            pendingManualIeDisplay = null;
        }
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

async function toggleIeDisplayForRound(roundIndex, enabled, entityType = 'addressInfo') {
    if (!currentSessionId || sessionBusy || roundIndex < 1) return;

    closeTerminalTurnMenu();
    pendingManualIeDisplay = enabled
        ? {
            enabled: true,
            roundIndex: Number(roundIndex || 0),
            entityType,
        }
        : null;
    renderTerminalEntries(sessionTerminalEntries);
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
                entity_type: entityType,
            }),
        });
        pendingManualIeDisplay = null;
        applySessionView(data);
    } catch (error) {
        pendingManualIeDisplay = null;
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
manualProductCategorySelect?.addEventListener('change', () => {
    syncManualScenarioSelection({ refreshKnownAddress: true });
});
manualRequestTypeSelect?.addEventListener('change', () => {
    syncManualScenarioSelection({ refreshKnownAddress: true });
});
historyDeviceBrandSelect?.addEventListener('change', () => {
    syncHistoryDeviceCategoryOptions();
    syncManualScenarioSelection({ refreshKnownAddress: false });
});
historyDeviceCategorySelect?.addEventListener('change', () => {
    syncManualScenarioSelection({ refreshKnownAddress: false });
});
[
    historyDevicePurchaseYearInput,
    historyDevicePurchaseMonthInput,
    historyDevicePurchaseDayInput,
].forEach((input) => {
    input?.addEventListener('input', () => {
        input.value = String(input.value || '').replace(/\D+/g, '');
        syncHistoryDeviceDateValueFromParts();
        syncManualScenarioSelection({ refreshKnownAddress: false });
    });
    input?.addEventListener('blur', () => {
        if (input === historyDevicePurchaseMonthInput || input === historyDevicePurchaseDayInput) {
            const value = String(input.value || '').trim();
            if (value) input.value = String(Number(value));
        }
        syncHistoryDeviceDateValueFromParts();
        syncManualScenarioSelection({ refreshKnownAddress: false });
    });
});
historyDevicePurchaseDateInput?.addEventListener('input', () => {
    setHistoryDeviceDateParts(historyDevicePurchaseDateInput.value);
    syncManualScenarioSelection({ refreshKnownAddress: false });
});
historyDeviceCalendarButton?.addEventListener('click', openHistoryDeviceCalendarPicker);
generateHistoryDeviceDateButton?.addEventListener('click', () => {
    setHistoryDeviceDateParts(randomHistoryDevicePurchaseDate());
    syncManualScenarioSelection({ refreshKnownAddress: false });
});
clearHistoryDeviceButton?.addEventListener('click', clearHistoryDeviceConfig);
document.getElementById('logout-btn').onclick = logout;
startSessionButton.onclick = () => {
    startSession();
};
if (autoModeButton) {
    autoModeButton.onclick = () => {
        runAutoMode();
    };
}
blockingActionNoticeCloseButton?.addEventListener('click', closeBlockingActionNotice);
blockingActionNotice?.addEventListener('click', (event) => {
    if (event.target === blockingActionNotice) {
        closeBlockingActionNotice();
    }
});
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
            rewriteUploadStatus.textContent = '已取消导出。';
        }
    });
}
if (rewriteExportCancelButton) {
    rewriteExportCancelButton.addEventListener('click', () => {
        closeRewriteExportModal();
        if (rewriteUploadStatus) {
            rewriteUploadStatus.textContent = '已取消导出。';
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
if (rewriteExportScopeChoices) {
    rewriteExportScopeChoices.addEventListener('click', (event) => {
        const button = event.target.closest('[data-rewrite-export-scope]');
        if (!button) return;
        const scope = String(button.dataset.rewriteExportScope || 'all').trim() || 'all';
        exportRewriteScopeWithValidation(scope);
    });
}
if (rewriteExportModal) {
    rewriteExportModal.addEventListener('click', (event) => {
        if (event.target === rewriteExportModal || event.target.classList.contains('modal-backdrop')) {
            closeRewriteExportModal();
            if (rewriteUploadStatus) {
                rewriteUploadStatus.textContent = '已取消导出。';
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
        if (rewriteFileInput) rewriteFileInput.value = '';
        renderRewriteFileInfo();
        renderRewriteRecordList();
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
    knownAddressExplicitOverride = true;
});
generateKnownAddressButton.addEventListener('click', () => {
    hydrateKnownAddressPrefill(true, { explicit: true });
});
generateCallStartTimeButton.addEventListener('click', () => {
    useSessionStartTimeCheckbox.checked = false;
    prefillMockCallStartTime(true);
    updateCallStartTimeValidationState();
    updateStartSessionButtonState();
});
knownAddressInput.addEventListener('input', () => {
    const currentValue = knownAddressInput.value.trim();
    if (!currentValue) {
        autoKnownAddressValue = '';
        knownAddressExplicitOverride = true;
    } else if (currentValue !== autoKnownAddressValue) {
        autoKnownAddressValue = '';
        knownAddressExplicitOverride = true;
    } else {
        knownAddressExplicitOverride = false;
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
        hasIeDisplay: userTextNode.dataset.hasAddressIeDisplay === 'true',
        clientX: event.clientX,
        clientY: event.clientY,
    });
});
rewriteRecordList.addEventListener('contextmenu', (event) => {
    const recordNode = event.target.closest('.scenario-item');
    if (!recordNode) {
        closeRewriteRecordMenu();
        return;
    }
    event.preventDefault();
    const recordIndex = Number(recordNode.dataset.recordIndex || '-1');
    if (!Number.isInteger(recordIndex) || recordIndex < 0) {
        closeRewriteRecordMenu();
        return;
    }
    openRewriteRecordMenu(recordIndex, event.clientX, event.clientY);
});
issueReferenceCloseButton.addEventListener('click', hideIssueReferencePopover);
terminalInsertAddressIeButton.addEventListener('click', () => {
    if (!terminalTurnMenuState) return;
    toggleIeDisplayForRound(
        Number(terminalTurnMenuState.roundIndex || 0),
        true,
        'addressInfo',
    ).catch(() => {});
});
terminalInsertTelephoneIeButton.addEventListener('click', () => {
    if (!terminalTurnMenuState) return;
    toggleIeDisplayForRound(
        Number(terminalTurnMenuState.roundIndex || 0),
        true,
        'telephone',
    ).catch(() => {});
});
terminalRemoveIeButton.addEventListener('click', () => {
    if (!terminalTurnMenuState) return;
    toggleIeDisplayForRound(
        Number(terminalTurnMenuState.roundIndex || 0),
        false,
    ).catch(() => {});
});
rewriteRecordDeleteButton?.addEventListener('click', () => {
    if (!rewriteRecordMenuState) return;
    deleteRewriteRecord(Number(rewriteRecordMenuState.recordIndex));
});
rewriteRecordReviewButton?.addEventListener('click', () => {
    if (!rewriteRecordMenuState) return;
    void submitRewriteRecordReview(Number(rewriteRecordMenuState.recordIndex));
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
    if (!rewriteRecordMenu || rewriteRecordMenu.classList.contains('hidden')) return;
    if (event.target.closest('#rewrite-record-menu')) return;
    closeRewriteRecordMenu();
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
window.addEventListener('resize', closeRewriteRecordMenu);
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
    applyManualShellWidthConstraints();
    applyManualShellLayoutState();
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
if (prefersReducedMotionQuery?.addEventListener) {
    prefersReducedMotionQuery.addEventListener('change', (event) => {
        applyReducedMotionPreference(event.matches);
    });
} else if (prefersReducedMotionQuery?.addListener) {
    prefersReducedMotionQuery.addListener((event) => {
        applyReducedMotionPreference(event.matches);
    });
}
applyReducedMotionPreference(prefersReducedMotion);
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
document.addEventListener('pointermove', handleManualShellResize);
document.addEventListener('pointerup', endManualShellResize);
document.addEventListener('pointercancel', endManualShellResize);
if (manualLeftSplitter) {
    manualLeftSplitter.addEventListener('pointerdown', (event) => {
        beginManualShellResize('left', event);
    });
    manualLeftSplitter.addEventListener('keydown', (event) => {
        if (window.innerWidth <= 1200) return;
        if (event.key === 'ArrowLeft') {
            event.preventDefault();
            manualShellLeftHidden = false;
            manualShellLeftWidth = Math.max(manualShellLeftWidth - 24, MANUAL_SHELL_LEFT_MIN_PX);
            if (manualShellLeftWidth <= MANUAL_SHELL_HIDE_THRESHOLD_PX + 8) {
                manualShellLeftHidden = true;
            }
            applyManualShellWidthConstraints();
            applyManualShellLayoutState();
            persistManualShellLayoutState();
        }
        if (event.key === 'ArrowRight') {
            event.preventDefault();
            manualShellLeftHidden = false;
            manualShellLeftWidth = Math.min(
                Math.max(manualShellLeftWidth || MANUAL_SHELL_LEFT_MIN_PX, MANUAL_SHELL_LEFT_MIN_PX) + 24,
                MANUAL_SHELL_LEFT_MAX_PX,
            );
            applyManualShellWidthConstraints();
            applyManualShellLayoutState();
            persistManualShellLayoutState();
        }
    });
}
if (manualRightSplitter) {
    manualRightSplitter.addEventListener('pointerdown', (event) => {
        beginManualShellResize('right', event);
    });
    manualRightSplitter.addEventListener('keydown', (event) => {
        if (window.innerWidth <= 1200) return;
        if (event.key === 'ArrowLeft') {
            event.preventDefault();
            manualShellRightHidden = false;
            manualShellRightWidth = Math.min(
                Math.max(manualShellRightWidth || MANUAL_SHELL_RIGHT_MIN_PX, MANUAL_SHELL_RIGHT_MIN_PX) + 24,
                MANUAL_SHELL_RIGHT_MAX_PX,
            );
            applyManualShellWidthConstraints();
            applyManualShellLayoutState();
            persistManualShellLayoutState();
        }
        if (event.key === 'ArrowRight') {
            event.preventDefault();
            manualShellRightHidden = false;
            manualShellRightWidth = Math.max(manualShellRightWidth - 24, MANUAL_SHELL_RIGHT_MIN_PX);
            if (manualShellRightWidth <= MANUAL_SHELL_HIDE_THRESHOLD_PX + 8) {
                manualShellRightHidden = true;
            }
            applyManualShellWidthConstraints();
            applyManualShellLayoutState();
            persistManualShellLayoutState();
        }
    });
}

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
{
    const initialManualShellLayout = loadManualShellLayoutState();
    manualShellLeftHidden = initialManualShellLayout.leftHidden;
    manualShellRightHidden = initialManualShellLayout.rightHidden;
    manualShellLeftWidth = initialManualShellLayout.leftWidth;
    manualShellRightWidth = initialManualShellLayout.rightWidth;
}
resetReviewState();
setPasswordVisibility(false);
prefillMockCallStartTime(true);
syncHistoryDeviceCategoryOptions();
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

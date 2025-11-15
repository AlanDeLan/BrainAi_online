// --- Authentication State ---
let authToken = localStorage.getItem('authToken');
let currentUser = JSON.parse(localStorage.getItem('currentUser') || 'null');

// --- Кешування DOM елементів ---
const elements = {
    form: document.getElementById('chat-form'),
    input: document.getElementById('message-input'),
    chatWindow: document.getElementById('chat-window'),
    archetypeSelect: document.getElementById('archetype'),
    historyBtn: document.getElementById('history-btn'),
    historyModal: document.getElementById('history-modal'),
    closeModalBtn: document.querySelector('.close-btn'),
    historyListContainer: document.getElementById('history-list-container'),
    historyViewContainer: document.querySelector('#history-view-container pre code'),
    rememberChatToggle: document.getElementById('remember-chat-toggle'),
    newChatBtn: document.getElementById('new-chat-btn'),
    configBtn: document.getElementById('config-btn'),
    configModal: document.getElementById('config-modal'),
    configCloseBtn: document.querySelector('.config-close-btn'),
    configLoading: document.getElementById('config-loading'),
    configFormWrapper: document.getElementById('config-form-wrapper'),
    archetypesList: document.getElementById('archetypes-list'),
    addArchetypeBtn: document.getElementById('add-archetype-btn'),
    saveConfigBtn: document.getElementById('save-config-btn'),
    configMessage: document.getElementById('config-message'),
    aiProviderBtn: document.getElementById('ai-provider-btn'),
    aiProviderModal: document.getElementById('ai-provider-modal'),
    aiProviderCloseBtn: document.querySelector('.ai-provider-close-btn'),
    aiProviderLoading: document.getElementById('ai-provider-loading'),
    aiProviderFormWrapper: document.getElementById('ai-provider-form-wrapper'),
    aiProviderSelect: document.getElementById('ai-provider-select'),
    googleApiKey: document.getElementById('google-api-key'),
    openaiApiKey: document.getElementById('openai-api-key'),
    openaiBaseUrl: document.getElementById('openai-base-url'),
    saveAiProviderBtn: document.getElementById('save-ai-provider-btn'),
    aiProviderMessage: document.getElementById('ai-provider-message'),
    aiProviderModels: document.getElementById('ai-provider-models'),
    vectorDbBtn: document.getElementById('vector-db-btn'),
    vectorDbModal: document.getElementById('vector-db-modal'),
    vectorDbCloseBtn: document.querySelector('.vector-db-close-btn'),
    vectorDbLoading: document.getElementById('vector-db-loading'),
    vectorDbWrapper: document.getElementById('vector-db-wrapper'),
    vectorDbEntriesList: document.getElementById('vector-db-entries-list'),
    vectorDbEntryView: document.getElementById('vector-db-entry-view'),
    statsBtn: document.getElementById('stats-btn'),
    statsModal: document.getElementById('stats-modal'),
    statsCloseBtn: document.querySelector('.stats-close-btn'),
    statsLoading: document.getElementById('stats-loading'),
    statsWrapper: document.getElementById('stats-wrapper'),
    statsContent: document.getElementById('stats-content'),
    refreshStatsBtn: document.getElementById('refresh-stats-btn'),
    resetStatsBtn: document.getElementById('reset-stats-btn'),
    menuBtn: document.getElementById('menu-btn'),
    langUkBtn: document.getElementById('lang-uk-btn'),
    langEnBtn: document.getElementById('lang-en-btn'),
    themeToggleBtn: document.getElementById('theme-toggle-btn'),
    dropdownMenu: document.getElementById('dropdown-menu'),
    shutdownBtn: document.getElementById('shutdown-btn'),
    uploadFileBtn: document.getElementById('upload-file-btn'),
    uploadFileModal: document.getElementById('upload-file-modal'),
    uploadFileCloseBtn: document.querySelector('.upload-file-close-btn'),
    uploadFileSubmitBtn: document.getElementById('upload-file-submit-btn'),
    uploadFileCancelBtn: document.getElementById('upload-file-cancel-btn'),
    fileInput: document.getElementById('file-input'),
    uploadFileProgress: document.getElementById('upload-file-progress'),
    uploadFileStatus: document.getElementById('upload-file-status'),
    uploadFileProgressBar: document.getElementById('upload-file-progress-bar'),
    uploadFileMessage: document.getElementById('upload-file-message'),
    authModal: document.getElementById('auth-modal'),
    loginTab: document.getElementById('login-tab'),
    registerTab: document.getElementById('register-tab'),
    loginForm: document.getElementById('login-form'),
    registerForm: document.getElementById('register-form'),
    loginEmail: document.getElementById('login-email'),
    loginPassword: document.getElementById('login-password'),
    loginSubmitBtn: document.getElementById('login-submit-btn'),
    loginMessage: document.getElementById('login-message'),
    registerUsername: document.getElementById('register-username'),
    registerEmail: document.getElementById('register-email'),
    registerPassword: document.getElementById('register-password'),
    registerSubmitBtn: document.getElementById('register-submit-btn'),
    registerMessage: document.getElementById('register-message'),
    userEmail: document.getElementById('user-email'),
    logoutBtn: document.getElementById('logout-btn'),
};

let currentChatId = null;
let currentArchetypeForChat = null;

// === AUTHENTICATION FUNCTIONS ===

function showAuthModal() {
    elements.authModal.classList.remove('hidden');
}

function hideAuthModal() {
    elements.authModal.classList.add('hidden');
}

function updateUserUI() {
    if (authToken && currentUser) {
        elements.userEmail.textContent = currentUser.email;
        elements.logoutBtn.classList.remove('hidden');
        hideAuthModal();
    } else {
        elements.userEmail.textContent = '';
        elements.logoutBtn.classList.add('hidden');
        showAuthModal();
    }
}

async function handleLogin(email, password) {
    try {
        elements.loginSubmitBtn.disabled = true;
        elements.loginMessage.textContent = 'Вхід...';
        elements.loginMessage.className = 'auth-message';
        
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            authToken = data.access_token;
            currentUser = { email: data.email, user_id: data.user_id };
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            
            elements.loginMessage.textContent = 'Успішний вхід!';
            elements.loginMessage.className = 'auth-message success';
            
            setTimeout(() => {
                updateUserUI();
                elements.loginEmail.value = '';
                elements.loginPassword.value = '';
                elements.loginMessage.textContent = '';
            }, 1000);
        } else {
            elements.loginMessage.textContent = data.error || 'Невірний email або пароль';
            elements.loginMessage.className = 'auth-message error';
        }
    } catch (error) {
        elements.loginMessage.textContent = 'Помилка з\'єднання';
        elements.loginMessage.className = 'auth-message error';
    } finally {
        elements.loginSubmitBtn.disabled = false;
    }
}

async function handleRegister(username, email, password) {
    try {
        elements.registerSubmitBtn.disabled = true;
        elements.registerMessage.textContent = 'Реєстрація...';
        elements.registerMessage.className = 'auth-message';
        
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            elements.registerMessage.textContent = 'Реєстрація успішна! Входимо...';
            elements.registerMessage.className = 'auth-message success';
            
            // Auto-login after registration
            setTimeout(() => {
                handleLogin(email, password);
                elements.registerUsername.value = '';
                elements.registerEmail.value = '';
                elements.registerPassword.value = '';
                elements.loginTab.click();
            }, 1000);
        } else {
            elements.registerMessage.textContent = data.error || 'Помилка реєстрації';
            elements.registerMessage.className = 'auth-message error';
        }
    } catch (error) {
        elements.registerMessage.textContent = 'Помилка з\'єднання';
        elements.registerMessage.className = 'auth-message error';
    } finally {
        elements.registerSubmitBtn.disabled = false;
    }
}

function handleLogout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    updateUserUI();
    
    // Clear chat
    elements.chatWindow.innerHTML = `
        <div class="message assistant">
            <p>Готово до роботи. Оберіть архетип та поставте запитання.</p>
        </div>
    `;
    currentChatId = null;
    currentArchetypeForChat = null;
}

// Helper function to add Authorization header to fetch requests
function getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }
    return headers;
}

// Функція для генерації нового chat_id та імені файлу історії
function generateChatId(archetype) {
    const now = new Date();
    const pad = n => n.toString().padStart(2, '0');
    const dateStr = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
    const uniq = Math.random().toString(36).slice(2, 8);
    const arch = archetype ? archetype.replace(/[^a-zA-Z0-9_]/g, '_') : 'any';
    return `${dateStr}_${uniq}_${arch}`;
}

document.addEventListener('DOMContentLoaded', () => {
    // Initialize auth UI
    updateUserUI();
    
    // Auth tab switching
    elements.loginTab.addEventListener('click', () => {
        elements.loginTab.classList.add('active');
        elements.registerTab.classList.remove('active');
        elements.loginForm.classList.remove('hidden');
        elements.registerForm.classList.add('hidden');
    });
    
    elements.registerTab.addEventListener('click', () => {
        elements.registerTab.classList.add('active');
        elements.loginTab.classList.remove('active');
        elements.registerForm.classList.remove('hidden');
        elements.loginForm.classList.add('hidden');
    });
    
    // Login form submit
    elements.loginSubmitBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const email = elements.loginEmail.value.trim();
        const password = elements.loginPassword.value;
        
        if (!email || !password) {
            elements.loginMessage.textContent = 'Заповніть всі поля';
            elements.loginMessage.className = 'auth-message error';
            return;
        }
        
        handleLogin(email, password);
    });
    
    // Register form submit
    elements.registerSubmitBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const username = elements.registerUsername.value.trim();
        const email = elements.registerEmail.value.trim();
        const password = elements.registerPassword.value;
        
        if (!username || !email || !password) {
            elements.registerMessage.textContent = 'Заповніть всі поля';
            elements.registerMessage.className = 'auth-message error';
            return;
        }
        
        if (password.length < 8) {
            elements.registerMessage.textContent = 'Пароль має бути не менше 8 символів';
            elements.registerMessage.className = 'auth-message error';
            return;
        }
        
        handleRegister(username, email, password);
    });
    
    // Logout button
    elements.logoutBtn.addEventListener('click', handleLogout);
    
    // --- Логіка кнопки "Новий чат" ---
    if (elements.newChatBtn) {
        elements.newChatBtn.addEventListener('click', () => {
            elements.chatWindow.innerHTML = `
                <div class="message assistant">
                    <p>Готово до роботи. Оберіть архетип та поставте запитання.</p>
                </div>
            `;
            elements.input.value = '';
            elements.input.focus();
            currentChatId = null;
            currentArchetypeForChat = null;
        });
    }
    
    // --- Скидання чату при зміні архетипа ---
    elements.archetypeSelect.addEventListener('change', () => {
        // Якщо змінили архетип, скидаємо поточний чат
        if (currentChatId) {
            currentChatId = null;
            currentArchetypeForChat = null;
        }
    });

    // --- Логіка чату ---
    elements.form.addEventListener('submit', handleFormSubmit);
    elements.input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleFormSubmit(e);
        }
        autoGrow(elements.input);
    });

    async function handleFormSubmit(e) {
        e.preventDefault();
        const userMessage = elements.input.value.trim();
        const selectedArchetype = elements.archetypeSelect.value;
        const rememberChat = elements.rememberChatToggle ? elements.rememberChatToggle.checked : true;

        if (!userMessage) {
            alert('Введіть повідомлення!');
            return;
        }
        
        if (!selectedArchetype) {
            alert('Оберіть архетип!');
            return;
        }

        addMessage(userMessage, 'user');
        elements.input.value = '';
        autoGrow(elements.input);

        const thinkingIndicator = addMessage('...', 'assistant thinking');

        try {
            let response, data;
            
            if (selectedArchetype === 'rada') {
                // Режим РАДА - сервер автоматично вибере всіх доступних агентів (до 3)
                // Генеруємо chat_id для РАДА
                if (!currentChatId) {
                    currentChatId = generateChatId('rada');
                }
                
                response = await fetch('/conference/rada', {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({ 
                        text: userMessage, 
                        archetypes: [], // Порожній масив - сервер вибере агентів автоматично
                        remember: rememberChat
                    })
                });
            } else {
                // Режим одного агента
                // Генеруємо chat_id тільки для першого повідомлення в чаті
                if (!currentChatId) {
                    currentArchetypeForChat = selectedArchetype;
                    currentChatId = generateChatId(selectedArchetype);
                }
                
                response = await fetch('/process', {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({ 
                        text: userMessage, 
                        archetype: selectedArchetype,
                        remember: rememberChat,
                        chat_id: currentChatId
                    })
                });
            }
            
            thinkingIndicator.remove();
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Server response was not ok.');
            }
            
            data = await response.json();
            
            if (selectedArchetype === 'rada') {
                // Відображення відповіді РАДА
                displayRadaResponse(data);
            } else {
                // Відображення відповіді одного агента
                if (data.response) {
                    const responseText = data.response;
                    // Add cache indicator if response was cached
                    const cacheIndicator = data.cached ? ' <span style="font-size: 0.8em; color: #4a9;" title="Відповідь з кешу">⚡</span>' : '';
                    addMessage(responseText + cacheIndicator, 'assistant', true);
                } else if (data.error) {
                    addMessage(`Помилка: ${data.error}`, 'assistant');
                }
            }
        } catch (error) {
            thinkingIndicator.remove();
            addMessage(`Помилка: ${error.message}`, 'assistant');
        }
    }
    
    function displayRadaResponse(data) {
        const radaContainer = document.createElement('div');
        radaContainer.className = 'message assistant rada-message';
        
        let html = '<div class="rada-section">';
        
        // Початкові відповіді
        if (data.initial && Object.keys(data.initial).length > 0) {
            html += '<h3 style="color: var(--accent-color); margin-top: 0;">Початкові думки:</h3>';
            for (const [agentName, response] of Object.entries(data.initial)) {
                html += `<div style="margin: 10px 0;"><div class="rada-agent-name">${agentName}:</div>`;
                html += `<div>${marked.parse(response)}</div></div>`;
            }
        }
        
        // Обговорення
        if (data.discussion && Object.keys(data.discussion).length > 0) {
            html += '<h3 style="color: var(--accent-color); margin-top: 20px;">Обговорення:</h3>';
            for (const [agentName, response] of Object.entries(data.discussion)) {
                html += `<div style="margin: 10px 0;"><div class="rada-agent-name">${agentName}:</div>`;
                html += `<div>${marked.parse(response)}</div></div>`;
            }
        }
        
        // Консенсус
        if (data.consensus) {
            html += '<h3 style="color: var(--accent-color); margin-top: 20px;">Консенсус Ради:</h3>';
            html += `<div style="padding: 10px; background-color: rgba(88, 166, 255, 0.15); border-radius: 6px; margin-top: 10px;">`;
            html += marked.parse(data.consensus);
            html += '</div>';
        }
        
        html += '</div>';
        radaContainer.innerHTML = html;
        
        // Додаємо кнопку копіювання
        const copyBtn = document.createElement('button');
        copyBtn.textContent = '📋';
        copyBtn.title = 'Копіювати відповідь';
        copyBtn.className = 'copy-btn';
        copyBtn.onclick = () => {
            const temp = document.createElement('div');
            temp.innerHTML = radaContainer.innerHTML;
            const plainText = temp.innerText;
            navigator.clipboard.writeText(plainText);
            copyBtn.textContent = '✅';
            setTimeout(() => { copyBtn.textContent = '📋'; }, 1200);
        };
        radaContainer.appendChild(copyBtn);
        
        elements.chatWindow.appendChild(radaContainer);
        elements.chatWindow.scrollTop = elements.chatWindow.scrollHeight;
    }
    
    function addMessage(text, type, isMarkdown = false) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message ' + type;
        const contentContainer = document.createElement('div');
        if (isMarkdown && typeof marked !== "undefined") {
            contentContainer.innerHTML = marked.parse(text);
        } else {
            contentContainer.innerHTML = text.replace(/\n/g, '<br>');
        }
        messageElement.appendChild(contentContainer);

        // --- Додаємо кнопку "Копіювати" для відповідей асистента ---
        if (type.startsWith('assistant')) {
            const copyBtn = document.createElement('button');
            copyBtn.textContent = '📋';
            copyBtn.title = 'Копіювати відповідь';
            copyBtn.className = 'copy-btn';
            copyBtn.onclick = () => {
                const temp = document.createElement('div');
                temp.innerHTML = contentContainer.innerHTML;
                const plainText = temp.innerText;
                navigator.clipboard.writeText(plainText);
                copyBtn.textContent = '✅';
                setTimeout(() => { copyBtn.textContent = '📋'; }, 1200);
            };
            messageElement.appendChild(copyBtn);
        }

        elements.chatWindow.appendChild(messageElement);
        elements.chatWindow.scrollTop = elements.chatWindow.scrollHeight;
        return messageElement;
    }

    function autoGrow(element) {
        element.style.height = "5px";
        element.style.height = (element.scrollHeight) + "px";
    }

    // --- Логіка історії ---
    elements.historyBtn.addEventListener('click', async () => {
        elements.historyModal.classList.remove('hidden');
        await loadHistoryList();
        await loadArchetypesForFilter();
    });
    
    // Load archetypes for filter
    async function loadArchetypesForFilter() {
        try {
            const response = await fetch('/api/archetypes');
            const data = await response.json();
            const filterSelect = document.getElementById('history-archetype-filter');
            if (filterSelect) {
                // Clear existing options except "All"
                filterSelect.innerHTML = `<option value="">${getTranslation('allArchetypes')}</option>`;
                // Add archetypes
                for (const [key, config] of Object.entries(data.archetypes || {})) {
                    const option = document.createElement('option');
                    option.value = key;
                    option.textContent = config.name || key;
                    filterSelect.appendChild(option);
                }
                // Add RADA option
                const radaOption = document.createElement('option');
                radaOption.value = 'rada';
                radaOption.textContent = 'РАДА';
                filterSelect.appendChild(radaOption);
            }
        } catch (error) {
            console.error('Error loading archetypes for filter:', error);
        }
    }
    
    // Load history list (with optional search)
    async function loadHistoryList(query = null, archetype = null) {
        elements.historyListContainer.innerHTML = `<ul><li>${getTranslation('loading')}</li></ul>`;
        
        try {
            let files = [];
            if (query || archetype) {
                // Use search endpoint
                const params = new URLSearchParams();
                if (query) params.append('query', query);
                if (archetype) params.append('archetype', archetype);
                const response = await fetch(`/api/history/search?${params}`);
                const data = await response.json();
                files = data.results.map(r => r.filename);
            } else {
                // Load all files
                const response = await fetch('/history');
                files = await response.json();
            }
            
            const ul = document.createElement('ul');
            if (files.length > 0) {
                files.forEach(file => {
                    const li = document.createElement('li');
                    const delBtn = document.createElement('span');
                    delBtn.textContent = '✖';
                    delBtn.title = getTranslation('delete');
                    delBtn.style.color = 'red';
                    delBtn.style.cursor = 'pointer';
                    delBtn.style.fontWeight = 'bold';
                    delBtn.style.fontSize = '14px';
                    delBtn.style.marginRight = '10px';
                    delBtn.style.verticalAlign = 'middle';
                    delBtn.onclick = async (e) => {
                        e.stopPropagation();
                        if (confirm(getTranslation('deleteChatConfirm'))) {
                            const resp = await fetch(`/history/${file}`, { method: 'DELETE' });
                            if (resp.ok) {
                                li.remove();
                                elements.historyViewContainer.innerHTML = `<pre><code>${getTranslation('selectChat')}</code></pre>`;
                                await loadHistoryList(query, archetype); // Reload list
                            } else {
                                alert(getTranslation('deleteFailed'));
                            }
                        }
                    };
                    li.appendChild(delBtn);
                    
                    // Export buttons
                    const exportJsonBtn = document.createElement('span');
                    exportJsonBtn.textContent = '📥 JSON';
                    exportJsonBtn.title = getTranslation('exportJson');
                    exportJsonBtn.style.color = '#58a6ff';
                    exportJsonBtn.style.cursor = 'pointer';
                    exportJsonBtn.style.marginRight = '10px';
                    exportJsonBtn.style.fontSize = '12px';
                    exportJsonBtn.onclick = async (e) => {
                        e.stopPropagation();
                        await exportHistoryFile(file, 'json');
                    };
                    li.appendChild(exportJsonBtn);
                    
                    const exportMdBtn = document.createElement('span');
                    exportMdBtn.textContent = '📄 MD';
                    exportMdBtn.title = getTranslation('exportMarkdown');
                    exportMdBtn.style.color = '#58a6ff';
                    exportMdBtn.style.cursor = 'pointer';
                    exportMdBtn.style.marginRight = '10px';
                    exportMdBtn.style.fontSize = '12px';
                    exportMdBtn.onclick = async (e) => {
                        e.stopPropagation();
                        await exportHistoryFile(file, 'markdown');
                    };
                    li.appendChild(exportMdBtn);
                    
                    const fileNameSpan = document.createElement('span');
                    fileNameSpan.textContent = file;
                    fileNameSpan.style.cursor = 'pointer';
                    li.appendChild(fileNameSpan);
                    li.addEventListener('click', () => viewHistoryFile(file));
                    ul.appendChild(li);
                });
            } else {
                 const li = document.createElement('li');
                 li.textContent = query || archetype ? getTranslation('nothingFound') : getTranslation('historyEmpty');
                 ul.appendChild(li);
            }
            elements.historyListContainer.innerHTML = '';
            elements.historyListContainer.appendChild(ul);
        } catch (error) {
            console.error('Error loading history:', error);
            elements.historyListContainer.innerHTML = `<ul><li>${getTranslation('historyLoadFailed')}</li></ul>`;
        }
    }
    
    // History search handlers
    const historySearchInput = document.getElementById('history-search-input');
    const historyArchetypeFilter = document.getElementById('history-archetype-filter');
    const historySearchBtn = document.getElementById('history-search-btn');
    const historyClearSearchBtn = document.getElementById('history-clear-search-btn');
    
    if (historySearchBtn) {
        historySearchBtn.addEventListener('click', async () => {
            const query = historySearchInput ? historySearchInput.value.trim() : null;
            const archetype = historyArchetypeFilter ? historyArchetypeFilter.value : null;
            await loadHistoryList(query || null, archetype || null);
        });
    }
    
    if (historyClearSearchBtn) {
        historyClearSearchBtn.addEventListener('click', async () => {
            if (historySearchInput) historySearchInput.value = '';
            if (historyArchetypeFilter) historyArchetypeFilter.value = '';
            await loadHistoryList();
        });
    }
    
    // Allow Enter key in search input
    if (historySearchInput) {
        historySearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                historySearchBtn.click();
            }
        });
    }
    
    async function viewHistoryFile(filename) {
        elements.historyViewContainer.textContent = getTranslation('loading');
        try {
            const response = await fetch(`/history/${filename}`);
            const data = await response.json();
            let html = '';
            
            // Перевіряємо, чи це РАДА-відповідь (об'єкт з полем type)
            if (data.type === 'rada') {
                html += `<b>Питання:</b><p>${data.user_input.replace(/\n/g, '<br>')}</p>`;
                // Використовуємо назви агентів, якщо доступні
                const agentNames = data.archetype_names 
                    ? Object.values(data.archetype_names).join(', ')
                    : (data.archetypes || []).join(', ');
                html += `<b>Агенти:</b> ${agentNames}<hr>`;
                
                // Початкові відповіді
                if (data.initial && Object.keys(data.initial).length > 0) {
                    html += '<b>Початкові думки:</b>';
                    for (const [agentName, response] of Object.entries(data.initial)) {
                        html += `<div style="margin: 10px 0;"><div class="rada-agent-name">${agentName}:</div>`;
                        html += `<div>${marked.parse(response)}</div></div>`;
                    }
                    html += '<hr>';
                }
                
                // Обговорення
                if (data.discussion && Object.keys(data.discussion).length > 0) {
                    html += '<b>Обговорення:</b>';
                    for (const [agentName, response] of Object.entries(data.discussion)) {
                        html += `<div style="margin: 10px 0;"><div class="rada-agent-name">${agentName}:</div>`;
                        html += `<div>${marked.parse(response)}</div></div>`;
                    }
                    html += '<hr>';
                }
                
                // Консенсус
                if (data.consensus) {
                    html += '<b>Консенсус Ради:</b>';
                    html += `<div style="padding: 10px; background-color: rgba(88, 166, 255, 0.15); border-radius: 6px; margin-top: 10px;">`;
                    html += marked.parse(data.consensus);
                    html += '</div>';
                }
            } else {
                // Звичайний формат (масив повідомлень)
                if (Array.isArray(data)) {
                    data.forEach(item => {
                        html += `<b>Користувач:</b>
                            <p>${item.user_input.replace(/\n/g, '<br>')}</p>
                            <b>Відповідь (${item.archetype}):</b>
                            ${marked.parse(item.model_response)}`;
                    });
                } else {
                    // Старий формат (об'єкт)
                    html += `<b>Користувач:</b>
                        <p>${data.user_input?.replace(/\n/g, '<br>') || ''}</p>
                        <b>Відповідь:</b>
                        ${marked.parse(data.model_response || data.response || '')}`;
                }
            }
            
            elements.historyViewContainer.innerHTML = html;
        } catch (error) {
            elements.historyViewContainer.textContent = `${getTranslation('fileLoadFailed')} ${filename}`;
        }
    }

    elements.closeModalBtn.addEventListener('click', () => elements.historyModal.classList.add('hidden'));
    elements.historyModal.addEventListener('click', (e) => {
        if (e.target === elements.historyModal) elements.historyModal.classList.add('hidden');
    });
    
    // --- Логіка налаштування агентів ---
    let archetypesConfig = {};
    
    elements.configBtn.addEventListener('click', async () => {
        // Закриваємо випадаюче меню
        if (elements.dropdownMenu) {
            elements.dropdownMenu.classList.add('hidden');
        }
        elements.configModal.classList.remove('hidden');
        elements.configLoading.classList.remove('hidden');
        elements.configFormWrapper.classList.add('hidden');
        elements.configMessage.className = 'config-message';
        elements.configMessage.textContent = '';
        
        try {
            const response = await fetch('/api/archetypes');
            const data = await response.json();
            archetypesConfig = data.archetypes || {};
            renderArchetypesForm();
        } catch (error) {
            elements.configLoading.textContent = `${getTranslation('loadError')} ${error.message}`;
        }
    });
    
    elements.configCloseBtn.addEventListener('click', () => {
        elements.configModal.classList.add('hidden');
    });
    
    elements.configModal.addEventListener('click', (e) => {
        if (e.target === elements.configModal) {
            elements.configModal.classList.add('hidden');
        }
    });
    
    elements.addArchetypeBtn.addEventListener('click', () => {
        const newKey = `agent_${Date.now()}`;
        archetypesConfig[newKey] = {
            name: getTranslation('newAgent'),
            description: '',
            model_name: 'gemini-2.5-flash',
            role: 'creative_generator',
            prompt: ''  // For new archetypes, prompt will be saved to file
        };
        renderArchetypesForm();
        // Прокручуємо до нового агента
        setTimeout(() => {
            const newCard = document.querySelector(`[data-archetype-key="${newKey}"]`);
            if (newCard) {
                newCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                const nameInput = newCard.querySelector('input[name="name"]');
                if (nameInput) nameInput.focus();
            }
        }, 100);
    });
    
    elements.saveConfigBtn.addEventListener('click', async () => {
        // Збираємо дані з форми
        let configData;
        try {
            configData = collectArchetypesData();
        } catch (error) {
            showConfigMessage(error.message, 'error');
            return;
        }
        
        // Валідація
        const errors = validateArchetypesConfig(configData);
        if (errors.length > 0) {
            showConfigMessage(errors.join('<br>'), 'error');
            return;
        }
        
        try {
            elements.saveConfigBtn.disabled = true;
            elements.saveConfigBtn.textContent = getTranslation('saving');
            
            const response = await fetch('/api/archetypes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ archetypes: configData })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || getTranslation('saveError'));
            }
            
            const result = await response.json();
            showConfigMessage(result.message || getTranslation('configSaved'), 'success');
            archetypesConfig = configData;
            
            // Перезавантажуємо сторінку через 1.5 секунди
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } catch (error) {
            showConfigMessage(`${getTranslation('saveError')}: ${error.message}`, 'error');
        } finally {
            elements.saveConfigBtn.disabled = false;
            elements.saveConfigBtn.textContent = getTranslation('saveConfig');
        }
    });
    
    function renderArchetypesForm() {
        elements.archetypesList.innerHTML = '';
        
        for (const [key, config] of Object.entries(archetypesConfig)) {
            const card = createArchetypeCard(key, config);
            elements.archetypesList.appendChild(card);
        }
        
        elements.configLoading.classList.add('hidden');
        elements.configFormWrapper.classList.remove('hidden');
    }
    
    function createArchetypeCard(key, config) {
        const card = document.createElement('div');
        card.className = 'archetype-card';
        card.setAttribute('data-archetype-key', key);
        
        const header = document.createElement('div');
        header.className = 'archetype-card-header';
        
        const title = document.createElement('h3');
        title.className = 'archetype-card-title';
        title.textContent = config.name || key;
        title.id = `title_${key}`;
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'archetype-delete-btn';
        deleteBtn.textContent = getTranslation('deleteAgent');
        deleteBtn.onclick = () => {
            if (confirm(getTranslation('deleteAgentConfirm').replace('{name}', config.name || key))) {
                delete archetypesConfig[key];
                renderArchetypesForm();
            }
        };
        
        header.appendChild(title);
        header.appendChild(deleteBtn);
        
        const form = document.createElement('div');
        form.className = 'archetype-form';
        
        // Ключ агента
        const keyGroup = createFormGroup(getTranslation('agentKey'), 'text', `key_${key}`, key, false, getTranslation('agentKeyHelp'));
        const keyInput = keyGroup.querySelector('input');
        keyInput.addEventListener('blur', () => {
            const newKey = keyInput.value.trim();
            if (newKey && newKey !== key && !/^[a-z0-9_]+$/i.test(newKey)) {
                keyInput.value = key;
                    alert(getTranslation('agentKeyError'));
            }
        });
        form.appendChild(keyGroup);
        
        // Назва
        const nameGroup = createFormGroup(getTranslation('agentName'), 'text', `name_${key}`, config.name || '', false, getTranslation('agentNameHelp'));
        const nameInput = nameGroup.querySelector('input');
        nameInput.addEventListener('input', () => {
            title.textContent = nameInput.value || key;
        });
        form.appendChild(nameGroup);
        
        // Опис
        form.appendChild(createFormGroup(getTranslation('agentDescription'), 'text', `description_${key}`, config.description || '', false, getTranslation('agentDescriptionHelp')));
        
        // Модель
        const modelSelect = createFormGroup(getTranslation('agentModel'), 'select', `model_${key}`, config.model_name || 'gemini-2.5-flash', false, getTranslation('agentModelHelp'));
        const modelSelectElement = modelSelect.querySelector('select');
        modelSelectElement.innerHTML = `
            <option value="gemini-2.5-flash">gemini-2.5-flash</option>
            <option value="gemini-1.5-pro">gemini-1.5-pro</option>
            <option value="gemini-1.5-flash">gemini-1.5-flash</option>
        `;
        modelSelectElement.value = config.model_name || 'gemini-2.5-flash';
        form.appendChild(modelSelect);
        
        // Роль
        const roleSelect = createFormGroup(getTranslation('agentRole'), 'select', `role_${key}`, config.role || 'creative_generator', false, getTranslation('agentRoleHelp'));
        const roleSelectElement = roleSelect.querySelector('select');
        roleSelectElement.innerHTML = `
            <option value="creative_generator">${getTranslation('roleCreative')}</option>
            <option value="critic">${getTranslation('roleCritic')}</option>
            <option value="executor">${getTranslation('roleExecutor')}</option>
        `;
        roleSelectElement.value = config.role || 'creative_generator';
        form.appendChild(roleSelect);
        
        // Model parameters
        const paramsGroup = document.createElement('div');
        paramsGroup.className = 'archetype-form-group';
        paramsGroup.style.borderTop = '1px solid var(--border-color)';
        paramsGroup.style.paddingTop = '15px';
        paramsGroup.style.marginTop = '15px';
        
        const paramsLabel = document.createElement('label');
        paramsLabel.textContent = getTranslation('modelParams');
        paramsLabel.style.fontWeight = 'bold';
        paramsGroup.appendChild(paramsLabel);
        
        const paramsHelp = document.createElement('small');
        paramsHelp.textContent = getTranslation('modelParamsHelp');
        paramsHelp.style.display = 'block';
        paramsHelp.style.marginBottom = '10px';
        paramsGroup.appendChild(paramsHelp);
        
        // Temperature
        const tempGroup = createFormGroup(getTranslation('temperature'), 'number', `temperature_${key}`, config.temperature || '', false, getTranslation('temperatureHelp'));
        const tempInput = tempGroup.querySelector('input');
        tempInput.min = '0';
        tempInput.max = '2';
        tempInput.step = '0.1';
        tempInput.placeholder = '0.7';
        paramsGroup.appendChild(tempGroup);
        
        // Max tokens
        const maxTokensGroup = createFormGroup(getTranslation('maxTokens'), 'number', `max_tokens_${key}`, config.max_tokens || '', false, getTranslation('maxTokensHelp'));
        const maxTokensInput = maxTokensGroup.querySelector('input');
        maxTokensInput.min = '1';
        maxTokensInput.max = '8192';
        maxTokensInput.step = '1';
        maxTokensInput.placeholder = '2000';
        paramsGroup.appendChild(maxTokensGroup);
        
        // Top P
        const topPGroup = createFormGroup(getTranslation('topP'), 'number', `top_p_${key}`, config.top_p || '', false, getTranslation('topPHelp'));
        const topPInput = topPGroup.querySelector('input');
        topPInput.min = '0';
        topPInput.max = '1';
        topPInput.step = '0.01';
        topPInput.placeholder = getTranslation('notSet');
        paramsGroup.appendChild(topPGroup);
        
        // Top K
        const topKGroup = createFormGroup(getTranslation('topK'), 'number', `top_k_${key}`, config.top_k || '', false, getTranslation('topKHelp'));
        const topKInput = topKGroup.querySelector('input');
        topKInput.min = '1';
        topKInput.max = '100';
        topKInput.step = '1';
        topKInput.placeholder = getTranslation('notSet');
        paramsGroup.appendChild(topKGroup);
        
        form.appendChild(paramsGroup);
        
        // Промпт - вибір типу
        const promptTypeGroup = document.createElement('div');
        promptTypeGroup.className = 'archetype-form-group';
        
        const promptTypeLabel = document.createElement('label');
        promptTypeLabel.textContent = getTranslation('promptType');
        promptTypeGroup.appendChild(promptTypeLabel);
        
        const promptTypeSelector = document.createElement('div');
        promptTypeSelector.className = 'prompt-type-selector';
        
        // Show file path if exists (editable for existing, will be auto-generated for new)
        const promptFileGroup = createFormGroup(getTranslation('promptFile'), 'text', `prompt_file_${key}`, config.prompt_file || '', false, getTranslation('promptFileHelp'));
        form.appendChild(promptFileGroup);
        
        // Show prompt content for editing (from file or empty for new)
        const promptContent = config._prompt_content || config.prompt || '';
        const promptTextArea = createFormGroup(getTranslation('promptContent'), 'textarea', `prompt_content_${key}`, promptContent, false, getTranslation('promptContentHelp'));
        promptTextArea.querySelector('textarea').style.minHeight = '200px';
        promptTextArea.querySelector('textarea').required = true;
        form.appendChild(promptTextArea);
        
        // Додаткові промпти
        const additionalPromptsGroup = document.createElement('div');
        additionalPromptsGroup.className = 'archetype-form-group';
        
        const additionalPromptsLabel = document.createElement('label');
        additionalPromptsLabel.textContent = getTranslation('additionalPrompts');
        additionalPromptsGroup.appendChild(additionalPromptsLabel);
        
        const additionalPromptsList = document.createElement('div');
        additionalPromptsList.className = 'additional-prompts-list';
        additionalPromptsList.id = `additional_prompts_${key}`;
        
        // Використовуємо вміст файлів для редагування, якщо доступний
        const additionalPrompts = config.additional_prompts || [];
        const additionalContents = config._additional_prompts_content || [];
        
        // Якщо є вміст для редагування, використовуємо його, інакше використовуємо шляхи до файлів
        const promptsToShow = additionalContents.length > 0 ? additionalContents : additionalPrompts;
        
        promptsToShow.forEach((prompt, index) => {
            additionalPromptsList.appendChild(createPromptItem(key, index, prompt));
        });
        
        const addPromptBtn = document.createElement('button');
        addPromptBtn.type = 'button';
        addPromptBtn.className = 'add-prompt-btn';
        addPromptBtn.textContent = getTranslation('addPrompt');
        addPromptBtn.onclick = () => {
            const index = additionalPromptsList.children.length;
            additionalPromptsList.appendChild(createPromptItem(key, index, ''));
        };
        
        additionalPromptsGroup.appendChild(additionalPromptsList);
        additionalPromptsGroup.appendChild(addPromptBtn);
        additionalPromptsGroup.appendChild(document.createElement('small')).textContent = getTranslation('additionalPromptsHelp');
        form.appendChild(additionalPromptsGroup);
        
        card.appendChild(header);
        card.appendChild(form);
        
        return card;
    }
    
    function createFormGroup(labelText, type, name, value, readonly = false, helpText = '') {
        const group = document.createElement('div');
        group.className = 'archetype-form-group';
        
        const label = document.createElement('label');
        label.textContent = labelText;
        label.setAttribute('for', name);
        group.appendChild(label);
        
        let input;
        if (type === 'textarea') {
            input = document.createElement('textarea');
            input.rows = 5;
        } else if (type === 'select') {
            input = document.createElement('select');
        } else {
            input = document.createElement('input');
            input.type = type;
        }
        
        input.name = name;
        input.id = name;
        if (type !== 'select') {
            input.value = value || '';
        }
        if (readonly) {
            input.readOnly = true;
            input.style.backgroundColor = 'var(--user-message-bg)';
            input.style.cursor = 'not-allowed';
        }
        group.appendChild(input);
        
        if (helpText) {
            const small = document.createElement('small');
            small.textContent = helpText;
            group.appendChild(small);
        }
        
        return group;
    }
    
    function createRadioOption(name, value, label, checked = false) {
        const labelEl = document.createElement('label');
        const input = document.createElement('input');
        input.type = 'radio';
        input.name = name;
        input.value = value;
        input.checked = checked;
        labelEl.appendChild(input);
        labelEl.appendChild(document.createTextNode(label));
        return labelEl;
    }
    
    function createPromptItem(key, index, value) {
        const item = document.createElement('div');
        item.className = 'prompt-item';
        
        const input = document.createElement('input');
        input.type = 'text';
        input.name = `additional_prompt_${key}_${index}`;
        input.value = value;
        input.placeholder = 'Шлях до файлу або текст';
        item.appendChild(input);
        
        const deleteBtn = document.createElement('button');
        deleteBtn.type = 'button';
        deleteBtn.textContent = 'Видалити';
        deleteBtn.onclick = () => item.remove();
        item.appendChild(deleteBtn);
        
        return item;
    }
    
    function collectArchetypesData() {
        const data = {};
        const keys = new Set();
        
        // Знаходимо всі картки агентів
        const cards = document.querySelectorAll('.archetype-card');
        
        // Спочатку збираємо всі ключі для перевірки на унікальність
        cards.forEach(card => {
            const key = card.getAttribute('data-archetype-key');
            const newKey = document.getElementById(`key_${key}`).value.trim();
            if (newKey) {
                if (keys.has(newKey)) {
                    throw new Error(`Ключ "${newKey}" використовується кілька разів. Ключі мають бути унікальними.`);
                }
                keys.add(newKey);
            }
        });
        
        // Тепер збираємо дані
        cards.forEach(card => {
            const key = card.getAttribute('data-archetype-key');
            const newKey = document.getElementById(`key_${key}`).value.trim();
            
            if (!newKey) return; // Пропускаємо якщо ключ порожній
            
            const config = {
                name: document.getElementById(`name_${key}`).value.trim(),
                description: document.getElementById(`description_${key}`).value.trim(),
                model_name: document.getElementById(`model_${key}`).value.trim(),
                role: document.getElementById(`role_${key}`).value.trim()
            };
            
            // Model parameters - add only if provided
            const tempInput = document.getElementById(`temperature_${key}`);
            if (tempInput && tempInput.value.trim()) {
                const tempValue = parseFloat(tempInput.value.trim());
                if (!isNaN(tempValue)) {
                    config.temperature = tempValue;
                }
            }
            
            const maxTokensInput = document.getElementById(`max_tokens_${key}`);
            if (maxTokensInput && maxTokensInput.value.trim()) {
                const maxTokensValue = parseInt(maxTokensInput.value.trim());
                if (!isNaN(maxTokensValue)) {
                    config.max_tokens = maxTokensValue;
                }
            }
            
            const topPInput = document.getElementById(`top_p_${key}`);
            if (topPInput && topPInput.value.trim()) {
                const topPValue = parseFloat(topPInput.value.trim());
                if (!isNaN(topPValue)) {
                    config.top_p = topPValue;
                }
            }
            
            const topKInput = document.getElementById(`top_k_${key}`);
            if (topKInput && topKInput.value.trim()) {
                const topKValue = parseInt(topKInput.value.trim());
                if (!isNaN(topKValue)) {
                    config.top_k = topKValue;
                }
            }
            
            // Промпт - завжди зберігаємо як файл
            // Якщо є prompt_file, використовуємо його, инакше створюємо новий
            const promptFileInput = document.getElementById(`prompt_file_${key}`);
            const promptContentInput = document.getElementById(`prompt_content_${key}`);
            
            if (promptContentInput) {
                const promptContent = promptContentInput.value.trim();
                if (promptContent) {
                    // Завжди зберігаємо вміст у поле prompt для обробки на сервері
                    // Сервер автоматично створить/оновить файл
                    config.prompt = promptContent;
                    
                    // Якщо є prompt_file, використовуємо його, інакше сервер створить новий
                    if (promptFileInput) {
                        const promptFile = promptFileInput.value.trim();
                        if (promptFile) {
                            config.prompt_file = promptFile;
                        }
                    }
                }
            }
            
            // Додаткові промпти
            // Використовуємо оригінальні шляхи до файлів, але зберігаємо вміст для оновлення
            const originalAdditional = config.additional_prompts || [];
            const originalContents = config._additional_prompts_content || [];
            const additionalPrompts = [];
            
            const promptItems = document.querySelectorAll(`#additional_prompts_${key} .prompt-item input`);
            promptItems.forEach((input, idx) => {
                const value = input.value.trim();
                if (value) {
                    // Якщо є оригінальний файл на цій позиції, використовуємо його шлях
                    // Інакше сервер створить новий файл
                    if (idx < originalAdditional.length && typeof originalAdditional[idx] === 'string' && 
                        (originalAdditional[idx].endsWith('.txt') || originalAdditional[idx].endsWith('.md'))) {
                        // Це файл - зберігаємо вміст для оновлення файлу
                        additionalPrompts.push(value);
                    } else {
                        // Новий промпт - зберігаємо як текст, сервер створить файл
                        additionalPrompts.push(value);
                    }
                }
            });
            
            if (additionalPrompts.length > 0) {
                // Зберігаємо вміст, сервер визначить файли на основі оригінальних шляхів
                config.additional_prompts = additionalPrompts;
                // Зберігаємо оригінальні шляхи для сервера
                if (originalAdditional.length > 0) {
                    config._original_additional_file_paths = originalAdditional;
                }
            }
            
            data[newKey] = config;
        });
        
        return data;
    }
    
    function validateArchetypesConfig(config) {
        const errors = [];
        
        if (Object.keys(config).length === 0) {
            errors.push('Потрібно мати хоча б одного агента');
        }
        
        for (const [key, agentConfig] of Object.entries(config)) {
            if (!/^[a-z0-9_]+$/i.test(key)) {
                errors.push(`Ключ агента "${key}" може містити тільки латинські літери, цифри та підкреслення`);
            }
            
            if (!agentConfig.name || !agentConfig.name.trim()) {
                errors.push(`Агент "${key}" повинен мати назву`);
            }
            
            if (!agentConfig.model_name || !agentConfig.model_name.trim()) {
                errors.push(`Агент "${key}" повинен мати модель`);
            }
            
            if (!agentConfig.prompt && !agentConfig.prompt_file) {
                errors.push(`Агент "${key}" повинен мати або промпт, або файл з промптом`);
            }
        }
        
        return errors;
    }
    
    function showConfigMessage(message, type) {
        elements.configMessage.textContent = '';
        elements.configMessage.innerHTML = message;
        elements.configMessage.className = `config-message ${type}`;
        elements.configMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    // --- AI Provider Modal ---
    if (elements.aiProviderBtn) {
        elements.aiProviderBtn.addEventListener('click', async () => {
            // Закриваємо випадаюче меню
            if (elements.dropdownMenu) {
                elements.dropdownMenu.classList.add('hidden');
            }
            elements.aiProviderModal.classList.remove('hidden');
            elements.aiProviderLoading.classList.remove('hidden');
            elements.aiProviderFormWrapper.classList.add('hidden');
            
            try {
                const response = await fetch('/api/ai-provider');
                const data = await response.json();
                
                elements.aiProviderSelect.value = data.provider || 'google_ai';
                elements.openaiBaseUrl.value = data.openai_base_url || 'https://api.openai.com/v1';
                
                // Заповнюємо поля ключів, якщо вони вже налаштовані
                if (data.has_google_key) {
                    elements.googleApiKey.value = '••••••••••••••••';
                    elements.googleApiKey.placeholder = 'Ключ вже налаштований (залиште порожнім, щоб не змінювати)';
                    elements.googleApiKey.style.color = '#4a9';
                } else {
                    elements.googleApiKey.value = '';
                    elements.googleApiKey.placeholder = 'Введіть Google API ключ';
                    elements.googleApiKey.style.color = '';
                }
                
                if (data.has_openai_key) {
                    elements.openaiApiKey.value = '••••••••••••••••';
                    elements.openaiApiKey.placeholder = 'Ключ вже налаштований (залиште порожнім, щоб не змінювати)';
                    elements.openaiApiKey.style.color = '#4a9';
                } else {
                    elements.openaiApiKey.value = '';
                    elements.openaiApiKey.placeholder = 'Введіть OpenAI API ключ';
                    elements.openaiApiKey.style.color = '';
                }
                
                elements.aiProviderLoading.classList.add('hidden');
                elements.aiProviderFormWrapper.classList.remove('hidden');
                
                // Завантажуємо моделі для поточного провайдера (з перекладом)
                await loadModelsForProvider(data.provider || 'google_ai');
            } catch (error) {
                console.error('Помилка завантаження конфігурації AI провайдера:', error);
                elements.aiProviderLoading.textContent = 'Помилка завантаження';
            }
        });
    }
    
    // Функція для завантаження моделей для вибраного провайдера
    async function loadModelsForProvider(provider) {
        try {
            // Отримуємо поточну мову
            const currentLang = localStorage.getItem('language') || 'uk';
            const translations = {
                uk: {
                    availableModels: 'Доступні моделі:',
                    modelsLoading: 'Моделі завантажуються...',
                    modelsError: 'Помилка завантаження моделей'
                },
                en: {
                    availableModels: 'Available Models:',
                    modelsLoading: 'Loading models...',
                    modelsError: 'Error loading models'
                }
            };
            const t = translations[currentLang] || translations.uk;
            
            // Отримуємо список моделей з API
            const response = await fetch('/api/ai-provider');
            const data = await response.json();
            
            // Отримуємо моделі для вибраного провайдера
            let modelsList = [];
            if (data.supported_models) {
                // supported_models - це об'єкт, де ключ - це провайдер, значення - масив моделей
                // Наприклад: { "google_ai": [...], "openai": [...] }
                if (provider === 'google_ai') {
                    modelsList = data.supported_models.google_ai || data.supported_models['google_ai'] || [];
                } else if (provider === 'openai') {
                    modelsList = data.supported_models.openai || data.supported_models['openai'] || [];
                }
                
                // Якщо не знайдено, спробуємо отримати перший масив
                if (modelsList.length === 0 && Object.keys(data.supported_models).length > 0) {
                    const firstKey = Object.keys(data.supported_models)[0];
                    modelsList = data.supported_models[firstKey] || [];
                }
            }
            
            // Оновлюємо відображення моделей
            if (modelsList && modelsList.length > 0) {
                elements.aiProviderModels.innerHTML = `
                    <div class="archetype-form-group">
                        <label>${t.availableModels}</label>
                        <div style="margin-top: 5px; color: var(--text-color); font-size: 0.9em;">
                            ${modelsList.map(m => `<span style="display: inline-block; margin: 2px 5px; padding: 2px 8px; background: var(--assistant-message-bg); border-radius: 3px; border: 1px solid var(--border-color);">${m}</span>`).join('')}
                        </div>
                    </div>
                `;
            } else {
                elements.aiProviderModels.innerHTML = `
                    <div class="archetype-form-group">
                        <label>${t.availableModels}</label>
                        <div style="margin-top: 5px; color: var(--text-color); font-size: 0.9em; font-style: italic;">
                            ${t.modelsLoading}
                        </div>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Помилка завантаження моделей:', error);
            const currentLang = localStorage.getItem('language') || 'uk';
            const translations = {
                uk: {
                    availableModels: 'Доступні моделі:',
                    modelsError: 'Помилка завантаження моделей'
                },
                en: {
                    availableModels: 'Available Models:',
                    modelsError: 'Error loading models'
                }
            };
            const t = translations[currentLang] || translations.uk;
            elements.aiProviderModels.innerHTML = `
                <div class="archetype-form-group">
                    <label>${t.availableModels}</label>
                    <div style="margin-top: 5px; color: #ff4444; font-size: 0.9em;">
                        ${t.modelsError}
                    </div>
                </div>
            `;
        }
    }
    
    // Обробник зміни провайдера
    if (elements.aiProviderSelect) {
        elements.aiProviderSelect.addEventListener('change', async (e) => {
            const selectedProvider = e.target.value;
            await loadModelsForProvider(selectedProvider);
        });
    }
    
    // Обробники для очищення поля при введенні нового ключа
    if (elements.googleApiKey) {
        elements.googleApiKey.addEventListener('focus', (e) => {
            if (e.target.value === '••••••••••••••••') {
                e.target.value = '';
                e.target.placeholder = 'Введіть Google API ключ';
                e.target.style.color = '';
            }
        });
    }
    
    if (elements.openaiApiKey) {
        elements.openaiApiKey.addEventListener('focus', (e) => {
            if (e.target.value === '••••••••••••••••') {
                e.target.value = '';
                e.target.placeholder = 'Введіть OpenAI API ключ';
                e.target.style.color = '';
            }
        });
    }
    
    if (elements.aiProviderCloseBtn) {
        elements.aiProviderCloseBtn.addEventListener('click', () => {
            elements.aiProviderModal.classList.add('hidden');
        });
    }
    
    if (elements.saveAiProviderBtn) {
        elements.saveAiProviderBtn.addEventListener('click', async () => {
            const provider = elements.aiProviderSelect.value;
            let googleApiKey = elements.googleApiKey.value.trim();
            let openaiApiKey = elements.openaiApiKey.value.trim();
            const openaiBaseUrl = elements.openaiBaseUrl.value.trim();
            
            // Якщо ключ містить тільки символи ••••, це означає, що ключ вже налаштований
            // і користувач не хоче його змінювати - не відправляємо його
            if (googleApiKey === '••••••••••••••••' || googleApiKey === '') {
                googleApiKey = null; // Не змінюємо існуючий ключ
            }
            if (openaiApiKey === '••••••••••••••••' || openaiApiKey === '') {
                openaiApiKey = null; // Не змінюємо існуючий ключ
            }
            
            // Перевіряємо, чи є хоча б один ключ для вибраного провайдера
            // Але спочатку перевіримо, чи ключі вже налаштовані
            try {
                const checkResponse = await fetch('/api/ai-provider');
                const checkData = await checkResponse.json();
                
                const hasGoogleKey = checkData.has_google_key;
                const hasOpenaiKey = checkData.has_openai_key;
                
                // Якщо провайдер Google AI і немає ключа (ні нового, ні старого)
                if (provider === 'google_ai' && !googleApiKey && !hasGoogleKey) {
                    showAiProviderMessage('Введіть Google API ключ', 'error');
                    return;
                }
                
                // Якщо провайдер OpenAI і немає ключа (ні нового, ні старого)
                if (provider === 'openai' && !openaiApiKey && !hasOpenaiKey) {
                    showAiProviderMessage('Введіть OpenAI API ключ', 'error');
                    return;
                }
            } catch (error) {
                console.error('Помилка перевірки ключів:', error);
                // Продовжуємо з перевіркою наявності хоча б одного ключа
                if (!googleApiKey && !openaiApiKey) {
                    showAiProviderMessage('Введіть хоча б один API ключ', 'error');
                    return;
                }
            }
            
            try {
                const response = await fetch('/api/ai-provider', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        provider: provider,
                        google_api_key: googleApiKey || undefined,
                        openai_api_key: openaiApiKey || undefined,
                        openai_base_url: openaiBaseUrl || undefined,
                    })
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    showAiProviderMessage(data.message, 'success');
                    setTimeout(() => {
                        elements.aiProviderModal.classList.add('hidden');
                        location.reload(); // Перезавантажуємо сторінку для застосування змін
                    }, 1500);
                } else {
                    showAiProviderMessage(data.detail || 'Помилка збереження', 'error');
                }
            } catch (error) {
                console.error('Помилка збереження конфігурації AI провайдера:', error);
                showAiProviderMessage('Помилка збереження: ' + error.message, 'error');
            }
        });
    }
    
    function showAiProviderMessage(message, type) {
        elements.aiProviderMessage.textContent = '';
        elements.aiProviderMessage.innerHTML = message;
        elements.aiProviderMessage.className = `config-message ${type}`;
        elements.aiProviderMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    
    // --- Vector DB Modal ---
    if (elements.vectorDbBtn) {
        elements.vectorDbBtn.addEventListener('click', async () => {
            // Закриваємо випадаюче меню
            if (elements.dropdownMenu) {
                elements.dropdownMenu.classList.add('hidden');
            }
            elements.vectorDbModal.classList.remove('hidden');
            elements.vectorDbLoading.classList.remove('hidden');
            elements.vectorDbWrapper.classList.add('hidden');
            
            await loadVectorDbEntries();
        });
    }
    
    if (elements.vectorDbCloseBtn) {
        elements.vectorDbCloseBtn.addEventListener('click', () => {
            elements.vectorDbModal.classList.add('hidden');
        });
    }
    
    // Vector DB search handlers
    const vectorDbSearchInput = document.getElementById('vector-db-search-input');
    const vectorDbSearchNResults = document.getElementById('vector-db-search-n-results');
    const vectorDbSearchBtn = document.getElementById('vector-db-search-btn');
    const vectorDbClearSearchBtn = document.getElementById('vector-db-clear-search-btn');
    
    if (vectorDbSearchBtn) {
        vectorDbSearchBtn.addEventListener('click', async () => {
            const query = vectorDbSearchInput ? vectorDbSearchInput.value.trim() : null;
            const nResults = vectorDbSearchNResults ? parseInt(vectorDbSearchNResults.value) || 5 : 5;
            if (query) {
                await loadVectorDbEntries(query, nResults);
            } else {
                await loadVectorDbEntries();
            }
        });
    }
    
    if (vectorDbClearSearchBtn) {
        vectorDbClearSearchBtn.addEventListener('click', async () => {
            if (vectorDbSearchInput) vectorDbSearchInput.value = '';
            if (vectorDbSearchNResults) vectorDbSearchNResults.value = '5';
            await loadVectorDbEntries();
        });
    }
    
    // Allow Enter key in search input
    if (vectorDbSearchInput) {
        vectorDbSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                vectorDbSearchBtn.click();
            }
        });
    }
    
    async function loadVectorDbEntries(query = null, nResults = 5) {
        try {
            let data;
            if (query) {
                // Use search endpoint
                const params = new URLSearchParams();
                params.append('query', query);
                params.append('n_results', nResults.toString());
                const response = await fetch(`/api/vector-db/search?${params}`, {
                    headers: getAuthHeaders()
                });
                data = await response.json();
                // Convert search results to entries format
                data.entries = data.results.map(result => ({
                    id: result.chat_id,
                    metadata: {
                        archetypes: result.archetypes,
                        timestamp: result.timestamp,
                        topic: result.topic
                    },
                    document: result.text,
                    preview: result.text.substring(0, 200) + (result.text.length > 200 ? '...' : ''),
                    relevance: result.relevance !== undefined ? result.relevance : (1 - (result.score || 0))
                }));
            } else {
                // Load all entries
                const response = await fetch('/api/vector-db', {
                    headers: getAuthHeaders()
                });
                data = await response.json();
            }
            
            elements.vectorDbEntriesList.innerHTML = '';

            // Deduplicate entries by ID to avoid accidental duplicates
            if (data && Array.isArray(data.entries)) {
                const uniqueMap = new Map();
                data.entries.forEach(e => {
                    if (e && e.id && !uniqueMap.has(e.id)) {
                        uniqueMap.set(e.id, e);
                    }
                });
                data.entries = Array.from(uniqueMap.values());
            }
            
            if (data.entries && data.entries.length > 0) {
                data.entries.forEach(entry => {
                    const item = document.createElement('div');
                    item.className = 'vector-db-entry-item';
                    
                    // Add relevance indicator if available (from search)
                    const relevanceBadge = entry.relevance !== undefined 
                        ? `<span style="background: #4a9; color: white; padding: 2px 6px; border-radius: 3px; font-size: 0.85em; margin-left: 10px;">Релевантність: ${(entry.relevance * 100).toFixed(1)}%</span>`
                        : '';
                    
                    item.innerHTML = `
                        <div class="vector-db-entry-header">
                            <strong>${entry.id}</strong>${relevanceBadge}
                            <div class="vector-db-entry-actions">
                                <button class="vector-db-view-btn" data-id="${entry.id}">${getTranslation('view')}</button>
                                <button class="vector-db-edit-btn" data-id="${entry.id}">${getTranslation('edit')}</button>
                                <button class="vector-db-delete-btn" data-id="${entry.id}">${getTranslation('delete')}</button>
                            </div>
                        </div>
                        <div class="vector-db-entry-preview">${entry.preview}</div>
                        <div class="vector-db-entry-meta">
                            ${getTranslation('archetypes')} ${entry.metadata.archetypes || 'N/A'} | 
                            Timestamp: ${entry.metadata.timestamp || 'N/A'}
                        </div>
                    `;
                    
                    // Обробники подій
                    item.querySelector('.vector-db-view-btn').addEventListener('click', () => viewVectorDbEntry(entry.id));
                    item.querySelector('.vector-db-edit-btn').addEventListener('click', () => editVectorDbEntry(entry.id));
                    item.querySelector('.vector-db-delete-btn').addEventListener('click', () => deleteVectorDbEntry(entry.id));
                    
                    elements.vectorDbEntriesList.appendChild(item);
                });
            } else {
                const message = query 
                    ? getTranslation('nothingFoundQuery')
                    : getTranslation('vectorDbEmpty');
                elements.vectorDbEntriesList.innerHTML = `<div style="padding: 20px; text-align: center; color: #666;">${message}</div>`;
            }
            
            elements.vectorDbLoading.classList.add('hidden');
            elements.vectorDbWrapper.classList.remove('hidden');
        } catch (error) {
            console.error('Помилка завантаження векторної бази:', error);
            elements.vectorDbLoading.textContent = 'Помилка завантаження: ' + error.message;
        }
    }
    
    async function viewVectorDbEntry(chatId) {
        try {
            const response = await fetch(`/api/vector-db/${chatId}`, {
                headers: getAuthHeaders()
            });
            const data = await response.json();
            
            elements.vectorDbEntryView.innerHTML = `
                <div class="vector-db-entry-full">
                    <h3>ID: ${data.id}</h3>
                    <div class="vector-db-entry-meta-full">
                        <strong>${getTranslation('metadataLabel')}</strong>
                        <pre>${JSON.stringify(data.metadata, null, 2)}</pre>
                    </div>
                    <div class="vector-db-entry-document-full">
                        <strong>${getTranslation('document')}</strong>
                        <pre>${data.document}</pre>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Помилка перегляду запису:', error);
            elements.vectorDbEntryView.innerHTML = `<pre><code>${getTranslation('loadEntryError')}</code></pre>`;
        }
    }
    
    async function editVectorDbEntry(chatId) {
        try {
            const response = await fetch(`/api/vector-db/${chatId}`, {
                headers: getAuthHeaders()
            });
            const data = await response.json();
            
            elements.vectorDbEntryView.innerHTML = `
                <div class="vector-db-entry-edit">
                    <h3>${getTranslation('editing')} ${data.id}</h3>
                    <div class="archetype-form-group">
                        <label>${getTranslation('document')}</label>
                        <textarea id="vector-db-edit-document" rows="10" style="width: 100%;">${data.document}</textarea>
                    </div>
                    <div class="archetype-form-group">
                        <label>${getTranslation('metadata')}</label>
                        <textarea id="vector-db-edit-metadata" rows="5" style="width: 100%;">${JSON.stringify(data.metadata, null, 2)}</textarea>
                    </div>
                    <div class="config-actions">
                        <button id="vector-db-save-edit-btn" class="config-btn-save" data-id="${data.id}">${getTranslation('save')}</button>
                        <button id="vector-db-cancel-edit-btn" class="config-btn-add">${getTranslation('cancel')}</button>
                    </div>
                </div>
            `;
            
            document.getElementById('vector-db-save-edit-btn').addEventListener('click', async () => {
                const document = document.getElementById('vector-db-edit-document').value;
                let metadata = {};
                try {
                    metadata = JSON.parse(document.getElementById('vector-db-edit-metadata').value);
                } catch (e) {
                    alert('Невірний формат JSON для метаданих');
                    return;
                }
                
                try {
                    const headers = getAuthHeaders();
                    headers['Content-Type'] = 'application/json';
                    const saveResponse = await fetch(`/api/vector-db/${chatId}`, {
                        method: 'POST',
                        headers,
                        body: JSON.stringify({ document, metadata })
                    });
                    
                    const saveData = await saveResponse.json();
                    
                    if (saveData.status === 'success') {
                        alert(getTranslation('entryUpdated'));
                        await loadVectorDbEntries();
                        viewVectorDbEntry(chatId);
                    } else {
                        alert(getTranslation('updateError') + ' ' + (saveData.detail || getTranslation('unknownError')));
                    }
                } catch (error) {
                    alert(getTranslation('saveError') + ' ' + error.message);
                }
            });
            
            document.getElementById('vector-db-cancel-edit-btn').addEventListener('click', () => {
                viewVectorDbEntry(chatId);
            });
        } catch (error) {
            console.error('Помилка редагування запису:', error);
            elements.vectorDbEntryView.innerHTML = `<pre><code>${getTranslation('loadEntryError')}</code></pre>`;
        }
    }
    
    async function deleteVectorDbEntry(chatId) {
        if (!confirm(getTranslation('deleteEntryConfirm').replace('{id}', chatId))) {
            return;
        }
        
        try {
            const response = await fetch(`/api/vector-db/${chatId}`, {
                method: 'DELETE',
                headers: getAuthHeaders()
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                alert(getTranslation('entryDeleted'));
                await loadVectorDbEntries();
                elements.vectorDbEntryView.innerHTML = `<pre><code>${getTranslation('selectEntry')}</code></pre>`;
            } else {
                alert(getTranslation('deleteError') + ' ' + (data.detail || getTranslation('unknownError')));
            }
        } catch (error) {
            alert(getTranslation('deleteError') + ' ' + error.message);
        }
    }
    
    // Export history file function
    async function exportHistoryFile(filename, format) {
        try {
            const response = await fetch(`/api/history/export/${filename}?format=${format}`);
            const data = await response.json();
            
            // Create download link
            const blob = new Blob(
                [format === 'markdown' ? data.content : JSON.stringify(data.content, null, 2)],
                { type: format === 'markdown' ? 'text/markdown' : 'application/json' }
            );
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = data.filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            alert(`Файл експортовано: ${data.filename}`);
        } catch (error) {
            console.error('Error exporting file:', error);
            alert('Помилка експорту файлу');
        }
    }
    
    // Add export all button to history modal
    if (elements.historyBtn) {
        const originalHistoryClick = elements.historyBtn.onclick;
        elements.historyBtn.addEventListener('click', () => {
            // Add export all button if not exists
            setTimeout(() => {
                const historyModal = document.getElementById('history-modal');
                if (historyModal && !historyModal.querySelector('.export-all-btn-container')) {
                    const exportContainer = document.createElement('div');
                    exportContainer.className = 'export-all-btn-container';
                    exportContainer.style.marginBottom = '10px';
                    exportContainer.style.padding = '10px';
                    exportContainer.style.borderBottom = '1px solid var(--border-color)';
                    
                    const exportAllBtn = document.createElement('button');
                    exportAllBtn.textContent = '📥 Експорт всіх чатів';
                    exportAllBtn.style.padding = '8px 15px';
                    exportAllBtn.style.marginRight = '10px';
                    exportAllBtn.onclick = async () => {
                        const format = confirm('Експортувати в Markdown? (OK - Markdown, Cancel - JSON)') ? 'markdown' : 'json';
                        try {
                            const response = await fetch(`/api/history/export/all?format=${format}`);
                            const data = await response.json();
                            
                            // Create download link
                            const blob = new Blob(
                                [format === 'markdown' ? data.content : JSON.stringify(data.content, null, 2)],
                                { type: format === 'markdown' ? 'text/markdown' : 'application/json' }
                            );
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = data.filename;
                            document.body.appendChild(a);
                            a.click();
                            document.body.removeChild(a);
                            URL.revokeObjectURL(url);
                            
                            alert(`Експортовано ${data.total_chats} чатів: ${data.filename}`);
                        } catch (error) {
                            console.error('Error exporting all files:', error);
                            alert('Помилка експорту');
                        }
                    };
                    exportContainer.appendChild(exportAllBtn);
                    
                    const historySearchContainer = historyModal.querySelector('.history-search-container');
                    if (historySearchContainer) {
                        historySearchContainer.parentNode.insertBefore(exportContainer, historySearchContainer);
                    } else {
                        const historyContent = historyModal.querySelector('.modal-content');
                        if (historyContent) {
                            const h2 = historyContent.querySelector('h2');
                            if (h2 && h2.nextSibling) {
                                historyContent.insertBefore(exportContainer, h2.nextSibling);
                            }
                        }
                    }
                }
            }, 100);
        });
    }
    
    // --- Statistics Modal ---
    if (elements.statsBtn) {
        elements.statsBtn.addEventListener('click', async () => {
            if (elements.dropdownMenu) {
                elements.dropdownMenu.classList.add('hidden');
            }
            elements.statsModal.classList.remove('hidden');
            elements.statsLoading.classList.remove('hidden');
            elements.statsWrapper.classList.add('hidden');
            await loadStatistics();
        });
    }
    
    // --- File Upload Modal ---
    // Функція для оновлення статусу вибору файлу
    function updateFileSelectionStatus() {
        const fileSelectionStatus = document.getElementById('file-selection-status');
        if (!fileSelectionStatus) return;
        
        // Очищаємо попередній вміст повністю
        while (fileSelectionStatus.firstChild) {
            fileSelectionStatus.removeChild(fileSelectionStatus.firstChild);
        }
        
        if (elements.fileInput && elements.fileInput.files && elements.fileInput.files.length > 0) {
            fileSelectionStatus.textContent = elements.fileInput.files[0].name;
        } else {
            const currentLang = localStorage.getItem('language') || 'uk';
            const text = currentLang === 'en' ? 'File not selected' : 'Файл не вибрано';
            fileSelectionStatus.textContent = text;
        }
    }
    
    if (elements.uploadFileBtn) {
        elements.uploadFileBtn.addEventListener('click', () => {
            if (elements.dropdownMenu) {
                elements.dropdownMenu.classList.add('hidden');
            }
            elements.uploadFileModal.classList.remove('hidden');
            // Reset form
            if (elements.fileInput) elements.fileInput.value = '';
            elements.uploadFileProgress.classList.add('hidden');
            elements.uploadFileMessage.textContent = '';
            // Оновлюємо статус вибору файлу
            updateFileSelectionStatus();
        });
    }
    
    // Обробник зміни файлу
    if (elements.fileInput) {
        elements.fileInput.addEventListener('change', () => {
            updateFileSelectionStatus();
        });
    }
    
    if (elements.uploadFileCloseBtn) {
        elements.uploadFileCloseBtn.addEventListener('click', () => {
            elements.uploadFileModal.classList.add('hidden');
        });
    }
    
    if (elements.uploadFileCancelBtn) {
        elements.uploadFileCancelBtn.addEventListener('click', () => {
            elements.uploadFileModal.classList.add('hidden');
        });
    }
    
    if (elements.uploadFileSubmitBtn) {
        elements.uploadFileSubmitBtn.addEventListener('click', async () => {
            await handleFileUpload();
        });
    }
    
    async function handleFileUpload() {
        if (!elements.fileInput || !elements.fileInput.files || elements.fileInput.files.length === 0) {
            showUploadMessage(getTranslation('pleaseSelectFile'), 'error');
            return;
        }
        
        const file = elements.fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);
        
        // Show progress
        elements.uploadFileProgress.classList.remove('hidden');
        elements.uploadFileStatus.textContent = getTranslation('uploadingFile');
        elements.uploadFileProgressBar.style.width = '30%';
        elements.uploadFileSubmitBtn.disabled = true;
        elements.uploadFileMessage.textContent = '';
        
        try {
            const response = await fetch('/api/files/upload', {
                method: 'POST',
                body: formData
            });
            
            elements.uploadFileProgressBar.style.width = '70%';
            elements.uploadFileStatus.textContent = getTranslation('processingFile');
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || getTranslation('uploadFileError'));
            }
            
            elements.uploadFileProgressBar.style.width = '100%';
            elements.uploadFileStatus.textContent = getTranslation('ready');
            
            const fileProcessedMsg = getTranslation('fileProcessed')
                .replace('{filename}', data.filename)
                .replace('{chunks}', data.chunks_count);
            showUploadMessage(fileProcessedMsg, 'success');
            
            // Reset form after delay
            setTimeout(() => {
                elements.uploadFileModal.classList.add('hidden');
                elements.uploadFileProgress.classList.add('hidden');
                if (elements.fileInput) elements.fileInput.value = '';
                elements.uploadFileSubmitBtn.disabled = false;
            }, 2000);
            
        } catch (error) {
            elements.uploadFileProgress.classList.add('hidden');
            showUploadMessage(`Помилка: ${error.message}`, 'error');
            elements.uploadFileSubmitBtn.disabled = false;
        }
    }
    
    function showUploadMessage(message, type) {
        if (!elements.uploadFileMessage) return;
        
        elements.uploadFileMessage.textContent = message;
        elements.uploadFileMessage.style.padding = '10px';
        elements.uploadFileMessage.style.borderRadius = '4px';
        elements.uploadFileMessage.style.marginBottom = '15px';
        
        if (type === 'success') {
            elements.uploadFileMessage.style.background = '#d4edda';
            elements.uploadFileMessage.style.color = '#155724';
            elements.uploadFileMessage.style.border = '1px solid #c3e6cb';
        } else if (type === 'error') {
            elements.uploadFileMessage.style.background = '#f8d7da';
            elements.uploadFileMessage.style.color = '#721c24';
            elements.uploadFileMessage.style.border = '1px solid #f5c6cb';
        }
    }
    
    if (elements.statsCloseBtn) {
        elements.statsCloseBtn.addEventListener('click', () => {
            elements.statsModal.classList.add('hidden');
        });
    }
    
    if (elements.refreshStatsBtn) {
        elements.refreshStatsBtn.addEventListener('click', async () => {
            await loadStatistics();
        });
    }
    
    if (elements.resetStatsBtn) {
        elements.resetStatsBtn.addEventListener('click', async () => {
            if (confirm(getTranslation('resetStatsConfirm'))) {
                try {
                    const response = await fetch('/api/metrics/reset', { method: 'POST' });
                    const data = await response.json();
                    if (data.status === 'success') {
                        alert(getTranslation('statsReset'));
                        await loadStatistics();
                    } else {
                        alert(getTranslation('resetStatsError'));
                    }
                } catch (error) {
                    console.error('Error resetting stats:', error);
                    alert(getTranslation('resetStatsError'));
                }
            }
        });
    }
    
    async function loadStatistics() {
        try {
            const response = await fetch('/api/metrics');
            const data = await response.json();
            
            let html = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px;">';
            
            // Counters
            if (data.counters && Object.keys(data.counters).length > 0) {
                html += '<div class="stats-section">';
                html += `<h3>${getTranslation('counters')}</h3>`;
                html += '<ul style="list-style: none; padding: 0;">';
                for (const [key, value] of Object.entries(data.counters)) {
                    html += `<li style="padding: 5px 0; border-bottom: 1px solid var(--border-color);"><strong>${key}:</strong> ${value}</li>`;
                }
                html += '</ul>';
                html += '</div>';
            }
            
            // Archetype usage
            if (data.archetype_usage && Object.keys(data.archetype_usage).length > 0) {
                html += '<div class="stats-section">';
                html += `<h3>${getTranslation('archetypeUsage')}</h3>`;
                html += '<ul style="list-style: none; padding: 0;">';
                const sorted = Object.entries(data.archetype_usage).sort((a, b) => b[1] - a[1]);
                for (const [archetype, count] of sorted) {
                    html += `<li style="padding: 5px 0; border-bottom: 1px solid var(--border-color);"><strong>${archetype}:</strong> ${count}</li>`;
                }
                html += '</ul>';
                html += '</div>';
            }
            
            // Cache statistics
            if (data.cache) {
                html += '<div class="stats-section">';
                html += `<h3>${getTranslation('cache')}</h3>`;
                html += `<p><strong>${getTranslation('cacheSize')}</strong> ${data.cache.cache_size} ${getTranslation('entries')}</p>`;
                html += `<p><strong>${getTranslation('hits')}</strong> ${data.cache.hits}</p>`;
                html += `<p><strong>${getTranslation('misses')}</strong> ${data.cache.misses}</p>`;
                html += `<p><strong>${getTranslation('totalRequests')}</strong> ${data.cache.total_requests}</p>`;
                html += `<p><strong>${getTranslation('hitRate')}</strong> ${(data.cache.hit_rate * 100).toFixed(1)}%</p>`;
                html += `<p><strong>${getTranslation('evictions')}</strong> ${data.cache.evictions}</p>`;
                
                // Cache management buttons
                html += '<div style="margin-top: 10px;">';
                html += `<button onclick="clearCache()" style="padding: 5px 10px; margin-right: 5px; background: var(--accent-color); color: white; border: none; border-radius: 4px; cursor: pointer;">${getTranslation('clearCache')}</button>`;
                html += `<button onclick="clearExpiredCache()" style="padding: 5px 10px; background: var(--accent-color); color: white; border: none; border-radius: 4px; cursor: pointer;">${getTranslation('clearExpired')}</button>`;
                html += '</div>';
                html += '</div>';
            }
            
            // History statistics
            if (data.history) {
                html += '<div class="stats-section">';
                html += `<h3>${getTranslation('history')}</h3>`;
                html += `<p><strong>${getTranslation('totalChats')}</strong> ${data.history.total_chats}</p>`;
                html += '</div>';
            }
            
            // Vector DB statistics
            if (data.vector_db) {
                html += '<div class="stats-section">';
                html += `<h3>${getTranslation('vectorDatabase')}</h3>`;
                html += `<p><strong>${getTranslation('totalEntries')}</strong> ${data.vector_db.total_entries}</p>`;
                html += '</div>';
            }
            
            // Timers
            if (data.timers && Object.keys(data.timers).length > 0) {
                html += '<div class="stats-section" style="grid-column: 1 / -1;">';
                html += `<h3>${getTranslation('timers')}</h3>`;
                html += '<table style="width: 100%; border-collapse: collapse;">';
                html += `<tr><th style="text-align: left; padding: 5px; border-bottom: 1px solid var(--border-color);">${getTranslation('name')}</th><th style="text-align: left; padding: 5px; border-bottom: 1px solid var(--border-color);">${getTranslation('min')}</th><th style="text-align: left; padding: 5px; border-bottom: 1px solid var(--border-color);">${getTranslation('max')}</th><th style="text-align: left; padding: 5px; border-bottom: 1px solid var(--border-color);">${getTranslation('average')}</th><th style="text-align: left; padding: 5px; border-bottom: 1px solid var(--border-color);">${getTranslation('count')}</th></tr>`;
                for (const [name, stats] of Object.entries(data.timers)) {
                    html += `<tr><td style="padding: 5px; border-bottom: 1px solid var(--border-color);">${name}</td><td style="padding: 5px; border-bottom: 1px solid var(--border-color);">${stats.min.toFixed(3)}s</td><td style="padding: 5px; border-bottom: 1px solid var(--border-color);">${stats.max.toFixed(3)}s</td><td style="padding: 5px; border-bottom: 1px solid var(--border-color);">${stats.avg.toFixed(3)}s</td><td style="padding: 5px; border-bottom: 1px solid var(--border-color);">${stats.count}</td></tr>`;
                }
                html += '</table>';
                html += '</div>';
            }
            
            html += '</div>';
            
            elements.statsContent.innerHTML = html;
            elements.statsLoading.classList.add('hidden');
            elements.statsWrapper.classList.remove('hidden');
        } catch (error) {
            console.error('Error loading statistics:', error);
            elements.statsLoading.textContent = getTranslation('statsLoadError') + ' ' + error.message;
        }
    }
    
    // Cache management functions (global for onclick handlers)
    window.clearCache = async function() {
        if (confirm(getTranslation('clearCacheConfirm'))) {
            try {
                const response = await fetch('/api/cache/clear', { method: 'POST' });
                const data = await response.json();
                if (data.status === 'success') {
                    alert(getTranslation('cacheCleared'));
                    await loadStatistics();
                } else {
                    alert(getTranslation('clearCacheError'));
                }
            } catch (error) {
                console.error('Error clearing cache:', error);
                    alert(getTranslation('clearCacheError'));
            }
        }
    };
    
    window.clearExpiredCache = async function() {
        try {
            const response = await fetch('/api/cache/clear-expired', { method: 'POST' });
            const data = await response.json();
            if (data.status === 'success') {
                alert(getTranslation('clearedExpiredEntries').replace('{count}', data.cleared_count));
                await loadStatistics();
            } else {
                alert(getTranslation('clearExpiredCacheError'));
            }
        } catch (error) {
            console.error('Error clearing expired cache:', error);
            alert(getTranslation('clearExpiredCacheError'));
        }
    };
    
    // --- Dropdown Menu ---
    if (elements.menuBtn && elements.dropdownMenu) {
        // Перемикання випадаючого меню
        elements.menuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            elements.dropdownMenu.classList.toggle('hidden');
        });
        
        // Закрити меню при кліку поза ним
        document.addEventListener('click', (e) => {
            if (!elements.menuBtn.contains(e.target) && !elements.dropdownMenu.contains(e.target)) {
                elements.dropdownMenu.classList.add('hidden');
            }
        });
        
    }
    
    // --- Language Switcher ---
    function setLanguage(lang) {
        // Зберігаємо вибір в localStorage
        localStorage.setItem('language', lang);
        
        // Оновлюємо активну кнопку
        if (elements.langUkBtn && elements.langEnBtn) {
            elements.langUkBtn.classList.toggle('active', lang === 'uk');
            elements.langEnBtn.classList.toggle('active', lang === 'en');
        }
        
        // Оновлюємо атрибут lang в HTML
        document.documentElement.lang = lang;
        
        // Оновлюємо текст інтерфейсу одразу
        updateUIText(lang);
        
        // Оновлюємо статус вибору файлу
        if (typeof updateFileSelectionStatus === 'function') {
            updateFileSelectionStatus();
        }
        
        // Відправляємо запит на сервер для оновлення мови
        fetch('/api/set-language', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ language: lang })
        }).then((response) => {
            if (response.ok) {
                // Не перезавантажуємо сторінку, оскільки текст вже оновлено
                console.log('Language changed to:', lang);
            } else {
                console.error('Failed to set language on server');
            }
        }).catch(err => {
            console.error('Error setting language:', err);
        });
    }
    
    if (elements.langUkBtn) {
        elements.langUkBtn.addEventListener('click', () => setLanguage('uk'));
    }
    
    if (elements.langEnBtn) {
        elements.langEnBtn.addEventListener('click', () => setLanguage('en'));
    }
    
    // Завантажуємо збережену мову при завантаженні сторінки
    const savedLanguage = localStorage.getItem('language') || 'uk';
    if (savedLanguage === 'en' && elements.langEnBtn) {
        elements.langEnBtn.classList.add('active');
        if (elements.langUkBtn) elements.langUkBtn.classList.remove('active');
        document.documentElement.lang = 'en';
    } else {
        if (elements.langUkBtn) elements.langUkBtn.classList.add('active');
        if (elements.langEnBtn) elements.langEnBtn.classList.remove('active');
        document.documentElement.lang = 'uk';
    }
    
    // Функція для отримання перекладу
    function getTranslation(key) {
        const lang = localStorage.getItem('language') || 'uk';
        const translations = {
            uk: {
                allArchetypes: 'Всі архетипи',
                loading: 'Завантаження...',
                selectChat: 'Оберіть чат для перегляду...',
                delete: 'Видалити',
                deleteChatConfirm: 'Видалити цей чат з історії та памʼяті?',
                deleteFailed: 'Не вдалося видалити файл!',
                exportJson: 'Експорт в JSON',
                exportMarkdown: 'Експорт в Markdown',
                nothingFound: 'Нічого не знайдено.',
                historyEmpty: 'Історія порожня.',
                historyLoadFailed: 'Не вдалося завантажити історію.',
                fileLoadFailed: 'Не вдалося завантажити файл:',
                nothingFoundQuery: 'Нічого не знайдено за запитом.',
                vectorDbEmpty: 'Векторна база даних порожня',
                selectEntry: 'Оберіть запис для перегляду...',
                deleteError: 'Помилка видалення:',
                uploadingFile: 'Завантаження файлу...',
                entryDeleted: 'Запис видалено успішно',
                unknownError: 'Невідома помилка',
                resetStatsError: 'Помилка скидання статистики',
                clearCacheError: 'Помилка очищення кешу',
                // Векторна БД - кнопки редагування
                view: 'Переглянути',
                edit: 'Редагувати',
                save: 'Зберегти',
                cancel: 'Скасувати',
                editing: 'Редагування:',
                document: 'Документ:',
                metadata: 'Метадані (JSON):',
                metadataLabel: 'Метадані:',
                loadEntryError: 'Помилка завантаження запису',
                archetypes: 'Архетипи:',
                deleteEntryConfirm: 'Видалити запис {id}?',
                // Завантажити файл
                pleaseSelectFile: 'Будь ласка, оберіть файл',
                fileNotSelected: 'Файл не вибрано',
                processingFile: 'Обробка файлу...',
                ready: 'Готово!',
                uploadFileError: 'Помилка завантаження файлу',
                fileProcessed: 'Файл "{filename}" успішно оброблено! Створено {chunks} частин.',
                // Налаштування агентів - форма
                agentKey: 'Ключ агента (ID)',
                agentKeyHelp: 'Унікальний ідентифікатор агента (тільки латинські літери, цифри, підкреслення)',
                agentKeyError: 'Ключ може містити тільки латинські літери, цифри та підкреслення',
                agentName: 'Назва',
                agentNameHelp: 'Відображається назва агента',
                agentDescription: 'Опис',
                agentDescriptionHelp: 'Короткий опис ролі агента',
                agentModel: 'Модель',
                agentModelHelp: 'Модель Gemini для використання',
                agentRole: 'Роль',
                agentRoleHelp: 'Роль агента для режиму РАДА',
                roleCreative: 'Творчий генератор (creative_generator)',
                roleCritic: 'Критик (critic)',
                roleExecutor: 'Виконавець (executor)',
                modelParams: 'Параметри моделі (опціонально)',
                modelParamsHelp: 'Параметри генерації для моделі. Якщо не вказано, використовуються значення за замовчуванням.',
                temperature: 'Temperature',
                temperatureHelp: 'Креативність відповіді (0.0-2.0). За замовчуванням: 0.7',
                maxTokens: 'Max Tokens',
                maxTokensHelp: 'Максимальна кількість токенів у відповіді. За замовчуванням: 2000',
                topP: 'Top P',
                topPHelp: 'Ядро вибірки (0.0-1.0). За замовчуванням: не встановлено',
                topK: 'Top K',
                topKHelp: 'Кількість найкращих токенів для вибірки. За замовчуванням: не встановлено',
                notSet: 'не встановлено',
                promptType: 'Тип промпту',
                promptFile: 'Файл з промптом (опціонально)',
                promptFileHelp: 'Шлях до файлу з основним промптом (наприклад: prompts/sofiya_base.txt). Якщо не вказано, буде створено автоматично.',
                promptContent: 'Вміст промпту *',
                promptContentHelp: 'Вміст основного промпту. Буде збережено в файл (вказаний вище або автоматично створений).',
                additionalPrompts: 'Додаткові промпти',
                additionalPromptsHelp: 'Додаткові промпти (файли або текст)',
                addPrompt: '+ Додати промпт',
                newAgent: 'Новий агент',
                deleteAgent: 'Видалити',
                deleteAgentConfirm: 'Видалити агента "{name}"?',
                saving: 'Збереження...',
                configSaved: 'Конфігурація збережена успішно!',
                saveError: 'Помилка збереження',
                loadError: 'Помилка завантаження:',
                // Статистика - контент
                counters: 'Лічильники',
                archetypeUsage: 'Використання архетипів',
                cache: 'Кеш',
                cacheSize: 'Розмір кешу:',
                entries: 'записів',
                hits: 'Попадань:',
                misses: 'Промахів:',
                totalRequests: 'Всього запитів:',
                hitRate: 'Частота попадань:',
                evictions: 'Видалено записів:',
                clearCache: 'Очистити кеш',
                clearExpired: 'Очистити застарілі',
                history: 'Історія',
                totalChats: 'Всього чатів:',
                vectorDatabase: 'Векторна база даних',
                totalEntries: 'Всього записів:',
                timers: 'Таймери',
                name: 'Назва',
                min: 'Мін',
                max: 'Макс',
                average: 'Середнє',
                count: 'Кількість',
                statsLoadError: 'Помилка завантаження статистики:',
                clearExpiredCacheError: 'Помилка очищення застарілого кешу',
                clearedExpiredEntries: 'Очищено {count} застарілих записів'
            },
            en: {
                allArchetypes: 'All archetypes',
                loading: 'Loading...',
                selectChat: 'Select a chat to view...',
                delete: 'Delete',
                deleteChatConfirm: 'Delete this chat from history and memory?',
                deleteFailed: 'Failed to delete file!',
                exportJson: 'Export to JSON',
                exportMarkdown: 'Export to Markdown',
                nothingFound: 'Nothing found.',
                historyEmpty: 'History is empty.',
                historyLoadFailed: 'Failed to load history.',
                fileLoadFailed: 'Failed to load file:',
                nothingFoundQuery: 'Nothing found for query.',
                vectorDbEmpty: 'Vector database is empty',
                selectEntry: 'Select an entry to view...',
                deleteError: 'Delete error:',
                uploadingFile: 'Uploading file...',
                entryDeleted: 'Entry deleted successfully',
                unknownError: 'Unknown error',
                resetStatsError: 'Error resetting statistics',
                clearCacheError: 'Error clearing cache',
                // Векторна БД - кнопки редагування
                view: 'View',
                edit: 'Edit',
                save: 'Save',
                cancel: 'Cancel',
                editing: 'Editing:',
                document: 'Document:',
                metadata: 'Metadata (JSON):',
                metadataLabel: 'Metadata:',
                loadEntryError: 'Error loading entry',
                archetypes: 'Archetypes:',
                deleteEntryConfirm: 'Delete entry {id}?',
                // Завантажити файл
                pleaseSelectFile: 'Please select a file',
                fileNotSelected: 'File not selected',
                processingFile: 'Processing file...',
                ready: 'Ready!',
                uploadFileError: 'File upload error',
                fileProcessed: 'File "{filename}" processed successfully! Created {chunks} chunks.',
                // Налаштування агентів - форма
                agentKey: 'Agent Key (ID)',
                agentKeyHelp: 'Unique agent identifier (only Latin letters, numbers, underscores)',
                agentKeyError: 'Key can only contain Latin letters, numbers, and underscores',
                agentName: 'Name',
                agentNameHelp: 'Displayed agent name',
                agentDescription: 'Description',
                agentDescriptionHelp: 'Brief description of agent role',
                agentModel: 'Model',
                agentModelHelp: 'Gemini model to use',
                agentRole: 'Role',
                agentRoleHelp: 'Agent role for RADA mode',
                roleCreative: 'Creative Generator (creative_generator)',
                roleCritic: 'Critic (critic)',
                roleExecutor: 'Executor (executor)',
                modelParams: 'Model Parameters (optional)',
                modelParamsHelp: 'Generation parameters for the model. If not specified, default values are used.',
                temperature: 'Temperature',
                temperatureHelp: 'Response creativity (0.0-2.0). Default: 0.7',
                maxTokens: 'Max Tokens',
                maxTokensHelp: 'Maximum number of tokens in response. Default: 2000',
                topP: 'Top P',
                topPHelp: 'Nucleus sampling (0.0-1.0). Default: not set',
                topK: 'Top K',
                topKHelp: 'Number of top tokens for sampling. Default: not set',
                notSet: 'not set',
                promptType: 'Prompt Type',
                promptFile: 'Prompt File (optional)',
                promptFileHelp: 'Path to file with main prompt (e.g., prompts/sofiya_base.txt). If not specified, will be created automatically.',
                promptContent: 'Prompt Content *',
                promptContentHelp: 'Main prompt content. Will be saved to file (specified above or automatically created).',
                additionalPrompts: 'Additional Prompts',
                additionalPromptsHelp: 'Additional prompts (files or text)',
                addPrompt: '+ Add Prompt',
                newAgent: 'New Agent',
                deleteAgent: 'Delete',
                deleteAgentConfirm: 'Delete agent "{name}"?',
                saving: 'Saving...',
                configSaved: 'Configuration saved successfully!',
                saveError: 'Save error',
                loadError: 'Load error:',
                // Статистика - контент
                counters: 'Counters',
                archetypeUsage: 'Archetype Usage',
                cache: 'Cache',
                cacheSize: 'Cache Size:',
                entries: 'entries',
                hits: 'Hits:',
                misses: 'Misses:',
                totalRequests: 'Total Requests:',
                hitRate: 'Hit Rate:',
                evictions: 'Evictions:',
                clearCache: 'Clear Cache',
                clearExpired: 'Clear Expired',
                history: 'History',
                totalChats: 'Total Chats:',
                vectorDatabase: 'Vector Database',
                totalEntries: 'Total Entries:',
                timers: 'Timers',
                name: 'Name',
                min: 'Min',
                max: 'Max',
                average: 'Average',
                count: 'Count',
                statsLoadError: 'Error loading statistics:',
                clearExpiredCacheError: 'Error clearing expired cache',
                clearedExpiredEntries: 'Cleared {count} expired entries'
            }
        };
        return translations[lang]?.[key] || translations.uk[key] || key;
    }
    
    // Оновлюємо текст інтерфейсу відповідно до мови
    function updateUIText(lang) {
        const translations = {
            uk: {
                newChat: 'Новий чат',
                history: 'Історія',
                menu: '☰ Меню',
                ready: 'Готово до роботи. Оберіть архетип та поставте запитання.',
                send: 'Відправити',
                typeMessage: 'Введіть повідомлення... (Shift+Enter — новий рядок)',
                rememberChat: 'Запамʼятати цей чат',
                theme: 'Тема',
                agentSettings: 'Налаштування агентів',
                aiProvider: 'AI Провайдер',
                vectorDb: 'Векторна БД',
                uploadFile: 'Завантажити файл',
                stats: 'Статистика',
                endSession: 'Завершити сеанс',
                // Історія
                historyTitle: 'Історія розмов',
                searchText: 'Пошук по тексту...',
                allArchetypes: 'Всі архетипи',
                search: 'Пошук',
                clear: 'Очистити',
                selectChat: 'Оберіть чат для перегляду...',
                // Налаштування агентів
                configTitle: 'Налаштування агентів',
                loading: 'Завантаження...',
                addAgent: '+ Додати агента',
                saveConfig: 'Зберегти конфігурацію',
                // AI Провайдер
                aiProviderTitle: 'Налаштування AI Провайдера',
                provider: 'Провайдер:',
                googleApiKey: 'Google API Key:',
                openaiApiKey: 'OpenAI API Key:',
                openaiBaseUrl: 'OpenAI Base URL (опціонально):',
                enterGoogleKey: 'Введіть Google API ключ',
                enterOpenaiKey: 'Введіть OpenAI API ключ',
                saveSettings: 'Зберегти налаштування',
                // Векторна БД
                vectorDbTitle: 'Векторна База Даних',
                searchRelevantChats: 'Пошук релевантних чатів...',
                // Завантажити файл
                uploadFileTitle: 'Завантажити файл',
                uploadFileDescription: 'Завантажте текстовий файл для обробки та збереження в векторну базу даних. Файл буде розбитий на частини та доданий до контексту для асистента.',
                selectFile: 'Оберіть файл:',
                supportedFormats: 'Підтримувані формати: .txt, .md, .docx, .pdf',
                processing: 'Обробка...',
                upload: 'Завантажити',
                cancel: 'Скасувати',
                // Статистика
                statsTitle: 'Статистика використання',
                refresh: 'Оновити',
                resetStats: 'Скинути статистику',
                // Додаткові тексти
                availableModels: 'Доступні моделі:',
                supportedModels: 'Підтримувані моделі:',
                modelsLoading: 'Моделі завантажуються...',
                modelsError: 'Помилка завантаження моделей',
                // Динамічні тексти
                delete: 'Видалити',
                deleteChatConfirm: 'Видалити цей чат з історії та памʼяті?',
                deleteFailed: 'Не вдалося видалити файл!',
                exportJson: 'Експорт в JSON',
                exportMarkdown: 'Експорт в Markdown',
                nothingFound: 'Нічого не знайдено.',
                historyEmpty: 'Історія порожня.',
                historyLoadFailed: 'Не вдалося завантажити історію.',
                fileLoadFailed: 'Не вдалося завантажити файл:',
                nothingFoundQuery: 'Нічого не знайдено за запитом.',
                vectorDbEmpty: 'Векторна база даних порожня',
                selectEntry: 'Оберіть запис для перегляду...',
                deleteError: 'Помилка видалення:',
                uploadingFile: 'Завантаження файлу...',
                numberResults: 'Кількість результатів',
                entryDeleted: 'Запис видалено успішно',
                unknownError: 'Невідома помилка'
            },
            en: {
                newChat: 'New Chat',
                history: 'History',
                menu: '☰ Menu',
                ready: 'Ready to work. Select an archetype and ask a question.',
                send: 'Send',
                typeMessage: 'Type a message... (Shift+Enter for new line)',
                rememberChat: 'Remember this chat',
                theme: 'Theme',
                agentSettings: 'Agent Settings',
                aiProvider: 'AI Provider',
                vectorDb: 'Vector DB',
                uploadFile: 'Upload File',
                stats: 'Statistics',
                endSession: 'End Session',
                // Історія
                historyTitle: 'Chat History',
                searchText: 'Search by text...',
                allArchetypes: 'All archetypes',
                search: 'Search',
                clear: 'Clear',
                selectChat: 'Select a chat to view...',
                // Налаштування агентів
                configTitle: 'Agent Settings',
                loading: 'Loading...',
                addAgent: '+ Add Agent',
                saveConfig: 'Save Configuration',
                // AI Провайдер
                aiProviderTitle: 'AI Provider Settings',
                provider: 'Provider:',
                googleApiKey: 'Google API Key:',
                openaiApiKey: 'OpenAI API Key:',
                openaiBaseUrl: 'OpenAI Base URL (optional):',
                enterGoogleKey: 'Enter Google API key',
                enterOpenaiKey: 'Enter OpenAI API key',
                saveSettings: 'Save Settings',
                // Векторна БД
                vectorDbTitle: 'Vector Database',
                searchRelevantChats: 'Search relevant chats...',
                // Завантажити файл
                uploadFileTitle: 'Upload File',
                uploadFileDescription: 'Upload a text file for processing and saving to the vector database. The file will be split into parts and added to the context for the assistant.',
                selectFile: 'Select File:',
                supportedFormats: 'Supported formats: .txt, .md, .docx, .pdf',
                processing: 'Processing...',
                upload: 'Upload',
                cancel: 'Cancel',
                // Статистика
                statsTitle: 'Usage Statistics',
                refresh: 'Refresh',
                resetStats: 'Reset Statistics',
                // Додаткові тексти
                availableModels: 'Available Models:',
                supportedModels: 'Supported Models:',
                modelsLoading: 'Loading models...',
                modelsError: 'Error loading models',
                // Динамічні тексти
                delete: 'Delete',
                deleteChatConfirm: 'Delete this chat from history and memory?',
                deleteFailed: 'Failed to delete file!',
                exportJson: 'Export to JSON',
                exportMarkdown: 'Export to Markdown',
                nothingFound: 'Nothing found.',
                historyEmpty: 'History is empty.',
                historyLoadFailed: 'Failed to load history.',
                fileLoadFailed: 'Failed to load file:',
                nothingFoundQuery: 'Nothing found for query.',
                vectorDbEmpty: 'Vector database is empty',
                selectEntry: 'Select an entry to view...',
                deleteError: 'Delete error:',
                uploadingFile: 'Uploading file...',
                numberResults: 'Number of results',
                entryDeleted: 'Entry deleted successfully',
                unknownError: 'Unknown error'
            }
        };
        
        const t = translations[lang] || translations.uk;
        
        // Оновлюємо текст кнопок та елементів
        const newChatBtn = document.getElementById('new-chat-btn');
        if (newChatBtn) newChatBtn.textContent = t.newChat;
        
        const historyBtn = document.getElementById('history-btn');
        if (historyBtn) historyBtn.textContent = t.history;
        
        const menuBtn = document.getElementById('menu-btn');
        if (menuBtn) menuBtn.textContent = t.menu;
        
        const sendBtn = document.getElementById('send-btn');
        if (sendBtn) sendBtn.textContent = t.send;
        
        const messageInput = document.getElementById('message-input');
        if (messageInput) messageInput.placeholder = t.typeMessage;
        
        const rememberChatText = document.getElementById('remember-chat-text');
        if (rememberChatText) rememberChatText.textContent = t.rememberChat;
        
        // Оновлюємо текст в меню
        const configBtn = document.getElementById('config-btn');
        if (configBtn) configBtn.textContent = t.agentSettings;
        
        const aiProviderBtn = document.getElementById('ai-provider-btn');
        if (aiProviderBtn) aiProviderBtn.textContent = t.aiProvider;
        
        const vectorDbBtn = document.getElementById('vector-db-btn');
        if (vectorDbBtn) vectorDbBtn.textContent = t.vectorDb;
        
        const uploadFileBtn = document.getElementById('upload-file-btn');
        if (uploadFileBtn) uploadFileBtn.textContent = t.uploadFile;
        
        const statsBtn = document.getElementById('stats-btn');
        if (statsBtn) statsBtn.textContent = t.stats;
        
        const themeToggleBtn = document.getElementById('theme-toggle-btn');
        if (themeToggleBtn) themeToggleBtn.textContent = t.theme;
        
        const shutdownBtn = document.getElementById('shutdown-btn');
        if (shutdownBtn) shutdownBtn.textContent = t.endSession;
        
        // Оновлюємо текст готовності
        const readyMessage = document.querySelector('.message.assistant p');
        if (readyMessage) readyMessage.textContent = t.ready;
        
        // Історія
        const historyTitle = document.getElementById('history-modal-title');
        if (historyTitle) historyTitle.textContent = t.historyTitle;
        
        const historySearchInput = document.getElementById('history-search-input');
        if (historySearchInput) historySearchInput.placeholder = t.searchText;
        
        const historyAllArchetypes = document.getElementById('history-all-archetypes-option');
        if (historyAllArchetypes) historyAllArchetypes.textContent = t.allArchetypes;
        
        const historySearchBtn = document.getElementById('history-search-btn');
        if (historySearchBtn) historySearchBtn.textContent = t.search;
        
        const historyClearBtn = document.getElementById('history-clear-search-btn');
        if (historyClearBtn) historyClearBtn.textContent = t.clear;
        
        const historySelectChat = document.getElementById('history-select-chat-text');
        if (historySelectChat) historySelectChat.textContent = t.selectChat;
        
        // Налаштування агентів
        const configTitle = document.getElementById('config-modal-title');
        if (configTitle) configTitle.textContent = t.configTitle;
        
        const configLoading = document.getElementById('config-loading');
        if (configLoading) configLoading.textContent = t.loading;
        
        const addArchetypeBtn = document.getElementById('add-archetype-btn');
        if (addArchetypeBtn) addArchetypeBtn.textContent = t.addAgent;
        
        const saveConfigBtn = document.getElementById('save-config-btn');
        if (saveConfigBtn) saveConfigBtn.textContent = t.saveConfig;
        
        // AI Провайдер
        const aiProviderTitle = document.getElementById('ai-provider-modal-title');
        if (aiProviderTitle) aiProviderTitle.textContent = t.aiProviderTitle;
        
        const aiProviderLoading = document.getElementById('ai-provider-loading');
        if (aiProviderLoading) aiProviderLoading.textContent = t.loading;
        
        const aiProviderLabel = document.getElementById('ai-provider-label');
        if (aiProviderLabel) aiProviderLabel.textContent = t.provider;
        
        const googleApiKeyLabel = document.getElementById('google-api-key-label');
        if (googleApiKeyLabel) googleApiKeyLabel.textContent = t.googleApiKey;
        
        const openaiApiKeyLabel = document.getElementById('openai-api-key-label');
        if (openaiApiKeyLabel) openaiApiKeyLabel.textContent = t.openaiApiKey;
        
        const openaiBaseUrlLabel = document.getElementById('openai-base-url-label');
        if (openaiBaseUrlLabel) openaiBaseUrlLabel.textContent = t.openaiBaseUrl;
        
        const googleApiKeyInput = document.getElementById('google-api-key');
        if (googleApiKeyInput && !googleApiKeyInput.value) {
            googleApiKeyInput.placeholder = t.enterGoogleKey;
        }
        
        const openaiApiKeyInput = document.getElementById('openai-api-key');
        if (openaiApiKeyInput && !openaiApiKeyInput.value) {
            openaiApiKeyInput.placeholder = t.enterOpenaiKey;
        }
        
        const saveAiProviderBtn = document.getElementById('save-ai-provider-btn');
        if (saveAiProviderBtn) saveAiProviderBtn.textContent = t.saveSettings;
        
        // Векторна БД
        const vectorDbTitle = document.getElementById('vector-db-modal-title');
        if (vectorDbTitle) vectorDbTitle.textContent = t.vectorDbTitle;
        
        const vectorDbSearchInput = document.getElementById('vector-db-search-input');
        if (vectorDbSearchInput) vectorDbSearchInput.placeholder = t.searchRelevantChats;
        
        const vectorDbSearchBtn = document.getElementById('vector-db-search-btn');
        if (vectorDbSearchBtn) vectorDbSearchBtn.textContent = t.search;
        
        const vectorDbClearBtn = document.getElementById('vector-db-clear-search-btn');
        if (vectorDbClearBtn) vectorDbClearBtn.textContent = t.clear;
        
        const vectorDbLoading = document.getElementById('vector-db-loading');
        if (vectorDbLoading) vectorDbLoading.textContent = t.loading;
        
        // Векторна БД - текст вибору запису
        const vectorDbSelectEntry = document.getElementById('vector-db-select-entry-text');
        if (vectorDbSelectEntry) vectorDbSelectEntry.textContent = t.selectEntry;
        
        // Векторна БД - title атрибут
        const vectorDbNResults = document.getElementById('vector-db-search-n-results');
        if (vectorDbNResults) {
            const titleAttr = lang === 'en' ? vectorDbNResults.getAttribute('data-title-en') : vectorDbNResults.getAttribute('data-title-uk');
            if (titleAttr) vectorDbNResults.title = titleAttr;
        }
        
        // Завантажити файл
        const uploadFileTitle = document.getElementById('upload-file-modal-title');
        if (uploadFileTitle) uploadFileTitle.textContent = t.uploadFileTitle;
        
        const uploadFileDescription = document.getElementById('upload-file-description');
        if (uploadFileDescription) uploadFileDescription.textContent = t.uploadFileDescription;
        
        const uploadFileLabel = document.getElementById('upload-file-label');
        if (uploadFileLabel) uploadFileLabel.textContent = t.selectFile;
        
        const fileSelectButton = document.getElementById('file-select-button');
        if (fileSelectButton) {
            fileSelectButton.textContent = lang === 'en' ? 'Choose File' : 'Вибрати файл';
        }
        
        const uploadFileFormats = document.getElementById('upload-file-formats');
        if (uploadFileFormats) uploadFileFormats.textContent = t.supportedFormats;
        
        // Оновлюємо статус вибору файлу (якщо функція вже визначена)
        if (typeof updateFileSelectionStatus === 'function') {
            updateFileSelectionStatus();
        }
        
        const uploadFileStatus = document.getElementById('upload-file-status');
        if (uploadFileStatus && uploadFileStatus.textContent === 'Обробка...') {
            uploadFileStatus.textContent = t.processing;
        }
        
        const uploadFileSubmitBtn = document.getElementById('upload-file-submit-btn');
        if (uploadFileSubmitBtn) uploadFileSubmitBtn.textContent = t.upload;
        
        const uploadFileCancelBtn = document.getElementById('upload-file-cancel-btn');
        if (uploadFileCancelBtn) uploadFileCancelBtn.textContent = t.cancel;
        
        // Статистика
        const statsTitle = document.getElementById('stats-modal-title');
        if (statsTitle) statsTitle.textContent = t.statsTitle;
        
        const statsLoading = document.getElementById('stats-loading');
        if (statsLoading) statsLoading.textContent = t.loading;
        
        const refreshStatsBtn = document.getElementById('refresh-stats-btn');
        if (refreshStatsBtn) refreshStatsBtn.textContent = t.refresh;
        
        const resetStatsBtn = document.getElementById('reset-stats-btn');
        if (resetStatsBtn) resetStatsBtn.textContent = t.resetStats;
    }
    
    // Застосовуємо переклади при завантаженні
    updateUIText(savedLanguage);
    
    // --- Theme Toggle ---
    function toggleTheme() {
        const body = document.body;
        const isLight = body.classList.contains('light-theme');
        
        if (isLight) {
            body.classList.remove('light-theme');
            localStorage.setItem('theme', 'dark');
        } else {
            body.classList.add('light-theme');
            localStorage.setItem('theme', 'light');
        }
    }
    
    if (elements.themeToggleBtn) {
        elements.themeToggleBtn.addEventListener('click', () => {
            toggleTheme();
            if (elements.dropdownMenu) {
                elements.dropdownMenu.classList.add('hidden');
            }
        });
    }
    
    // Завантажуємо збережену тему при завантаженні сторінки
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
    }
    
    // --- Shutdown Button ---
    if (elements.shutdownBtn) {
        elements.shutdownBtn.addEventListener('click', async () => {
            elements.dropdownMenu.classList.add('hidden');
            
            if (!confirm(getTranslation('shutdownConfirm'))) {
                return;
            }
            
            try {
                elements.shutdownBtn.disabled = true;
                elements.shutdownBtn.textContent = getTranslation('shuttingDown');
                
                const response = await fetch('/api/shutdown', {
                    method: 'POST'
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    // Показуємо повідомлення та закриваємо сторінку
                    document.body.innerHTML = `
                        <div style="display: flex; justify-content: center; align-items: center; height: 100vh; flex-direction: column; color: var(--text-color);">
                            <h2>Сервер завершує роботу...</h2>
                            <p>Ви можете закрити це вікно.</p>
                        </div>
                    `;
                    
                    // Спробуємо закрити вікно через 2 секунди (якщо браузер дозволить)
                    setTimeout(() => {
                        window.close();
                    }, 2000);
                } else {
                    alert(getTranslation('shutdownError') + ' ' + (data.detail || getTranslation('unknownError')));
                    elements.shutdownBtn.disabled = false;
                    elements.shutdownBtn.textContent = t.endSession;
                }
            } catch (error) {
                // Помилка мережі означає, що сервер можливо вже завершується
                console.log('Сервер завершує роботу...');
                document.body.innerHTML = `
                    <div style="display: flex; justify-content: center; align-items: center; height: 100vh; flex-direction: column; color: var(--text-color);">
                        <h2>Сервер завершує роботу...</h2>
                        <p>Ви можете закрити це вікно.</p>
                    </div>
                `;
            }
        });
    }
});
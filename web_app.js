// Lustre Separator - Redesigned Web Controller (High-End Studio)
document.addEventListener('DOMContentLoaded', () => {
    // State
    let files = [];
    let selectedFile = null;
    let isProcessing = false;
    let processedCount = 0;
    let currentPlatform = 'facebook';

    // DOM References
    const filesList = document.getElementById('filesList');
    const emptyFilesState = document.getElementById('emptyFilesState');
    const statTotalVideos = document.getElementById('statTotalVideos');
    const statProcessedCount = document.getElementById('statProcessedCount');
    const selectionSummary = document.getElementById('selectionSummary');
    const btnRefreshFiles = document.getElementById('btnRefreshFiles');

    const platformSelect = document.getElementById('platformSelect');
    const platformChips = document.querySelectorAll('.platform-chip');
    const btnProcessAll = document.getElementById('btnProcessAll');
    const btnProcessSelected = document.getElementById('btnProcessSelected');
    const btnStop = document.getElementById('btnStop');

    const statusBadge = document.getElementById('statusBadge');
    const progressBarFill = document.getElementById('progressBarFill');
    const progressCurrentStatus = document.getElementById('progressCurrentStatus');
    const progressCounter = document.getElementById('progressCounter');
    const aiVisualizer = document.getElementById('aiVisualizer');
    const terminalLogBox = document.getElementById('terminalLogBox');
    const btnClearConsole = document.getElementById('btnClearConsole');
    const btnToggleLogs = document.getElementById('btnToggleLogs');
    const consoleBox = document.getElementById('consoleBox');

    const hookDisplay = document.getElementById('hookDisplay');
    const captionDisplay = document.getElementById('captionDisplay');
    const tagsDisplay = document.getElementById('tagsDisplay');
    const resultContent = document.getElementById('resultContent');
    const captionStatsBadge = document.getElementById('captionStatsBadge');
    const tagsCountBadge = document.getElementById('tagsCountBadge');

    const btnCopyResult = document.getElementById('btnCopyResult');
    const btnClearResult = document.getElementById('btnClearResult');
    const btnCopyHook = document.getElementById('btnCopyHook');
    const btnCopyCaption = document.getElementById('btnCopyCaption');
    const btnClearCaption = document.getElementById('btnClearCaption');
    const btnCopyTags = document.getElementById('btnCopyTags');
    const btnClearTags = document.getElementById('btnClearTags');

    const btnOpenInputFolder = document.getElementById('btnOpenInputFolder');
    const btnOpenOutputFolder = document.getElementById('btnOpenOutputFolder');

    const btnOpenSettings = document.getElementById('btnOpenSettings');
    const btnCloseSettings = document.getElementById('btnCloseSettings');
    const settingsModal = document.getElementById('settingsModal');
    const inputApiKey = document.getElementById('inputApiKey');
    const btnSaveApiKey = document.getElementById('btnSaveApiKey');

    // Studio Pro Menu Elements
    const studioProContainer = document.getElementById('studioProContainer');
    const btnStudioProBadge = document.getElementById('btnStudioProBadge');
    const studioProMenu = document.getElementById('studioProMenu');
    const studioProDot = document.getElementById('studioProDot');
    const studioProVersionText = document.getElementById('studioProVersionText');
    const spMenuVersionBadge = document.getElementById('spMenuVersionBadge');
    const spUpdateHint = document.getElementById('spUpdateHint');
    const btnStudioMenuUpdate = document.getElementById('btnStudioMenuUpdate');
    const spBadgeUpdate = document.getElementById('spBadgeUpdate');
    const spMenuUpdateDesc = document.getElementById('spMenuUpdateDesc');

    // Auto-Updater Elements
    const versionUpdaterPill = document.getElementById('versionUpdaterPill');
    const versionLabel = document.getElementById('versionLabel');
    const versionDot = document.getElementById('versionDot');
    const btnQuickUpdate = document.getElementById('btnQuickUpdate');
    const tabSettingsApi = document.getElementById('tabSettingsApi');
    const tabSettingsUpdater = document.getElementById('tabSettingsUpdater');
    const paneSettingsApi = document.getElementById('paneSettingsApi');
    const paneSettingsUpdater = document.getElementById('paneSettingsUpdater');
    const tabUpdateDot = document.getElementById('tabUpdateDot');
    const modalVersionBadge = document.getElementById('modalVersionBadge');
    const modalGitStatus = document.getElementById('modalGitStatus');
    const modalUpdateStatus = document.getElementById('modalUpdateStatus');
    const inputGitRemote = document.getElementById('inputGitRemote');
    const btnConnectGit = document.getElementById('btnConnectGit');
    const updateLogArea = document.getElementById('updateLogArea');
    const commitsListBox = document.getElementById('commitsListBox');
    const btnCheckUpdateModal = document.getElementById('btnCheckUpdateModal');
    const btnPerformUpdate = document.getElementById('btnPerformUpdate');

    // Drag & Drop / Upload Elements
    const dropOverlay = document.getElementById('dropOverlay');
    const uploadModal = document.getElementById('uploadModal');
    const uploadFileName = document.getElementById('uploadFileName');
    const uploadCountBadge = document.getElementById('uploadCountBadge');
    const uploadBarFill = document.getElementById('uploadBarFill');
    const btnAddFiles = document.getElementById('btnAddFiles');
    const btnAddFolder = document.getElementById('btnAddFolder');
    const filePickerInput = document.getElementById('filePickerInput');
    const folderPickerInput = document.getElementById('folderPickerInput');
    const btnEmptyAddFiles = document.getElementById('btnEmptyAddFiles');
    const btnEmptyAddFolder = document.getElementById('btnEmptyAddFolder');

    const toast = document.getElementById('toast');
    const toastMsg = document.getElementById('toastMsg');

    function showToast(message) {
        toastMsg.textContent = message;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3000);
    }

    function triggerCopyFeedback(button, originalHtml, successText = 'Copied! ✨') {
        button.classList.add('copy-success');
        button.innerHTML = `<i class="fa-solid fa-check"></i> ${successText}`;
        setTimeout(() => {
            button.classList.remove('copy-success');
            button.innerHTML = originalHtml;
        }, 2200);
    }

    // Platform Selector Chips
    platformChips.forEach(chip => {
        chip.addEventListener('click', () => {
            platformChips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            currentPlatform = chip.dataset.platform;
            if (platformSelect) platformSelect.value = currentPlatform;
            showToast(`Platform switched to ${currentPlatform.toUpperCase()}`);
        });
    });

    // Toggle Collapsible Logs
    if (btnToggleLogs && consoleBox) {
        btnToggleLogs.addEventListener('click', () => {
            consoleBox.classList.toggle('collapsed');
            const isCollapsed = consoleBox.classList.contains('collapsed');
            btnToggleLogs.innerHTML = isCollapsed 
                ? '<i class="fa-solid fa-chevron-up"></i> Logs' 
                : '<i class="fa-solid fa-chevron-down"></i> Logs';
        });
    }

    // View Mode Tabs (Editor View vs Feed Simulator)
    const tabEditorView = document.getElementById('tabEditorView');
    const tabMobileView = document.getElementById('tabMobileView');
    const editorViewContainer = document.getElementById('editorViewContainer');
    const mobileViewContainer = document.getElementById('mobileViewContainer');
    const simCaptionBody = document.getElementById('simCaptionBody');
    const simVideoLabel = document.getElementById('simVideoLabel');

    if (tabEditorView && tabMobileView) {
        tabEditorView.addEventListener('click', () => {
            tabEditorView.classList.add('active');
            tabMobileView.classList.remove('active');
            if (editorViewContainer) editorViewContainer.style.display = 'flex';
            if (mobileViewContainer) mobileViewContainer.style.display = 'none';
        });
        tabMobileView.addEventListener('click', () => {
            tabMobileView.classList.add('active');
            tabEditorView.classList.remove('active');
            if (editorViewContainer) editorViewContainer.style.display = 'none';
            if (mobileViewContainer) mobileViewContainer.style.display = 'flex';
        });
    }

    // --- API Calls ---
    async function loadFiles() {
        try {
            const res = await fetch('/api/files');
            const data = await res.json();
            files = data.files || [];
            renderFiles();
        } catch (err) {
            console.error('Error fetching files:', err);
        }
    }

    function renderFiles() {
        if (statTotalVideos) statTotalVideos.textContent = files.length;
        filesList.innerHTML = '';

        if (files.length === 0) {
            emptyFilesState.style.display = 'flex';
            selectionSummary.innerHTML = '<i class="fa-solid fa-circle-info"></i><span>No video selected</span>';
            btnProcessSelected.disabled = true;
            btnProcessAll.disabled = true;
            return;
        }

        emptyFilesState.style.display = 'none';
        btnProcessAll.disabled = isProcessing;

        files.forEach((f, idx) => {
            const row = document.createElement('div');
            row.className = 'file-row';
            if (selectedFile && selectedFile.rel_path === f.rel_path) {
                row.classList.add('selected');
            }

            const iconClass = f.is_video ? 'fa-film' : 'fa-image';
            const ext = f.name.substring(f.name.lastIndexOf('.'));
            const folderPart = f.name.includes('/') ? f.name.split('/')[0] : f.name.replace(/\.[^/.]+$/, "");

            row.innerHTML = `
                <div class="file-row-left">
                    <div class="file-badge-icon">
                        <i class="fa-solid ${iconClass}"></i>
                    </div>
                    <div class="file-title-wrap">
                        <span class="file-primary-name" title="${f.name}">${f.name}</span>
                        <span class="file-target-rename"><i class="fa-solid fa-arrow-right"></i> Target: <code>${folderPart}/1${ext}</code> (Sequential)</span>
                    </div>
                </div>
                <span class="file-size-tag">${f.size_mb} MB</span>
            `;

            row.addEventListener('click', () => {
                selectedFile = f;
                document.querySelectorAll('.file-row').forEach(el => el.classList.remove('selected'));
                row.classList.add('selected');
                selectionSummary.innerHTML = `<i class="fa-solid fa-circle-check text-cyan"></i><span>Selected: ${f.name} (${f.size_mb} MB)</span>`;
                btnProcessSelected.disabled = isProcessing;
            });

            filesList.appendChild(row);
        });

        if (!selectedFile && files.length > 0) {
            selectedFile = files[0];
            const firstRow = filesList.firstElementChild;
            if (firstRow) firstRow.classList.add('selected');
            selectionSummary.innerHTML = `<i class="fa-solid fa-circle-check text-cyan"></i><span>Selected: ${selectedFile.name} (${selectedFile.size_mb} MB)</span>`;
            btnProcessSelected.disabled = isProcessing;
        }
    }

    async function startProcessing(targets) {
        try {
            const res = await fetch('/api/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ files: targets, platform: currentPlatform })
            });
            const data = await res.json();
            if (res.ok) {
                showToast('🚀 Analysis started via Gemini AI!');
            } else {
                showToast(`❌ ${data.error || 'Failed to start'}`);
            }
        } catch (err) {
            showToast('❌ Communication error with engine');
        }
    }

    async function stopProcessing() {
        try {
            btnStop.disabled = true;
            btnStop.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Stopping...</span>';
            await fetch('/api/stop', { method: 'POST' });
            showToast('🛑 Stop signal dispatched. Halting after current step...');
        } catch (err) {
            showToast('❌ Failed to request stop');
        }
    }

    async function pollStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();

            isProcessing = data.is_processing;

            // Visualizer pulse
            if (aiVisualizer) {
                if (isProcessing) aiVisualizer.classList.add('active');
                else aiVisualizer.classList.remove('active');
            }

            // Update UI Button states
            btnProcessAll.disabled = isProcessing || files.length === 0;
            btnProcessSelected.disabled = isProcessing || !selectedFile;
            btnStop.disabled = !isProcessing || data.stop_requested;
            if (!isProcessing) {
                btnStop.innerHTML = '<i class="fa-solid fa-hand"></i> <span>Stop Analysis</span>';
            }

            // Status Badge
            if (isProcessing) {
                if (data.stop_requested) {
                    statusBadge.textContent = 'STOPPING';
                    statusBadge.className = 'status-badge stopping';
                } else {
                    statusBadge.textContent = 'ANALYZING';
                    statusBadge.className = 'status-badge analyzing';
                }
            } else {
                statusBadge.textContent = 'IDLE';
                statusBadge.className = 'status-badge';
            }

            // Progress Rail
            const current = data.progress_current || 0;
            const total = data.progress_total || 0;
            processedCount = current;
            if (statProcessedCount) statProcessedCount.textContent = processedCount;

            const percent = total > 0 ? Math.round((current / total) * 100) : 0;
            progressBarFill.style.width = `${percent}%`;
            progressCounter.textContent = `${current} / ${total}`;

            if (isProcessing) {
                progressCurrentStatus.textContent = data.current_file 
                    ? `Watching & analyzing: ${data.current_file}` 
                    : 'Attaching video to Gemini Cloud...';
            } else {
                progressCurrentStatus.textContent = 'Ready for video analysis.';
            }

            // Update Console Logs
            if (data.logs && data.logs.length > 0) {
                const lines = data.logs.map(l => {
                    let cls = 'log-line';
                    if (l.message.includes('Error') || l.message.includes('Failed')) cls += ' error';
                    else if (l.message.includes('✅') || l.message.includes('Success')) cls += ' success';
                    else if (l.message.includes('Gemini') || l.message.includes('Processing')) cls += ' system';
                    return `<div class="${cls}">[${l.time}] ${escapeHtml(l.message)}</div>`;
                }).join('');

                if (terminalLogBox.innerHTML !== lines) {
                    terminalLogBox.innerHTML = lines;
                    terminalLogBox.scrollTop = terminalLogBox.scrollHeight;
                }
            }

            // Update Structured Showcase Output
            if (data.latest_result && data.latest_result.content) {
                parseAndDisplayResult(data.latest_result.content);
            }

        } catch (err) {
            // Ignore polling transient errors
        }
    }

    function parseAndDisplayResult(raw) {
        resultContent.textContent = raw;

        const hasHookHeader = /🎯\s*HOOK:?/i.test(raw);
        const hasCaptionHeader = /📌\s*CAPTION:?/i.test(raw);
        const hasTagsHeader = /🏷️\s*HASHTAGS:?/i.test(raw);

        let hookText = "";
        let captionText = "";
        let tagsText = "";

        if (hasHookHeader || hasCaptionHeader || hasTagsHeader) {
            const hookMatch = raw.match(/🎯\s*HOOK:?\s*([\s\S]*?)(?=📌\s*CAPTION|$)/i);
            if (hookMatch) hookText = hookMatch[1].trim();

            const captionMatch = raw.match(/📌\s*CAPTION:?\s*([\s\S]*?)(?=🏷️\s*HASHTAGS|$)/i);
            if (captionMatch) captionText = captionMatch[1].trim();

            const tagsMatch = raw.match(/🏷️\s*HASHTAGS:?\s*([\s\S]*?)$/i);
            if (tagsMatch) tagsText = tagsMatch[1].trim();
        } else {
            // Clean format: Story caption followed by hashtags
            const firstTagIdx = raw.search(/#[\w\u0080-\uFFFF]+/);
            if (firstTagIdx !== -1) {
                captionText = raw.substring(0, firstTagIdx).trim();
                tagsText = raw.substring(firstTagIdx).trim();
            } else {
                captionText = raw.trim();
            }
        }

        const hookCard = document.querySelector('.hook-card');
        if (hookText && hookDisplay) {
            hookDisplay.textContent = hookText;
            if (hookCard) hookCard.style.display = 'block';
        } else {
            if (hookCard) hookCard.style.display = 'none';
        }

        if (captionDisplay) {
            captionDisplay.textContent = captionText || raw;
            // Update stats badge
            if (captionStatsBadge && captionText) {
                const chars = captionText.length;
                const words = captionText.trim().split(/\s+/).filter(Boolean).length;
                captionStatsBadge.textContent = `${chars} chars • ${words} words`;
            }
        }

        if (tagsText && tagsDisplay) {
            const tagList = tagsText.match(/#[\w\u0080-\uFFFF]+/g) || [];
            if (tagsCountBadge) {
                tagsCountBadge.textContent = `${tagList.length} hashtags`;
            }

            if (tagList.length > 0) {
                tagsDisplay.innerHTML = tagList.map(t => `<span class="tag-chip" title="Click to copy">${escapeHtml(t)}</span>`).join('');
                // Add click-to-copy on chips
                tagsDisplay.querySelectorAll('.tag-chip').forEach(c => {
                    c.addEventListener('click', () => {
                        navigator.clipboard.writeText(c.textContent);
                        const origText = c.textContent;
                        c.textContent = 'Copied! ✨';
                        setTimeout(() => c.textContent = origText, 1500);
                        showToast(`Copied ${origText}`);
                    });
                });
            } else {
                tagsDisplay.textContent = tagsText;
            }
        } else if (tagsDisplay) {
            tagsDisplay.innerHTML = '';
        }

        // Update Mobile Simulator
        if (simCaptionBody) {
            simCaptionBody.innerHTML = escapeHtml(raw).replace(/(#[\w\u0080-\uFFFF]+)/g, '<span style="color:#38bdf8; font-weight:700;">$1</span>');
        }
        if (simVideoLabel && selectedFile) {
            simVideoLabel.textContent = selectedFile.name;
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Event Handlers
    btnRefreshFiles.addEventListener('click', () => {
        loadFiles();
        showToast('🔄 Media queue refreshed');
    });

    btnClearConsole.addEventListener('click', () => {
        terminalLogBox.innerHTML = '<div class="log-line system">[CONSOLE] Cleared.</div>';
    });

    btnProcessAll.addEventListener('click', () => {
        if (files.length === 0) return;
        const allPaths = files.map(f => f.rel_path);
        startProcessing(allPaths);
    });

    btnProcessSelected.addEventListener('click', () => {
        if (!selectedFile) return;
        startProcessing([selectedFile.rel_path]);
    });

    btnStop.addEventListener('click', stopProcessing);

    btnOpenInputFolder.addEventListener('click', async () => {
        await fetch('/api/open_input', { method: 'POST' });
    });

    btnOpenOutputFolder.addEventListener('click', async () => {
        await fetch('/api/open_output', { method: 'POST' });
    });

    // Copy Handlers
    btnCopyResult.addEventListener('click', () => {
        const text = resultContent.textContent;
        if (!text) return;
        navigator.clipboard.writeText(text).then(() => {
            triggerCopyFeedback(btnCopyResult, '<i class="fa-regular fa-clone"></i> <span>Copy All</span>', 'Copied! ✨');
            showToast('📋 Caption & Hashtags copied directly!');
        });
    });

    if (btnCopyHook) {
        btnCopyHook.addEventListener('click', () => {
            const text = hookDisplay.textContent.trim();
            if (!text || text.includes('Awaiting')) return;
            navigator.clipboard.writeText(text).then(() => {
                triggerCopyFeedback(btnCopyHook, '<i class="fa-regular fa-copy"></i>');
                showToast('🎯 Hook copied to clipboard!');
            });
        });
    }

    if (btnCopyCaption) {
        btnCopyCaption.addEventListener('click', () => {
            const text = captionDisplay.textContent.trim();
            if (!text || text.includes('Story-driven')) return;
            navigator.clipboard.writeText(text).then(() => {
                triggerCopyFeedback(btnCopyCaption, '<i class="fa-regular fa-copy"></i> <span>Copy Caption</span>', 'Copied! ✨');
                showToast('📌 Caption copied to clipboard!');
            });
        });
    }

    if (btnCopyTags) {
        btnCopyTags.addEventListener('click', () => {
            const tags = Array.from(tagsDisplay.querySelectorAll('.tag-chip')).map(t => t.textContent).join(' ');
            if (!tags) return;
            navigator.clipboard.writeText(tags).then(() => {
                triggerCopyFeedback(btnCopyTags, '<i class="fa-regular fa-copy"></i> <span>Copy All Tags</span>', 'Copied! ✨');
                showToast('🏷️ Hashtags copied to clipboard!');
            });
        });
    }

    // =========================================================================
    // Clear Handlers
    // =========================================================================

    // Master Clear Result: Clears whole AI Social Media Package (Caption & Hashtags)
    if (btnClearResult) {
        btnClearResult.addEventListener('click', async () => {
            try {
                await fetch('/api/clear_result', { method: 'POST' });
            } catch (e) {}

            resultContent.textContent = '';
            if (captionDisplay) {
                captionDisplay.textContent = 'Story-driven caption in fluent English with context & emojis will appear here after analysis...';
            }
            if (captionStatsBadge) {
                captionStatsBadge.textContent = '0 chars • 0 words';
            }
            if (tagsDisplay) {
                tagsDisplay.innerHTML = '';
            }
            if (tagsCountBadge) {
                tagsCountBadge.textContent = '0 hashtags';
            }
            if (hookDisplay) {
                hookDisplay.textContent = 'Awaiting video analysis...';
            }
            const hookCard = document.querySelector('.hook-card');
            if (hookCard) hookCard.style.display = 'none';

            if (simCaptionBody) {
                simCaptionBody.innerHTML = 'Your caption and hashtags will preview here in real mobile social feed format!';
            }

            showToast('🧹 Caption & Hashtags cleared!');
        });
    }

    // Clear Caption Box only
    if (btnClearCaption) {
        btnClearCaption.addEventListener('click', () => {
            if (captionDisplay) {
                captionDisplay.textContent = '';
            }
            if (captionStatsBadge) {
                captionStatsBadge.textContent = '0 chars • 0 words';
            }
            showToast('🧹 Caption cleared!');
        });
    }

    // Clear Hashtags Box only
    if (btnClearTags) {
        btnClearTags.addEventListener('click', () => {
            if (tagsDisplay) {
                tagsDisplay.innerHTML = '';
            }
            if (tagsCountBadge) {
                tagsCountBadge.textContent = '0 hashtags';
            }
            showToast('🧹 Hashtags cleared!');
        });
    }

    // Clear Execution Logs Console
    if (btnClearConsole) {
        btnClearConsole.addEventListener('click', async () => {
            try {
                await fetch('/api/clear_logs', { method: 'POST' });
            } catch (e) {}
            if (terminalLogBox) {
                terminalLogBox.innerHTML = '<div class="log-line system">[00:00:00] Console logs cleared.</div>';
            }
            showToast('🧹 Execution log cleared!');
        });
    }

    // Live update stats if user types or edits caption directly in contenteditable
    if (captionDisplay) {
        captionDisplay.addEventListener('input', () => {
            const text = captionDisplay.textContent.trim();
            if (captionStatsBadge) {
                const chars = text.length;
                const words = text ? text.split(/\s+/).filter(Boolean).length : 0;
                captionStatsBadge.textContent = `${chars} chars • ${words} words`;
            }
            // Keep simulated mobile feed in sync with manual edits
            if (simCaptionBody) {
                simCaptionBody.innerHTML = escapeHtml(text).replace(/(#[\w\u0080-\uFFFF]+)/g, '<span style="color:#38bdf8; font-weight:700;">$1</span>');
            }
        });
    }

    // Studio Pro Menu Toggle & Interactions
    if (btnStudioProBadge && studioProMenu) {
        btnStudioProBadge.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = studioProMenu.classList.toggle('show');
            if (studioProContainer) studioProContainer.classList.toggle('open', isOpen);
        });

        document.addEventListener('click', (e) => {
            if (studioProContainer && !studioProContainer.contains(e.target)) {
                studioProMenu.classList.remove('show');
                studioProContainer.classList.remove('open');
            }
        });
    }

    if (btnStudioMenuUpdate) {
        btnStudioMenuUpdate.addEventListener('click', () => {
            if (studioProMenu) studioProMenu.classList.remove('show');
            if (studioProContainer) studioProContainer.classList.remove('open');
            if (btnOpenSettings) btnOpenSettings.click();
            if (tabSettingsUpdater) tabSettingsUpdater.click();
        });
    }

    // Settings Modal
    btnOpenSettings.addEventListener('click', async () => {
        if (studioProMenu) studioProMenu.classList.remove('show');
        if (studioProContainer) studioProContainer.classList.remove('open');
        if (tabSettingsApi) tabSettingsApi.click();
        try {
            const res = await fetch('/api/config');
            const cfg = await res.json();
            inputApiKey.value = cfg.gemini_api_key || '';
            settingsModal.classList.add('show');
            settingsModal.classList.add('active');
        } catch (err) {
            settingsModal.classList.add('show');
            settingsModal.classList.add('active');
        }
    });

    btnCloseSettings.addEventListener('click', () => {
        settingsModal.classList.remove('show');
        settingsModal.classList.remove('active');
    });

    btnSaveApiKey.addEventListener('click', async () => {
        const key = inputApiKey.value.trim();
        try {
            await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ gemini_api_key: key })
            });
            showToast('✅ Gemini API Key connected & saved!');
            settingsModal.classList.remove('show');
            settingsModal.classList.remove('active');
        } catch (err) {
            showToast('❌ Failed to save key');
        }
    });

    // =========================================================================
    // Git Auto-Updater Controller
    // =========================================================================

    // Settings Modal Tab Switcher (API Key vs Auto-Updater)
    if (tabSettingsApi && tabSettingsUpdater) {
        tabSettingsApi.addEventListener('click', () => {
            tabSettingsApi.classList.add('active');
            tabSettingsUpdater.classList.remove('active');
            if (paneSettingsApi) paneSettingsApi.classList.add('active');
            if (paneSettingsUpdater) paneSettingsUpdater.classList.remove('active');
        });

        tabSettingsUpdater.addEventListener('click', () => {
            tabSettingsUpdater.classList.add('active');
            tabSettingsApi.classList.remove('active');
            if (paneSettingsUpdater) paneSettingsUpdater.classList.add('active');
            if (paneSettingsApi) paneSettingsApi.classList.remove('active');
            checkAppUpdates(false);
        });
    }

    async function checkAppUpdates(isManual = false) {
        if (btnCheckUpdateModal) {
            btnCheckUpdateModal.disabled = true;
            btnCheckUpdateModal.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Checking...</span>';
        }

        try {
            const res = await fetch('/api/check_update', { method: 'POST' });
            const data = await res.json();

            if (modalVersionBadge && data.current_version) {
                modalVersionBadge.textContent = `v${data.current_version} (${data.current_commit || 'Stable'})`;
            }

            if (modalGitStatus) {
                if (!data.is_git) {
                    modalGitStatus.textContent = 'Not a Git repo';
                    modalGitStatus.className = 'updater-badge git';
                } else {
                    modalGitStatus.textContent = `${data.branch} (${data.current_commit})`;
                    modalGitStatus.className = 'updater-badge git';
                }
            }

            if (inputGitRemote && data.remote_url) {
                inputGitRemote.value = data.remote_url;
            }

            if (data.update_available) {
                const count = data.behind_count || 1;
                if (btnStudioProBadge) btnStudioProBadge.classList.add('has-update');
                if (studioProVersionText) studioProVersionText.textContent = `Update (${count})`;
                if (spUpdateHint) spUpdateHint.textContent = `🚀 ${count} new update(s) ready!`;
                if (spBadgeUpdate) spBadgeUpdate.style.display = 'inline-block';
                if (spMenuUpdateDesc) spMenuUpdateDesc.textContent = `${count} commit(s) ready to pull`;

                if (versionUpdaterPill) versionUpdaterPill.classList.add('update-ready');
                if (versionLabel) versionLabel.textContent = `🚀 Update (${count})`;
                if (btnQuickUpdate) btnQuickUpdate.style.display = 'inline-flex';
                if (tabUpdateDot) tabUpdateDot.style.display = 'inline-block';

                if (modalUpdateStatus) {
                    modalUpdateStatus.textContent = `${count} commit(s) ready to pull!`;
                    modalUpdateStatus.className = 'updater-badge status update-available';
                }

                if (btnPerformUpdate) {
                    btnPerformUpdate.disabled = false;
                    btnPerformUpdate.innerHTML = `<i class="fa-solid fa-cloud-arrow-down"></i> <span>Update Now (${count} commits)</span>`;
                }

                if (data.commits && data.commits.length > 0 && commitsListBox && updateLogArea) {
                    commitsListBox.innerHTML = data.commits.map(c => `<div class="commit-entry"><i class="fa-solid fa-code-commit text-cyan"></i> ${escapeHtml(c)}</div>`).join('');
                    updateLogArea.style.display = 'flex';
                }

                if (isManual) {
                    showToast(`🚀 ${count} new update(s) found! Click 'Update Now' to apply.`);
                }
            } else {
                if (btnStudioProBadge) btnStudioProBadge.classList.remove('has-update');
                if (studioProVersionText) studioProVersionText.textContent = `v${data.current_version || '2.4.0'}`;
                if (spMenuVersionBadge) spMenuVersionBadge.textContent = `v${data.current_version || '2.4.0'}`;
                if (spUpdateHint) spUpdateHint.textContent = '✅ Latest build installed';
                if (spBadgeUpdate) spBadgeUpdate.style.display = 'none';
                if (spMenuUpdateDesc) spMenuUpdateDesc.textContent = 'Check & pull latest updates';

                if (versionUpdaterPill) versionUpdaterPill.classList.remove('update-ready');
                if (versionLabel) versionLabel.textContent = `v${data.current_version || '2.4.0'}`;
                if (btnQuickUpdate) btnQuickUpdate.style.display = 'none';
                if (tabUpdateDot) tabUpdateDot.style.display = 'none';

                if (modalUpdateStatus) {
                    modalUpdateStatus.textContent = data.message || 'Application is up to date';
                    modalUpdateStatus.className = 'updater-badge status';
                }

                if (btnPerformUpdate) {
                    btnPerformUpdate.disabled = true;
                    btnPerformUpdate.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> <span>Update Now (Git Pull)</span>';
                }

                if (updateLogArea) updateLogArea.style.display = 'none';

                if (isManual) {
                    showToast('✅ Application is up to date!');
                }
            }
        } catch (err) {
            if (modalUpdateStatus) {
                modalUpdateStatus.textContent = 'Check failed';
            }
            if (isManual) showToast('❌ Failed to check for updates');
        } finally {
            if (btnCheckUpdateModal) {
                btnCheckUpdateModal.disabled = false;
                btnCheckUpdateModal.innerHTML = '<i class="fa-solid fa-rotate"></i> <span>Check for Updates</span>';
            }
        }
    }

    async function executeGitUpdate() {
        if (!confirm('Proceed with automatic Git Pull update? The application will update and reload.')) return;

        if (btnPerformUpdate) {
            btnPerformUpdate.disabled = true;
            btnPerformUpdate.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Updating...</span>';
        }
        if (btnQuickUpdate) {
            btnQuickUpdate.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Updating...</span>';
        }

        try {
            const res = await fetch('/api/perform_update', { method: 'POST' });
            const data = await res.json();

            if (data.ok) {
                showToast(`🎉 ${data.message} Reloading...`);
                setTimeout(() => {
                    location.reload();
                }, 1800);
            } else {
                showToast(`❌ Update error: ${data.error}`);
                if (btnPerformUpdate) {
                    btnPerformUpdate.disabled = false;
                    btnPerformUpdate.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> <span>Retry Update</span>';
                }
            }
        } catch (e) {
            showToast('❌ Update request failed. Check server.');
        }
    }

    if (btnCheckUpdateModal) {
        btnCheckUpdateModal.addEventListener('click', () => checkAppUpdates(true));
    }

    if (btnPerformUpdate) {
        btnPerformUpdate.addEventListener('click', executeGitUpdate);
    }

    if (btnQuickUpdate) {
        btnQuickUpdate.addEventListener('click', (e) => {
            e.stopPropagation();
            executeGitUpdate();
        });
    }

    if (versionUpdaterPill) {
        versionUpdaterPill.addEventListener('click', () => {
            if (btnOpenSettings) btnOpenSettings.click();
            if (tabSettingsUpdater) tabSettingsUpdater.click();
        });
    }

    if (btnConnectGit && inputGitRemote) {
        btnConnectGit.addEventListener('click', async () => {
            const url = inputGitRemote.value.trim();
            if (!url) {
                showToast('Please enter a Git Remote URL');
                return;
            }
            try {
                btnConnectGit.disabled = true;
                btnConnectGit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Linking...';
                const res = await fetch('/api/configure_git', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ remote_url: url, branch: 'main' })
                });
                const data = await res.json();
                if (data.ok) {
                    showToast('✅ Git Remote linked successfully!');
                    checkAppUpdates(true);
                } else {
                    showToast(`❌ Link failed: ${data.error}`);
                }
            } catch (err) {
                showToast('❌ Failed to link remote');
            } finally {
                btnConnectGit.disabled = false;
                btnConnectGit.innerHTML = '<i class="fa-solid fa-link"></i> Link';
            }
        });
    }

    // =========================================================================
    // Drag & Drop & Folder Traversal Uploader Engine
    // =========================================================================

    // Recursive directory reader for webkitGetAsEntry
    async function getFilesFromDataTransfer(items) {
        const fileEntries = [];

        async function traverseEntry(entry, path = '') {
            if (entry.isFile) {
                try {
                    const file = await new Promise((resolve, reject) => entry.file(resolve, reject));
                    const relPath = path ? `${path}/${file.name}` : file.name;
                    fileEntries.push({ file, relPath });
                } catch (e) {
                    console.error('Failed reading file entry', entry, e);
                }
            } else if (entry.isDirectory) {
                const dirReader = entry.createReader();
                const readAllEntries = async () => {
                    let all = [];
                    while (true) {
                        const batch = await new Promise((resolve, reject) => dirReader.readEntries(resolve, reject));
                        if (!batch || batch.length === 0) break;
                        all = all.concat(batch);
                    }
                    return all;
                };

                try {
                    const entries = await readAllEntries();
                    const nextPath = path ? `${path}/${entry.name}` : entry.name;
                    for (const childEntry of entries) {
                        await traverseEntry(childEntry, nextPath);
                    }
                } catch (e) {
                    console.error('Failed reading directory entry', entry, e);
                }
            }
        }

        const promises = [];
        for (let i = 0; i < items.length; i++) {
            const item = items[i];
            if (item.webkitGetAsEntry) {
                const entry = item.webkitGetAsEntry();
                if (entry) {
                    promises.push(traverseEntry(entry));
                }
            } else if (item.getAsFile) {
                const f = item.getAsFile();
                if (f) fileEntries.push({ file: f, relPath: f.name });
            }
        }

        await Promise.all(promises);
        return fileEntries;
    }

    function getFilesFromInput(inputElement) {
        const fileEntries = [];
        const fileList = inputElement.files || [];
        for (let i = 0; i < fileList.length; i++) {
            const file = fileList[i];
            const relPath = file.webkitRelativePath || file.name;
            fileEntries.push({ file, relPath });
        }
        return fileEntries;
    }

    async function uploadFilesBatch(fileEntries) {
        const mediaExts = ['.mp4', '.mov', '.mkv', '.avi', '.webm', '.m4v', '.jpg', '.jpeg', '.png', '.webp'];
        const validMedia = fileEntries.filter(item => {
            const name = item.file.name.toLowerCase();
            return mediaExts.some(ext => name.endsWith(ext));
        });

        if (validMedia.length === 0) {
            showToast('⚠️ No video or image files found in dropped items!');
            return;
        }

        if (uploadModal) uploadModal.classList.add('show', 'active');
        let uploadedCount = 0;

        for (let i = 0; i < validMedia.length; i++) {
            const item = validMedia[i];
            if (uploadFileName) uploadFileName.textContent = item.relPath;
            if (uploadCountBadge) uploadCountBadge.textContent = `${i + 1} / ${validMedia.length}`;
            if (uploadBarFill) uploadBarFill.style.width = `${Math.round(((i) / validMedia.length) * 100)}%`;

            try {
                await fetch('/api/upload', {
                    method: 'POST',
                    headers: {
                        'X-Relative-Path': encodeURIComponent(item.relPath),
                        'X-File-Name': encodeURIComponent(item.file.name),
                        'Content-Type': 'application/octet-stream'
                    },
                    body: item.file
                });
                uploadedCount++;
            } catch (err) {
                console.error('Upload failed for', item.relPath, err);
            }

            if (uploadBarFill) uploadBarFill.style.width = `${Math.round(((i + 1) / validMedia.length) * 100)}%`;
        }

        setTimeout(() => {
            if (uploadModal) uploadModal.classList.remove('show', 'active');
            if (uploadBarFill) uploadBarFill.style.width = '0%';
            loadFiles();
            showToast(`✨ Uploaded ${uploadedCount} file(s) into Queue!`);
        }, 500);
    }

    // Window Drag & Drop Listeners
    let dragCounter = 0;

    window.addEventListener('dragenter', (e) => {
        e.preventDefault();
        dragCounter++;
        if (e.dataTransfer && e.dataTransfer.types) {
            const hasFiles = Array.from(e.dataTransfer.types).some(t => t === 'Files' || t === 'public.file-url');
            if (hasFiles && dropOverlay) {
                dropOverlay.classList.add('active');
            }
        }
    });

    window.addEventListener('dragover', (e) => {
        e.preventDefault();
        if (e.dataTransfer) {
            e.dataTransfer.dropEffect = 'copy';
        }
        if (dropOverlay && !dropOverlay.classList.contains('active')) {
            dropOverlay.classList.add('active');
        }
    });

    window.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dragCounter--;
        if (dragCounter <= 0) {
            dragCounter = 0;
            if (dropOverlay) dropOverlay.classList.remove('active');
        }
    });

    window.addEventListener('drop', async (e) => {
        e.preventDefault();
        dragCounter = 0;
        if (dropOverlay) dropOverlay.classList.remove('active');

        if (!e.dataTransfer) return;

        if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
            const entries = await getFilesFromDataTransfer(e.dataTransfer.items);
            if (entries.length > 0) {
                await uploadFilesBatch(entries);
            }
        } else if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const entries = Array.from(e.dataTransfer.files).map(f => ({ file: f, relPath: f.name }));
            await uploadFilesBatch(entries);
        }
    });

    // File / Folder Picker Fallback Buttons
    if (btnAddFiles && filePickerInput) {
        btnAddFiles.addEventListener('click', () => filePickerInput.click());
    }
    if (btnEmptyAddFiles && filePickerInput) {
        btnEmptyAddFiles.addEventListener('click', () => filePickerInput.click());
    }
    if (btnAddFolder && folderPickerInput) {
        btnAddFolder.addEventListener('click', () => folderPickerInput.click());
    }
    if (btnEmptyAddFolder && folderPickerInput) {
        btnEmptyAddFolder.addEventListener('click', () => folderPickerInput.click());
    }

    if (filePickerInput) {
        filePickerInput.addEventListener('change', async () => {
            if (filePickerInput.files && filePickerInput.files.length > 0) {
                const entries = getFilesFromInput(filePickerInput);
                await uploadFilesBatch(entries);
                filePickerInput.value = '';
            }
        });
    }

    if (folderPickerInput) {
        folderPickerInput.addEventListener('change', async () => {
            if (folderPickerInput.files && folderPickerInput.files.length > 0) {
                const entries = getFilesFromInput(folderPickerInput);
                await uploadFilesBatch(entries);
                folderPickerInput.value = '';
            }
        });
    }

    // Initial Load & Loop
    loadFiles();
    checkAppUpdates(false);
    pollStatus();
    setInterval(pollStatus, 1000);
});

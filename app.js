// Content Separator & Online Live SEO Studio Engine
document.addEventListener('DOMContentLoaded', () => {
    // --- State & References ---
    let processedResults = [];
    let savedApiKey = localStorage.getItem('gemini_api_key') || '';

    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const aiSettingsBtn = document.getElementById('aiSettingsBtn');
    const aiModal = document.getElementById('aiModal');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const saveApiKeyBtn = document.getElementById('saveApiKeyBtn');
    const geminiApiKeyInput = document.getElementById('geminiApiKeyInput');
    const engineStatusTag = document.getElementById('engineStatusTag');

    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // Config elements
    const platformSelect = document.getElementById('platformSelect');
    const nicheSelect = document.getElementById('nicheSelect');
    const toneSelect = document.getElementById('toneSelect');
    const langSelect = document.getElementById('langSelect');
    
    // Tab 0 Elements (Gemini AI Copy-Paste)
    const geminiPasteInput = document.getElementById('geminiPasteInput');
    const copyGeminiPromptBtn = document.getElementById('copyGeminiPromptBtn');
    const pasteGeminiClipBtn = document.getElementById('pasteGeminiClipBtn');
    const clearGeminiPasteBtn = document.getElementById('clearGeminiPasteBtn');
    const processGeminiPasteBtn = document.getElementById('processGeminiPasteBtn');

    // Tab 1 Elements
    const bulkInput = document.getElementById('bulkInput');
    const delimiterSelect = document.getElementById('delimiterSelect');
    const processBulkBtn = document.getElementById('processBulkBtn');
    const clearBulkBtn = document.getElementById('clearBulkBtn');
    const uploadFileBtn = document.getElementById('uploadFileBtn');
    const txtFileInput = document.getElementById('txtFileInput');
    const uploadedFileName = document.getElementById('uploadedFileName');
    const dragOverlay = document.getElementById('dragOverlay');

    // Tab 2 Elements
    const singleTitle = document.getElementById('singleTitle');
    const singleNotes = document.getElementById('singleNotes');
    const singleKeywords = document.getElementById('singleKeywords');
    const singleCta = document.getElementById('singleCta');
    const processSingleBtn = document.getElementById('processSingleBtn');

    // Tab 3 Elements
    const cleanerInput = document.getElementById('cleanerInput');
    const processCleanBtn = document.getElementById('processCleanBtn');
    const clearCleanBtn = document.getElementById('clearCleanBtn');

    // Loading & Output Elements
    const loadingIndicator = document.getElementById('loadingIndicator');
    const loadingStepTitle = document.getElementById('loadingStepTitle');
    const loadingStepDesc = document.getElementById('loadingStepDesc');
    const outputSection = document.getElementById('outputSection');
    const resultsCountBadge = document.getElementById('resultsCountBadge');
    const cardsGrid = document.getElementById('cardsGrid');
    const copyAllOutputBtn = document.getElementById('copyAllOutputBtn');
    const downloadZipBtn = document.getElementById('downloadZipBtn');
    const downloadCombinedTxtBtn = document.getElementById('downloadCombinedTxtBtn');

    // Toast Container
    const toastContainer = document.getElementById('toastContainer');

    // Initialize API Key input if present
    if (savedApiKey) {
        geminiApiKeyInput.value = savedApiKey;
        updateEngineBadge(true);
    }

    function updateEngineBadge(hasKey) {
        if (hasKey) {
            engineStatusTag.innerHTML = `<span class="badge-online"><i class="fa-solid fa-bolt"></i> Gemini AI Online Active</span>`;
        } else {
            engineStatusTag.innerHTML = `<span class="badge-online"><i class="fa-solid fa-wifi"></i> Live Search Trends Active</span>`;
        }
    }

    // --- Modal Handlers ---
    aiSettingsBtn.addEventListener('click', () => {
        aiModal.classList.remove('hidden');
    });

    closeModalBtn.addEventListener('click', () => {
        aiModal.classList.add('hidden');
    });

    saveApiKeyBtn.addEventListener('click', () => {
        savedApiKey = geminiApiKeyInput.value.trim();
        localStorage.setItem('gemini_api_key', savedApiKey);
        updateEngineBadge(!!savedApiKey);
        aiModal.classList.add('hidden');
        showToast(savedApiKey ? 'Gemini AI Key सुरक्षित भयो!' : 'Default Live Suggest Engine मा सेट भयो!', 'success');
    });

    // --- Hashtag & Base Database ---
    const HASHTAG_BANK = {
        general: [
            "#fyp", "#viral", "#trending", "#foryou", "#foryoupage", "#viralvideo", 
            "#contentcreator", "#explorepage", "#shorts", "#reels", "#tiktok"
        ],
        nepal: [
            "#nepal", "#nepali", "#nepaltiktok", "#nepalmuser", "#kathmandu", 
            "#nepalireels", "#nepalitrending", "#nepalivideo", "#nepalicreator"
        ],
        tech: [
            "#tech", "#technology", "#aitools", "#mobiletech", "#softwarereview", 
            "#gadgets", "#techhacks", "#techtips", "#coding", "#technepal", "#ai"
        ],
        business: [
            "#business", "#money", "#finance", "#entrepreneur", "#sidehustle", 
            "#investing", "#businessideas", "#success", "#mindset", "#nepalbusiness"
        ],
        motivation: [
            "#motivation", "#quotes", "#inspiration", "#lifetips", "#mindset", 
            "#successquotes", "#positivity", "#motivationalvideo", "#nepaliyt", "#lifehacks"
        ],
        vlog: [
            "#vlog", "#dailyvlog", "#travel", "#minivlog", "#lifestyle", 
            "#travelvlog", "#vlogger", "#nepalivlog", "#explore", "#dayinmylife"
        ],
        education: [
            "#education", "#learning", "#gk", "#knowledge", "#facts", 
            "#studyhacks", "#studentlife", "#nepaleducation", "#didyouknow", "#learnontiktok"
        ],
        entertainment: [
            "#funny", "#comedy", "#entertainment", "#fun", "#jokes", 
            "#nepalicomedy", "#memes", "#relatable", "#laughter", "#viralreels"
        ],
        fitness: [
            "#fitness", "#gym", "#workout", "#health", "#diet", 
            "#fitnesstips", "#bodybuilding", "#nepalfitness", "#healthy", "#motivation"
        ]
    };

    const CTA_TEMPLATES = {
        viral: [
            "⚡ मन पर्यो भने Like र Share गर्न नबिर्सनुहोस्!",
            "🔥 साथीहरूलाई पनि यो भिडियो Tag / Share गरिदिनुहोस्!",
            "📌 पछिको लागि Save गरी राख्नुहोस्!"
        ],
        informative: [
            "💡 थप यस्तै उपयोगी भिडियोका लागि Follow/Subscribe गर्नुहोस्!",
            "💬 तपाईंको विचार के छ? कमेन्टमा लेख्नुहोस्!",
            "🔖 भिडियो उपयोगी लागेमा Save गर्नुहोस्!"
        ],
        story: [
            "📖 यस्तै नयाँ कथाहरू र भिडियोका लागि जोडिनुहोस्!",
            "💬 तपाईंलाई कुन कुरा मन पर्यो कमेन्ट गर्नुहोस्!",
            "❤️ भिडियो हेरिदिनुभएकोमा धन्यवाद!"
        ],
        professional: [
            "💼 Follow for more valuable business & tech insights!",
            "📥 Save this post for future reference.",
            "💬 Share your thoughts in the comments below."
        ]
    };

    // --- Theme Toggle ---
    themeToggleBtn.addEventListener('click', () => {
        document.body.classList.toggle('light-theme');
        document.body.classList.toggle('dark-theme');
        const isLight = document.body.classList.contains('light-theme');
        themeToggleBtn.innerHTML = isLight ? '<i class="fa-solid fa-sun"></i>' : '<i class="fa-solid fa-moon"></i>';
    });

    // --- Tab Switching ---
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });

    // --- Drag & Drop / File Upload ---
    const textareaParent = bulkInput.parentElement;

    textareaParent.addEventListener('dragover', (e) => {
        e.preventDefault();
        dragOverlay.classList.add('drag-active');
    });

    textareaParent.addEventListener('dragleave', () => {
        dragOverlay.classList.remove('drag-active');
    });

    textareaParent.addEventListener('drop', (e) => {
        e.preventDefault();
        dragOverlay.classList.remove('drag-active');
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    uploadFileBtn.addEventListener('click', () => txtFileInput.click());

    txtFileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
            handleFileUpload(e.target.files[0]);
        }
    });

    function handleFileUpload(file) {
        if (!file.name.endsWith('.txt') && !file.name.endsWith('.md')) {
            showToast('कृपया केवल .txt वा .md फाइल मात्र अपलोड गर्नुहोस्!', 'error');
            return;
        }
        const reader = new FileReader();
        reader.onload = (e) => {
            bulkInput.value = e.target.result;
            uploadedFileName.textContent = `📁 ${file.name}`;
            showToast(`फाइल सफलतापुर्वक लोड भयो: ${file.name}`, 'success');
        };
        reader.readAsText(file);
    }

    clearBulkBtn.addEventListener('click', () => {
        bulkInput.value = '';
        uploadedFileName.textContent = '';
        txtFileInput.value = '';
    });

    clearCleanBtn.addEventListener('click', () => {
        cleanerInput.value = '';
    });

    // --- Online Live SEO Suggest Fetcher ---
    async function fetchOnlineLiveSEO(queryTopic) {
        const cleanQuery = queryTopic.replace(/[^\w\s\u0900-\u097F]/g, ' ').trim().slice(0, 50);
        let onlineSuggestions = [];

        try {
            // Fetch online live YouTube & Google suggestions via Datamuse and JSONP/proxied suggest endpoints
            const datamuseUrl = `https://api.datamuse.com/words?ml=${encodeURIComponent(cleanQuery)}&max=10`;
            const res = await fetch(datamuseUrl, { method: 'GET' });
            if (res.ok) {
                const data = await res.json();
                if (Array.isArray(data)) {
                    onlineSuggestions = data.map(item => item.word);
                }
            }
        } catch (err) {
            console.warn('Online live fetch fallback to local semantic extractor:', err);
        }

        return onlineSuggestions;
    }

    // --- Optional Online Gemini API Caller ---
    async function generateWithGeminiOnline(apiKey, promptText) {
        const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`;
        const payload = {
            contents: [{ parts: [{ text: promptText }] }]
        };

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.statusText}`);
        }

        const data = await response.json();
        return data.candidates?.[0]?.content?.parts?.[0]?.text || '';
    }

    // --- Main Process Handlers ---

    // 0. Gemini Copy-Paste Handler
    if (copyGeminiPromptBtn) {
        copyGeminiPromptBtn.addEventListener('click', () => {
            const plat = (platformSelect ? platformSelect.value : 'facebook').toUpperCase();
            const prompt = `Analyze this video and give me an SEO package for ${plat}.

CRITICAL INSTRUCTIONS:
- You must carefully analyze the entire video content: watch the visual actions, listen to all spoken dialogue and audio, read on-screen text, and understand the central message.
- Target Platform: ${plat}
- Language: Engaging blend of conversational Nepali and English
- Emojis and bullet points must be clean, structured, and easy to read.

FORMAT YOUR RESPONSE STRICTLY AS FOLLOWS (DO NOT DEVIATE):
🎯 3 VIRAL ATTENTION HOOKS:
Hook 1 (Curiosity/Secret): [Stops viewers in first 3 seconds]
Hook 2 (Question/Relatable): [Relatable question or challenge]
Hook 3 (Urgent/Bold): [Direct statement]

📌 FULL CAPTION & STORY DESCRIPTION:
[Bespoke storytelling caption for ${plat} explaining the value of this video, key bullet points/highlights, practical tips, and emojis]

💡 SEARCH KEYWORDS (SEO & SEARCH TRENDS):
[8-10 high search volume keywords comma-separated for ${plat}]

📣 CALL TO ACTION (CTA):
[1 compelling call to action to like, comment, share, and follow]

🏷️ CONTENT-SPECIFIC HASHTAGS:
[20 ultra-targeted hashtags: Exact Topic Tags + Niche Tags + Viral ${plat} Tags]`;

            copyToClipboard(prompt);
            showToast('Gemini Prompt क्लिपबोर्डमा Copy भयो! अब gemini.google.com मा गई Paste गर्नुहोस्।', 'success');
        });
    }

    if (pasteGeminiClipBtn) {
        pasteGeminiClipBtn.addEventListener('click', async () => {
            try {
                const text = await navigator.clipboard.readText();
                if (text) {
                    geminiPasteInput.value = text.trim();
                    showToast('क्लिपबोर्डबाट Gemini Output Paste भयो!', 'success');
                } else {
                    showToast('क्लिपबोर्ड खाली छ! पहिले Gemini बाट Copy गर्नुहोस्।', 'error');
                }
            } catch (e) {
                showToast('क्लिपबोर्ड पढ्न सकिएन। सिधै Ctrl+V थिचेर Paste गर्नुहोस्।', 'error');
            }
        });
    }

    if (clearGeminiPasteBtn) {
        clearGeminiPasteBtn.addEventListener('click', () => {
            geminiPasteInput.value = '';
        });
    }

    if (processGeminiPasteBtn) {
        processGeminiPasteBtn.addEventListener('click', () => {
            const rawText = geminiPasteInput.value.trim();
            if (!rawText) {
                showToast('कृपया Gemini बाट आएको Output पहिला पेस्ट गर्नुहोस्!', 'error');
                return;
            }

            let chunks = [];
            if (rawText.includes('---')) {
                chunks = rawText.split('---').map(c => c.trim()).filter(Boolean);
            } else if (/video\s*\d+[:.]?/i.test(rawText)) {
                chunks = rawText.split(/(?:^|\n)(?=video\s*\d+[:.]?)/i).map(c => c.trim()).filter(Boolean);
            } else {
                chunks = [rawText];
            }

            processedResults = [];
            const plat = (platformSelect ? platformSelect.value : 'facebook').toUpperCase();

            chunks.forEach((chunk, idx) => {
                const hookMatch = chunk.match(/(?:🎯|VIRAL ATTENTION HOOKS:?)([\s\S]*?)(?=📌|FULL CAPTION|$)/i);
                const captionMatch = chunk.match(/(?:📌|FULL CAPTION & STORY DESCRIPTION:?)([\s\S]*?)(?=💡|SEARCH KEYWORDS|$)/i);
                const kwMatch = chunk.match(/(?:💡|SEARCH KEYWORDS[^:]*:?)([\s\S]*?)(?=📣|CALL TO ACTION|$)/i);
                const ctaMatch = chunk.match(/(?:📣|CALL TO ACTION[^:]*:?)([\s\S]*?)(?=🏷️|CONTENT-SPECIFIC HASHTAGS|$)/i);
                const hashMatch = chunk.match(/(?:🏷️|CONTENT-SPECIFIC HASHTAGS[^:]*:?)([\s\S]*)$/i);

                const hook = hookMatch ? hookMatch[1].trim() : '🔥 Video Attention Hooks';
                const caption = captionMatch ? captionMatch[1].trim() : chunk;
                const keywords = kwMatch ? kwMatch[1].trim() : extractKeywords(chunk);
                const cta = ctaMatch ? ctaMatch[1].trim() : '🔔 Follow for more updates!';
                const hashtags = hashMatch ? hashMatch[1].trim() : (chunk.match(/#[\w\u0900-\u097F]+/g) || []).join(' ');

                const title = `Gemini SEO Package ${idx + 1}`;
                const formattedTxt = `========================================
SEO DATA SOURCE: [Google Gemini AI (User Pasted)]
TARGET PLATFORM: ${plat}
========================================

${chunk}
========================================`;

                processedResults.push({
                    id: idx + 1,
                    title: title,
                    hook: hook,
                    caption: caption,
                    keywords: keywords,
                    cta: cta,
                    hashtags: hashtags || '#fyp #viral #trending',
                    formattedTxt: formattedTxt,
                    source: 'Gemini AI'
                });
            });

            renderResultCards(processedResults);
            showToast(`🎉 Gemini बाट आएका ${processedResults.length} वटा SEO Packages सफलतापुर्वक तयार भए!`, 'success');
        });
    }

    // 1. Bulk Separator Handler
    processBulkBtn.addEventListener('click', async () => {
        const rawText = bulkInput.value.trim();
        if (!rawText) {
            showToast('कृपया पहिला केही टेक्स्ट वा स्क्रिप्ट पेस्ट गर्नुहोस्!', 'error');
            return;
        }

        const delimiterMode = delimiterSelect.value;
        const rawItems = separateText(rawText, delimiterMode);

        if (rawItems.length === 0) {
            showToast('सामग्री छुट्याउन सकिएन। रिमार्क वा फर्म्याट जाँच्नुहोस्।', 'error');
            return;
        }

        setLoading(true, '🌐 Online SEO Data Fetching...', `कुल ${rawItems.length} वटा भिडियोको लागि Live SEO Keywords र Hashtags खोजिँदैछ...`);

        try {
            processedResults = [];
            for (let i = 0; i < rawItems.length; i++) {
                const item = rawItems[i];
                loadingStepDesc.textContent = `Processing Video ${i + 1}/${rawItems.length}: Live Online Trends & SEO...`;
                const seoObj = await generateSEODataObjectAsync(item, i + 1);
                processedResults.push(seoObj);
            }

            renderResultCards(processedResults);
            showToast(`सफलतापुर्वक ${processedResults.length} वटा भिडियोको Live SEO .txt Package तयार भयो!`, 'success');
        } catch (error) {
            console.error('Error during SEO generation:', error);
            showToast('SEO निर्माण गर्दा केही त्रुटि भयो। स्थानीय डेटाबाट लोड गरिँदैछ...', 'error');
        } finally {
            setLoading(false);
        }
    });

    // 2. Single Video Creator Handler
    processSingleBtn.addEventListener('click', async () => {
        const title = singleTitle.value.trim();
        const notes = singleNotes.value.trim();
        if (!title && !notes) {
            showToast('कृपया भिडियोको शीर्षक वा मुख्य बुँदाहरू भर्नुहोस्!', 'error');
            return;
        }

        const combinedText = `${title}\n${notes}`;
        setLoading(true, '🌐 Online SEO Data Fetching...', 'यस भिडियोको लागि Real-time SEO Trending Keywords र Hashtags खोजिँदैछ...');

        try {
            const seoObj = await generateSEODataObjectAsync(combinedText, 1, {
                customKeywords: singleKeywords.value.trim(),
                customCta: singleCta.value
            });

            processedResults = [seoObj];
            renderResultCards(processedResults);
            showToast('Online SEO क्याप्शन र ह्यासट्याग तैयार भयो!', 'success');
        } catch (error) {
            console.error('Error in single generation:', error);
            showToast('SEO निर्माण गर्दा केही समस्या भयो।', 'error');
        } finally {
            setLoading(false);
        }
    });

    // 3. Cleaner & Splitter Handler
    processCleanBtn.addEventListener('click', () => {
        const raw = cleanerInput.value.trim();
        if (!raw) {
            showToast('सफा गर्नका लागि टेक्स्ट पेस्ट गर्नुहोस्!', 'error');
            return;
        }

        const hashtagsMatch = raw.match(/#[\w🇳🇵अ-ह]+/g) || [];
        const cleanCaption = raw.replace(/#[\w🇳🇵अ-ह]+/g, '').replace(/\s+/g, ' ').trim();

        const seoObj = {
            id: 1,
            title: cleanCaption.substring(0, 60) || "Cleaned Content",
            hook: "📌 Key Highlight",
            caption: cleanCaption,
            keywords: extractKeywords(cleanCaption),
            hashtags: hashtagsMatch.join(' '),
            cta: "💬 Comments मा आफ्नो विचार दिनुहोस्!",
            source: "Online Cleaned",
            formattedTxt: buildFormattedTxtString(
                cleanCaption.substring(0, 60), 
                "📌 Key Highlight", 
                cleanCaption, 
                extractKeywords(cleanCaption), 
                hashtagsMatch.join(' '), 
                "💬 Comments मा आफ्नो विचार दिनुहोस्!",
                "Online Cleaned & Formatted"
            )
        };

        processedResults = [seoObj];
        renderResultCards(processedResults);
        showToast('टेक्स्ट सफलतापुर्वक Clean र Separate गरियो!', 'success');
    });

    function setLoading(isLoading, title = '', desc = '') {
        if (isLoading) {
            loadingStepTitle.textContent = title;
            loadingStepDesc.textContent = desc;
            loadingIndicator.classList.remove('hidden');
            outputSection.classList.add('hidden');
        } else {
            loadingIndicator.classList.add('hidden');
        }
    }

    // --- Parsing / Separating Algorithm ---
    function separateText(text, mode) {
        let items = [];

        if (mode === 'separator' || (mode === 'auto' && text.includes('---'))) {
            items = text.split(/---+/).map(s => s.trim()).filter(Boolean);
        } else if (mode === 'numbered' || (mode === 'auto' && /^\s*\d+[\.\)]/m.test(text))) {
            items = text.split(/(?=\n\s*\d+[\.\)])/).map(s => s.trim()).filter(Boolean);
        } else if (mode === 'videoTag' || (mode === 'auto' && /(video|post)\s*\d+/i.test(text))) {
            items = text.split(/(?=(?:video|post)\s*\d+)/i).map(s => s.trim()).filter(Boolean);
        } else if (mode === 'doubleLine' || (mode === 'auto' && text.includes('\n\n'))) {
            items = text.split(/\n\s*\n/).map(s => s.trim()).filter(Boolean);
        } else {
            items = text.split(/\n+/).map(s => s.trim()).filter(s => s.length > 10);
        }

        if (items.length === 0 && text.length > 0) {
            items = [text];
        }

        return items;
    }

    // --- Asynchronous SEO Generator Core with Online Integration ---
    async function generateSEODataObjectAsync(rawContent, index, options = {}) {
        const lines = rawContent.split('\n').map(l => l.trim()).filter(Boolean);
        let firstLine = lines[0] || `Video Segment ${index}`;

        let title = firstLine.replace(/^(\d+[\.\)]|(video|post)\s*\d+[:\-]?)/i, '').trim();
        let bodyContent = lines.length > 1 ? lines.slice(1).join('\n') : title;

        const platform = platformSelect.value;
        const niche = nicheSelect.value;
        const tone = toneSelect.value;
        const lang = langSelect.value;

        // If Gemini API Key is configured by user, use Deep Online AI
        if (savedApiKey) {
            try {
                const prompt = `You are a viral social media SEO expert.
Target Platform: ${platform}
Content Title/Topic: ${title}
Body/Details: ${bodyContent}
Language Preference: ${lang}
Tone: ${tone}

Generate an SEO package formatted strictly as follows:
HOOK: (1 viral attention grabbing hook)
CAPTION: (Engaging description with emojis)
KEYWORDS: (5-8 comma-separated high search volume SEO keywords)
CTA: (1 clear call to action)
HASHTAGS: (10-15 trending hashtags including niche and broad tags)`;

                const aiResponse = await generateWithGeminiOnline(savedApiKey, prompt);
                if (aiResponse) {
                    const hookMatch = aiResponse.match(/HOOK:\s*(.*)/i)?.[1] || generateHook(title, tone, lang);
                    const captionMatch = aiResponse.match(/CAPTION:\s*([\s\S]*?)(?=KEYWORDS:|$)/i)?.[1]?.trim() || bodyContent;
                    const kwMatch = aiResponse.match(/KEYWORDS:\s*(.*)/i)?.[1] || extractKeywords(`${title} ${bodyContent}`);
                    const ctaMatch = aiResponse.match(/CTA:\s*(.*)/i)?.[1] || "🔔 Follow for more updates!";
                    const hashMatch = aiResponse.match(/HASHTAGS:\s*(.*)/i)?.[1] || generateHashtags(niche, platform, kwMatch);

                    const formattedTxt = buildFormattedTxtString(title, hookMatch, captionMatch, kwMatch, hashMatch, ctaMatch, "Gemini AI Online Live Engine");

                    return {
                        id: index,
                        title: title || `Video Content #${index}`,
                        hook: hookMatch,
                        caption: captionMatch,
                        keywords: kwMatch,
                        hashtags: hashMatch,
                        cta: ctaMatch,
                        source: "Gemini AI Online",
                        formattedTxt
                    };
                }
            } catch (err) {
                console.warn('Gemini API fetch error, falling back to Live Suggest Engine:', err);
            }
        }

        // Live Online Suggest Scraping Engine
        const onlineKeywordsList = await fetchOnlineLiveSEO(title);
        const baseKeywords = options.customKeywords || extractKeywords(`${title} ${bodyContent}`);
        const combinedKeywords = Array.from(new Set([...baseKeywords.split(',').map(s => s.trim()), ...onlineKeywordsList]))
            .filter(Boolean)
            .slice(0, 8)
            .join(', ');

        const hook = generateHook(title, tone, lang);

        let cta = "";
        if (options.customCta) {
            cta = getCtaFromOption(options.customCta);
        } else {
            const ctaList = CTA_TEMPLATES[tone] || CTA_TEMPLATES.viral;
            cta = ctaList[Math.floor(Math.random() * ctaList.length)];
        }

        const hashtags = generateHashtags(niche, platform, combinedKeywords, onlineKeywordsList);
        const formattedTxt = buildFormattedTxtString(title, hook, bodyContent, combinedKeywords, hashtags, cta, "Live Online Search Trends Engine");

        return {
            id: index,
            title: title || `Video Content #${index}`,
            hook,
            caption: bodyContent,
            keywords: combinedKeywords,
            hashtags,
            cta,
            source: "Live Online SEO",
            formattedTxt
        };
    }

    function generateHook(title, tone, lang) {
        const titleClean = title.replace(/[?!.]/g, '');
        if (lang === 'nepali' || lang === 'mix') {
            if (tone === 'viral') return `🔥 यो भिडियो झुक्किएर पनि नछुटाउनुहोस्: ${titleClean}!`;
            if (tone === 'informative') return `💡 के तपाईंलाई थाहा छ? ${titleClean}`;
            if (tone === 'story') return `📖 आजको यो विशेष भिडियोमा: ${titleClean}...`;
            return `✨ ${titleClean}`;
        } else {
            if (tone === 'viral') return `🚨 STOP SCROLLING! You need to know this about: ${titleClean}!`;
            if (tone === 'informative') return `💡 Here is what you need to know about ${titleClean}:`;
            return `📌 ${titleClean}`;
        }
    }

    function extractKeywords(text) {
        const words = text.toLowerCase().match(/[\w🇳🇵अ-ह]+/g) || [];
        const stopWords = new Set(['the', 'and', 'for', 'you', 'this', 'that', 'with', 'have', 'from', 'nepal', 'video', 'छैन', 'छ', 'हो', 'र', 'का', 'को', 'मा', 'ले']);
        const filtered = words.filter(w => w.length > 3 && !stopWords.has(w));
        const unique = Array.from(new Set(filtered)).slice(0, 6);
        return unique.join(', ');
    }

    function generateHashtags(niche, platform, keywordsStr, onlineTags = []) {
        let tagPool = [];
        
        tagPool = tagPool.concat(HASHTAG_BANK.general);
        tagPool = tagPool.concat(HASHTAG_BANK.nepal);

        if (niche && HASHTAG_BANK[niche]) {
            tagPool = tagPool.concat(HASHTAG_BANK[niche]);
        }

        // Add Online retrieved keywords as hashtags
        if (onlineTags && onlineTags.length > 0) {
            onlineTags.forEach(t => {
                const cleanTag = `#${t.replace(/\s+/g, '')}`;
                if (!tagPool.includes(cleanTag)) tagPool.push(cleanTag);
            });
        }

        if (keywordsStr) {
            const kwArray = keywordsStr.split(',').map(k => k.trim());
            kwArray.forEach(kw => {
                const tag = `#${kw.replace(/\s+/g, '')}`;
                if (!tagPool.includes(tag)) tagPool.push(tag);
            });
        }

        let limit = 15;
        if (platform === 'tiktok') limit = 12;
        if (platform === 'instagram') limit = 20;
        if (platform === 'youtube') limit = 8;

        const shuffled = Array.from(new Set(tagPool)).sort(() => 0.5 - Math.random());
        return shuffled.slice(0, limit).join(' ');
    }

    // Google Gemini Generative Language API Caller
    async function generateWithGeminiOnline(apiKey, promptText) {
        const models = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash'];
        for (const model of models) {
            try {
                const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        contents: [{ parts: [{ text: promptText }] }],
                        generationConfig: {
                            temperature: 0.7,
                            maxOutputTokens: 1000
                        }
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    return data.candidates?.[0]?.content?.parts?.[0]?.text || null;
                }
            } catch (err) {
                console.warn(`Error trying Gemini model ${model}:`, err);
            }
        }
        return null;
    }

    function getCtaFromOption(ctaVal) {
        if (ctaVal === 'follow') return '🔔 Subscribe & Follow for more tips!';
        if (ctaVal === 'comment') return '💬 तपाईंको विचार कमेन्टमा लेख्नुहोस्!';
        if (ctaVal === 'save') return '🔖 Save this video for later!';
        if (ctaVal === 'share') return '➡️ साथीहरूलाई पनि Share गर्नुहोस्!';
        return '🔔 Follow for more updates!';
    }

    function buildFormattedTxtString(title, hook, caption, keywords, hashtags, cta, engineTag = "Online Live SEO Engine") {
        return `========================================
SEO DATA SOURCE: [${engineTag}]
VIDEO TITLE / SUBJECT:
${title}
========================================

🔥 VIRAL HOOK:
${hook}

📌 CAPTION / DESCRIPTION:
${caption}

💡 SEARCH KEYWORDS (SEO & SEARCH TRENDS):
${keywords}

📣 CALL TO ACTION (CTA):
${cta}

🏷️ HASHTAGS (ONLINE PICKED & CATEGORIZED):
${hashtags}
========================================`;
    }

    // --- Render Output Cards ---
    function renderResultCards(results) {
        cardsGrid.innerHTML = '';
        resultsCountBadge.textContent = `${results.length} Video${results.length > 1 ? 's' : ''} Processed`;
        outputSection.classList.remove('hidden');

        results.forEach((item) => {
            const card = document.createElement('div');
            card.className = 'result-card';
            
            const charCount = item.formattedTxt.length;
            const hashtagCount = (item.hashtags.match(/#/g) || []).length;

            card.innerHTML = `
                <div class="result-card-header">
                    <div class="video-number">
                        <i class="fa-solid fa-film"></i> Video #${item.id}
                    </div>
                    <div class="video-meta">
                        <span><i class="fa-solid fa-hashtag"></i> ${hashtagCount} Tags</span>
                        <span><i class="fa-solid fa-font"></i> ${charCount} Chars</span>
                    </div>
                </div>

                <div class="card-tab-bar">
                    <button class="card-tab active" data-view="full">Full .txt Package</button>
                    <button class="card-tab" data-view="caption">Caption & Hook</button>
                    <button class="card-tab" data-view="hashtags">Hashtags & SEO</button>
                </div>

                <div class="card-content-box">
                    <pre class="formatted-txt-preview" id="preview_${item.id}">${escapeHtml(item.formattedTxt)}</pre>
                </div>

                <div class="card-actions-footer">
                    <div class="stats-badges">
                        <span class="stat-item stat-item-live"><i class="fa-solid fa-bolt"></i> ${item.source || 'Live Online SEO'}</span>
                        <span class="stat-item">UTF-8 .txt</span>
                    </div>
                    <div class="card-btn-group">
                        <button class="btn btn-secondary btn-sm copy-card-btn" data-id="${item.id}">
                            <i class="fa-solid fa-copy"></i> Copy
                        </button>
                        <button class="btn btn-primary btn-sm download-card-btn" data-id="${item.id}">
                            <i class="fa-solid fa-download"></i> Save .txt
                        </button>
                    </div>
                </div>
            `;

            cardsGrid.appendChild(card);

            // Tab Switching inside individual Card
            const cardTabs = card.querySelectorAll('.card-tab');
            const previewBox = card.querySelector(`#preview_${item.id}`);

            cardTabs.forEach(ctab => {
                ctab.addEventListener('click', () => {
                    cardTabs.forEach(t => t.classList.remove('active'));
                    ctab.classList.add('active');

                    const viewType = ctab.getAttribute('data-view');
                    if (viewType === 'full') {
                        previewBox.textContent = item.formattedTxt;
                    } else if (viewType === 'caption') {
                        previewBox.textContent = `${item.hook}\n\n${item.caption}\n\n${item.cta}`;
                    } else if (viewType === 'hashtags') {
                        previewBox.textContent = `SEARCH KEYWORDS:\n${item.keywords}\n\nHASHTAGS:\n${item.hashtags}`;
                    }
                });
            });
        });

        // Attach event listeners for Copy and Download on Cards
        document.querySelectorAll('.copy-card-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.currentTarget.getAttribute('data-id'));
                const targetObj = processedResults.find(r => r.id === id);
                if (targetObj) {
                    copyToClipboard(targetObj.formattedTxt);
                    showToast(`Video #${id} टेक्स्ट Copy भयो!`, 'success');
                }
            });
        });

        document.querySelectorAll('.download-card-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.currentTarget.getAttribute('data-id'));
                const targetObj = processedResults.find(r => r.id === id);
                if (targetObj) {
                    const filename = `video_${id}_seo_caption.txt`;
                    downloadSingleTxtFile(filename, targetObj.formattedTxt);
                    showToast(`${filename} डाउनलोड भयो!`, 'success');
                }
            });
        });

        outputSection.scrollIntoView({ behavior: 'smooth' });
    }

    // --- Bulk Export Actions ---

    copyAllOutputBtn.addEventListener('click', () => {
        if (processedResults.length === 0) return;
        const allText = processedResults.map(r => r.formattedTxt).join('\n\n\n');
        copyToClipboard(allText);
        showToast('सबै भिडियो क्याप्शन र ह्यासट्याग Copy भयो!', 'success');
    });

    downloadCombinedTxtBtn.addEventListener('click', () => {
        if (processedResults.length === 0) return;
        const combinedText = processedResults.map(r => r.formattedTxt).join('\n\n\n');
        downloadSingleTxtFile(`all_videos_seo_captions.txt`, combinedText);
        showToast('एकमुष्ट all_videos_seo_captions.txt डाउनलोड भयो!', 'success');
    });

    downloadZipBtn.addEventListener('click', async () => {
        if (processedResults.length === 0) return;
        if (typeof JSZip === 'undefined') {
            showToast('JSZip Library उपलब्ध छैन, Combined .txt डाउनलोड गर्दै...', 'error');
            downloadSingleTxtFile(`all_videos_seo_captions.txt`, processedResults.map(r => r.formattedTxt).join('\n\n\n'));
            return;
        }

        const zip = new JSZip();
        const folder = zip.folder("video_captions_txt");

        processedResults.forEach(r => {
            const sanitizedTitle = r.title.substring(0, 20).replace(/[^a-zA-Z0-9\u0900-\u097F]/g, '_');
            const fileName = `video_${r.id}_${sanitizedTitle}.txt`;
            folder.file(fileName, r.formattedTxt);
        });

        const blob = await zip.generateAsync({ type: "blob" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "video_seo_captions_pack.zip";
        link.click();
        URL.revokeObjectURL(link.href);
        showToast('ZIP फाइल सफलतापुर्वक डाउनलोड भयो!', 'success');
    });

    // --- Utility Functions ---
    function downloadSingleTxtFile(filename, textContent) {
        const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
        URL.revokeObjectURL(link.href);
    }

    function copyToClipboard(text) {
        navigator.clipboard.writeText(text).catch(err => {
            console.error('Copy error:', err);
        });
    }

    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        const iconClass = type === 'success' ? 'fa-circle-check' : 'fa-circle-exclamation';
        toast.innerHTML = `<i class="fa-solid ${iconClass}"></i> <span>${escapeHtml(message)}</span>`;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    function escapeHtml(str) {
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});

/**
 * iQIYI Recommend / Hero Banner Extractor Script
 *
 * Injected into the browser page context to extract the 6 main carousel series
 * with their 3 distinct visual layers:
 * 1. Background image (bg_url)
 * 2. Character cutout / focus image (character_url)
 * 3. Series logo / title artwork (logo_url)
 */
(() => {
    function fixUrl(u) {
        if (!u || typeof u !== 'string') return null;
        u = u.trim();
        if (!u) return null;
        if (u.startsWith('//')) return 'https:' + u;
        if (u.startsWith('http://')) return u.replace('http://', 'https://');
        return u;
    }

    function extractFromFiber() {
        const candidates = document.querySelectorAll('.pc-focus-wrapper, [class*="focus-wrapper"], [class*="focus"]');
        for (const el of candidates) {
            const fiberKey = Object.keys(el).find(k => k.startsWith('__reactFiber$') || k.startsWith('__reactInternalInstance$'));
            if (!fiberKey) continue;

            let cur = el[fiberKey];
            let depth = 0;
            while (cur && depth < 25) {
                if (cur.memoizedProps) {
                    const props = cur.memoizedProps;
                    const list = props.focusImgInfo || (props.data && props.data.focusImgInfo) || (props.blocks);
                    if (Array.isArray(list) && list.length > 0 && (list[0].imgSrc || list[0].title)) {
                        return list;
                    }
                }
                cur = cur.return;
                depth++;
            }
        }
        return null;
    }

    function extractFromNextData() {
        if (!window.__NEXT_DATA__ || !window.__NEXT_DATA__.props) return null;
        try {
            const state = window.__NEXT_DATA__.props.initialState || {};
            const commonConfig = state.commonConfig || {};
            const homeWeb = commonConfig.home_web || {};
            const cards = homeWeb.cards || [];
            const bannerCard = cards.find(c => c && (c.card_type === 'pcw_focus_banner' || (c.name && c.name.includes('焦点图'))));
            if (bannerCard && Array.isArray(bannerCard.blocks) && bannerCard.blocks.length > 0) {
                return bannerCard.blocks;
            }
        } catch (e) {
            console.error('[Extractor] Error reading __NEXT_DATA__:', e);
        }
        return null;
    }

    function extractFromDOM() {
        const results = [];
        const focusItems = document.querySelectorAll('.focus-item, [class*="focus-item-title"]');
        
        // Check current hero banner in DOM
        const bgEl = document.querySelector('.focus-img-background img, .focus-img-wapper img, [class*="focus-img"] img');
        const charEl = document.querySelector('.focus-character img, [class*="focus-character"] img');
        const titleEl = document.querySelector('.focus-item-title, .focus-item-title a, h1, h2');
        const descEl = document.querySelector('.focus-item-desc, [class*="focus-item-desc"]');

        if (bgEl || charEl || titleEl) {
            results.push({
                index: 1,
                title: (titleEl && titleEl.textContent ? titleEl.textContent.trim() : 'Series_1'),
                bg_url: fixUrl(bgEl ? (bgEl.src || bgEl.getAttribute('data-src')) : null),
                character_url: fixUrl(charEl ? (charEl.src || charEl.getAttribute('data-src')) : null),
                logo_url: null,
                desc: (descEl && descEl.textContent ? descEl.textContent.trim() : ''),
                tags: []
            });
        }
        return results;
    }

    // Try extraction strategies in order of data richness
    let rawItems = extractFromFiber();
    if (!rawItems || rawItems.length === 0) {
        rawItems = extractFromNextData();
    }

    if (rawItems && Array.isArray(rawItems) && rawItems.length > 0) {
        return rawItems.map((item, idx) => {
            const logo = (item.defMultiImageObj && item.defMultiImageObj.url) 
                ? item.defMultiImageObj.url 
                : item.defMultiImage;
            
            return {
                index: (typeof item.index === 'number' ? item.index + 1 : idx + 1),
                title: (item.title || `Series_${idx + 1}`).trim(),
                bg_url: fixUrl(item.imgSrc || item.imgSrcMobile),
                character_url: fixUrl(item.characterImage || item.characterImageMobile),
                logo_url: fixUrl(logo),
                desc: (item.desc || '').trim(),
                score: item.score || null,
                year: item.year || null,
                rating: item.rating || null,
                tags: Array.isArray(item.categoryTagList) ? item.categoryTagList : [],
                play_link: fixUrl(item.playLink)
            };
        });
    }

    return extractFromDOM();
})();

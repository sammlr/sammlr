const stickerListPage = document.querySelector('.sticker-list-glassboard-page');
const CEOKLAUE_STICKER_LIST_SEED = stickerListPage.dataset.stickerListMixingSeed;
const STICKER_LIST_ALBUM_ID = stickerListPage.dataset.stickerListAlbumId;
const CEOKLAUE_STICKER_LIST_STORAGE_KEY = `sammlr.stickerList.selection.${STICKER_LIST_ALBUM_ID}.v01`;
const stickerListSelections = {
    get: [],
    give: []
};
const stickerListGlassboard = document.getElementById('stickerListReviewModal');
const STICKER_LIST_GLASSBOARD_MOTION_MS = 400;
const STICKER_LIST_REVIEW_FIRST_COLUMN_CAPACITY = 8;
const STICKER_LIST_REVIEW_FIRST_NOTE_CAPACITY = 16;
const STICKER_LIST_REVIEW_CONTINUATION_COLUMN_CAPACITY = 10;
const STICKER_LIST_REVIEW_CONTINUATION_NOTE_CAPACITY = 20;
let stickerListLockedScrollY = 0;
let stickerListGlassboardCloseTimer = 0;
let stickerListSwipeStart = null;

function stickerListLockPageScroll(){
    stickerListLockedScrollY = window.scrollY || window.pageYOffset || 0;
    document.documentElement.classList.add('sticker-list-glassboard-locked');
    document.body.classList.add('sticker-list-glassboard-locked');
    document.body.style.position = 'fixed';
    document.body.style.top = '-' + stickerListLockedScrollY + 'px';
    document.body.style.left = '0';
    document.body.style.right = '0';
    document.body.style.width = '100%';
}

function stickerListUnlockPageScroll(){
    const restoreY = stickerListLockedScrollY;
    document.documentElement.classList.remove('sticker-list-glassboard-locked');
    document.body.classList.remove('sticker-list-glassboard-locked');
    document.body.style.position = '';
    document.body.style.top = '';
    document.body.style.left = '';
    document.body.style.right = '';
    document.body.style.width = '';
    window.scrollTo(0, restoreY);
}

function stickerListCeoklaueIndex(text, character, position, context, previousAlternate){
    const payload = CEOKLAUE_STICKER_LIST_SEED + '\0' + context + '\0' + text + '\0' + position + '\0' + character;
    let value = 2166136261;
    for(let index = 0; index < payload.length; index += 1){
        value ^= payload.charCodeAt(index);
        value = Math.imul(value, 16777619) >>> 0;
    }
    let alternate = value % 3;
    if(previousAlternate !== undefined && alternate === previousAlternate - 1){
        alternate = (alternate + 1 + ((value >>> 8) & 1)) % 3;
    }
    return alternate + 1;
}

function stickerListWriteCeoklaue(target, text, context){
    target.replaceChildren();
    const run = document.createElement('span');
    run.className = 'ceoklaue-run';
    run.setAttribute('aria-label', text);
    run.dataset.ceoklaueContext = context;
    const previousAlternates = Object.create(null);
    Array.from(text).forEach(function(character, position){
        const glyph = document.createElement('span');
        glyph.setAttribute('aria-hidden', 'true');
        glyph.textContent = character;
        if(character === ' '){
            glyph.className = 'ceoklaue-space';
        }else if('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789äöüÄÖÜß.,:;!?-+/&%()'.includes(character)){
            const alternate = stickerListCeoklaueIndex(
                text, character, position, context, previousAlternates[character]
            );
            previousAlternates[character] = alternate;
            glyph.className = 'ceoklaue-glyph ceoklaue-alt-' + alternate;
            glyph.dataset.character = character;
            glyph.dataset.alternate = String(alternate);
        }else{
            glyph.className = 'ceoklaue-fallback';
        }
        run.appendChild(glyph);
    });
    target.appendChild(run);
}

function stickerListCodeLabel(itemKey){
    const parts = String(itemKey).split('::');
    const code = parts[0];
    const item = Array.from(document.querySelectorAll('.sticker-list-item')).find(function(candidate){
        return stickerListItemKey(candidate) === itemKey || candidate.dataset.code === code;
    });
    return item ? (item.dataset.display || code) : code;
}

function stickerListItemKey(item){
    return item.dataset.code + '::' + (item.dataset.instance || '1');
}

function stickerListRenderCodes(mode){
    const items = stickerListSelections[mode];
    if(items.length === 0) return 'Noch nichts markiert';
    return items.map(stickerListCodeLabel).join('<br>');
}

function stickerListCountLabel(count){
    return count + (count === 1 ? ' Sticker' : ' Sticker');
}

function stickerListSyncHiddenInputs(){
    const hidden = document.getElementById('stickerListHiddenInputs');
    hidden.innerHTML = '';

    stickerListSelections.get.forEach(function(itemKey){
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'get_codes';
        input.value = String(itemKey).split('::')[0];
        hidden.appendChild(input);
    });

    stickerListSelections.give.forEach(function(itemKey){
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'give_codes';
        input.value = String(itemKey).split('::')[0];
        hidden.appendChild(input);
    });
}

function stickerListWriteCountLine(target, getCount, giveCount, context){
    target.replaceChildren();
    const first = document.createElement('span');
    const second = document.createElement('span');
    stickerListWriteCeoklaue(first, getCount + ' erhalten', context + '-get');
    stickerListWriteCeoklaue(second, giveCount + ' abgegeben', context + '-give');
    const dot = document.createElement('img');
    dot.className = 'ceoklaue-middle-dot';
    dot.src = '/static/ceoklaue-ui/middle-dot-0' + ([1,2,4][(getCount + giveCount) % 3]) + '.svg';
    dot.alt = ' · ';
    target.append(first, dot, second);
}

function stickerListWriteReviewCountLine(target, getCount, giveCount, context){
    target.replaceChildren();
    const first = document.createElement('span');
    const second = document.createElement('span');
    stickerListWriteCeoklaue(first, getCount + ' erhalten', context + '-get');
    stickerListWriteCeoklaue(second, giveCount + ' abgegeben', context + '-give');
    target.append(first, second);
}

function stickerListSizePostitUnderlines(scope){
    (scope || document).querySelectorAll('[data-postit-heading]').forEach(function(heading){
        const underline = heading.nextElementSibling;
        if(!underline || !underline.classList.contains('postit-underline')) return;
        underline.style.width = Math.ceil(heading.getBoundingClientRect().width + 6) + 'px';
    });
}

function stickerListPersist(){
    localStorage.setItem(CEOKLAUE_STICKER_LIST_STORAGE_KEY, JSON.stringify(stickerListSelections));
}

function stickerListUpdateTradebar(){
    const getCount = stickerListSelections.get.length;
    const giveCount = stickerListSelections.give.length;
    stickerListWriteCountLine(document.getElementById('stickerListSummary'), getCount, giveCount, `sticker-list-${STICKER_LIST_ALBUM_ID}-trade-summary`);
    const canReview = getCount > 0 || giveCount > 0;
    const tradebar = document.querySelector('.sticker-list-tradebar');
    tradebar.hidden = !canReview;
    tradebar.classList.toggle('is-active', canReview);
    tradebar.classList.toggle('is-idle', !canReview);
    document.getElementById('stickerListReviewButton').disabled = !canReview;
    requestAnimationFrame(function(){ stickerListSizePostitUnderlines(tradebar); });

    stickerListSyncHiddenInputs();
    stickerListPersist();
}

function stickerListRenderReview(){
    stickerListRenderReviewMode('get', 'stickerListReviewGetNotes', 'stickerListReviewGetPostit');
    stickerListRenderReviewMode('give', 'stickerListReviewGiveNotes', 'stickerListReviewGivePostit');

    const submit = document.getElementById('stickerListSubmit');
    const subtitle = document.getElementById('stickerListReviewSubtitle');
    const getCount = stickerListSelections.get.length;
    const giveCount = stickerListSelections.give.length;
    const invalid = getCount === 0 && giveCount === 0;

    if(subtitle) stickerListWriteReviewCountLine(subtitle, getCount, giveCount, `sticker-list-${STICKER_LIST_ALBUM_ID}-review-summary`);
    submit.disabled = invalid;
    requestAnimationFrame(function(){ stickerListSizePostitUnderlines(document.querySelector('.sticker-list-review-postits')); });
}

function stickerListRenderReviewMode(mode, columnId, firstPostitId){
    const column = document.getElementById(columnId);
    const firstPostit = document.getElementById(firstPostitId);
    if(!column || !firstPostit) return;

    column.querySelectorAll('.trade-postit[data-review-continuation]').forEach(function(note){ note.remove(); });
    const items = stickerListSelections[mode];
    if(items.length === 0){
        firstPostit.hidden = true;
        column.hidden = true;
        return;
    }

    firstPostit.hidden = false;
    column.hidden = false;
    const continuationCount = Math.ceil(
        Math.max(0, items.length - STICKER_LIST_REVIEW_FIRST_NOTE_CAPACITY)
        / STICKER_LIST_REVIEW_CONTINUATION_NOTE_CAPACITY
    );
    const noteCount = 1 + continuationCount;
    for(let noteIndex = 0; noteIndex < noteCount; noteIndex += 1){
        const postit = noteIndex === 0 ? firstPostit : firstPostit.cloneNode(false);
        let target;
        if(noteIndex === 0){
            target = postit.querySelector('.sticker-list-review-codes');
        }else{
            postit.removeAttribute('id');
            postit.dataset.reviewContinuation = String(noteIndex + 1);
            postit.classList.add('is-continuation');
            target = document.createElement('div');
            target.className = 'sticker-list-review-codes';
            postit.appendChild(target);
            column.appendChild(postit);
        }
        const isContinuation = noteIndex > 0;
        const capacity = isContinuation
            ? STICKER_LIST_REVIEW_CONTINUATION_NOTE_CAPACITY
            : STICKER_LIST_REVIEW_FIRST_NOTE_CAPACITY;
        const columnCapacity = isContinuation
            ? STICKER_LIST_REVIEW_CONTINUATION_COLUMN_CAPACITY
            : STICKER_LIST_REVIEW_FIRST_COLUMN_CAPACITY;
        const start = isContinuation
            ? STICKER_LIST_REVIEW_FIRST_NOTE_CAPACITY
                + (noteIndex - 1) * STICKER_LIST_REVIEW_CONTINUATION_NOTE_CAPACITY
            : 0;
        const chunk = items.slice(start, start + capacity);
        target.replaceChildren();
        target.classList.toggle('is-two-column', chunk.length > columnCapacity);
        chunk.forEach(function(itemKey){
            const row = document.createElement('div');
            row.className = 'pending-review-row';

            const label = document.createElement('strong');
            label.className = 'sticker-list-review-code';
            stickerListWriteCeoklaue(
                label,
                stickerListCodeLabel(itemKey),
                `sticker-list-${STICKER_LIST_ALBUM_ID}-review-${mode}-${noteIndex}-${itemKey}`
            );

            row.appendChild(label);
            target.appendChild(row);
        });
    }
}

function stickerListOpenDetail(){
    const detail = document.getElementById('stickerListDetailContent');
    detail.replaceChildren();
    ['get','give'].forEach(function(mode){
        const section = document.createElement('section');
        const heading = document.createElement('h3');
        heading.textContent = mode === 'get' ? 'Du bekommst' : 'Du gibst ab';
        section.appendChild(heading);
        stickerListSelections[mode].forEach(function(key){
            const line = document.createElement('p'); line.textContent = stickerListCodeLabel(key); section.appendChild(line);
        });
        detail.appendChild(section);
    });
    document.querySelector('.sticker-list-review-postits').hidden = true;
    document.getElementById('stickerListDetailView').hidden = false;
}

document.querySelectorAll('.sticker-list-item').forEach(function(item){
    item.addEventListener('click', function(){
        const mode = item.dataset.listMode;
        const selection = stickerListSelections[mode];
        const itemKey = stickerListItemKey(item);

        if(selection.includes(itemKey)){
            stickerListSelections[mode] = selection.filter(function(existing){
                return existing !== itemKey;
            });
            item.classList.remove('selected');
            item.setAttribute('aria-pressed', 'false');
        }else{
            selection.push(itemKey);
            item.classList.remove('is-restored');
            item.classList.add('selected');
            item.setAttribute('aria-pressed', 'true');
        }

        stickerListUpdateTradebar();
    });
});

document.getElementById('stickerListClear').addEventListener('click', function(){
    stickerListSelections.get = [];
    stickerListSelections.give = [];
    document.querySelectorAll('.sticker-list-item.selected').forEach(function(item){
        item.classList.remove('selected');
        item.setAttribute('aria-pressed', 'false');
    });
    stickerListUpdateTradebar();
});

document.getElementById('stickerListReviewButton').addEventListener('click', function(){
    if(stickerListGlassboard.classList.contains('is-review')) return;
    stickerListRenderReview();
    window.clearTimeout(stickerListGlassboardCloseTimer);
    document.querySelector('.sticker-list-review-postits').hidden = false;
    document.getElementById('stickerListDetailView').hidden = true;
    stickerListLockPageScroll();
    stickerListGlassboard.classList.remove('is-closing');
    stickerListGlassboard.classList.add('is-review');
    stickerListGlassboard.dataset.glassboardState = 'review';
    stickerListGlassboard.setAttribute('aria-hidden', 'false');
});

function stickerListCloseReview(){
    if(!stickerListGlassboard.classList.contains('is-review')) return;
    stickerListGlassboard.classList.add('is-closing');
    stickerListGlassboard.classList.remove('is-review');
    stickerListGlassboard.dataset.glassboardState = 'closing';
    stickerListGlassboard.setAttribute('aria-hidden', 'true');
    window.clearTimeout(stickerListGlassboardCloseTimer);
    stickerListGlassboardCloseTimer = window.setTimeout(function(){
        stickerListGlassboard.classList.remove('is-closing');
        stickerListGlassboard.dataset.glassboardState = 'list';
        document.querySelector('.sticker-list-review-postits').hidden = false;
        document.getElementById('stickerListDetailView').hidden = true;
        stickerListUnlockPageScroll();
    }, STICKER_LIST_GLASSBOARD_MOTION_MS);
}

document.getElementById('stickerListReviewClose').addEventListener('click', function(){
    stickerListCloseReview();
});

function stickerListIsFreeGlassTarget(target){
    return !target.closest('button, a, .trade-postit, .sticker-list-detail-view');
}

stickerListGlassboard.addEventListener('touchstart', function(event){
    if(!stickerListGlassboard.classList.contains('is-review')) return;
    if(event.touches.length !== 1 || !stickerListIsFreeGlassTarget(event.target)) return;
    const touch = event.touches[0];
    stickerListSwipeStart = {x:touch.clientX, y:touch.clientY};
}, {passive:true});

stickerListGlassboard.addEventListener('touchmove', function(event){
    if(!stickerListSwipeStart || !stickerListGlassboard.classList.contains('is-review')) return;
    event.preventDefault();
}, {passive:false});

stickerListGlassboard.addEventListener('touchend', function(event){
    if(!stickerListSwipeStart || event.changedTouches.length !== 1){
        stickerListSwipeStart = null;
        return;
    }
    const touch = event.changedTouches[0];
    const deltaX = touch.clientX - stickerListSwipeStart.x;
    const deltaY = touch.clientY - stickerListSwipeStart.y;
    stickerListSwipeStart = null;
    if(deltaY < -56 && Math.abs(deltaY) > Math.abs(deltaX) * 1.2){
        stickerListCloseReview();
    }
}, {passive:true});

stickerListGlassboard.addEventListener('touchcancel', function(){
    stickerListSwipeStart = null;
}, {passive:true});

document.getElementById('stickerListDetailClose').addEventListener('click', function(){
    document.getElementById('stickerListDetailView').hidden = true;
    document.querySelector('.sticker-list-review-postits').hidden = false;
});

document.getElementById('stickerListTradeForm').addEventListener('submit', function(event){
    stickerListRenderReview();
    if(document.getElementById('stickerListSubmit').disabled){
        event.preventDefault();
    }
});

try{
    const stored = JSON.parse(localStorage.getItem(CEOKLAUE_STICKER_LIST_STORAGE_KEY) || 'null');
    if(stored && Array.isArray(stored.get) && Array.isArray(stored.give)){
        ['get','give'].forEach(function(mode){
            const allowed = new Set(Array.from(document.querySelectorAll('.sticker-list-item[data-list-mode="' + mode + '"]')).map(stickerListItemKey));
            stickerListSelections[mode] = stored[mode].filter(function(key){ return allowed.has(key); });
            stickerListSelections[mode].forEach(function(key){
                const item = Array.from(document.querySelectorAll('.sticker-list-item[data-list-mode="' + mode + '"]')).find(function(candidate){ return stickerListItemKey(candidate) === key; });
                if(item){ item.classList.add('selected','is-restored'); item.setAttribute('aria-pressed','true'); }
            });
        });
    }
}catch(error){ localStorage.removeItem(CEOKLAUE_STICKER_LIST_STORAGE_KEY); }
stickerListUpdateTradebar();
if(document.fonts && document.fonts.ready){
    document.fonts.ready.then(function(){ stickerListSizePostitUnderlines(document); });
}

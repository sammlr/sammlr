(function () {
    "use strict";

    const wall = document.querySelector('[data-sticker-wall-renderer="canonical"][data-wall-capability="read-only"]');
    if (!wall) return;

    const search = document.getElementById("stickerSearch");
    const count = document.getElementById("visibleStickerCount");
    const feedback = document.getElementById("searchDebugBox");
    const sticky = document.getElementById("stickerWallStickyContext");
    const storageKey = "sammlr:public-stickerwall:chapters:" + window.location.pathname;
    let activeFilter = (document.querySelector(".sticker-filter-pill.active") || {}).dataset?.filter || "all";
    let stickySource = null;

    function normalize(value) {
        return String(value || "").trim().toUpperCase().replace(/[^A-Z0-9]/g, "");
    }

    function slotMatches(slot) {
        if (activeFilter === "missing") return slot.classList.contains("missing");
        if (activeFilter === "duplicate") return slot.classList.contains("duplicate");
        return true;
    }

    function searchMatches(slot, term) {
        if (!term) return true;
        const needle = normalize(term);
        return normalize([slot.dataset.code, slot.dataset.display, slot.dataset.search].join(" ")).includes(needle);
    }

    function applyCollapse() {
        const searching = Boolean(normalize(search && search.value));
        wall.querySelectorAll(".album-chapter-title").forEach(function (heading) {
            const collapsed = heading.classList.contains("chapter-collapsed") && !searching;
            heading.setAttribute("aria-expanded", collapsed ? "false" : "true");
            const chapter = heading.closest(".sticker-chapter-block");
            if (!chapter) return;
            Array.from(chapter.children).forEach(function (child) {
                if (child !== heading) child.classList.toggle("collapse-section-hidden", collapsed);
            });
        });
    }

    function refresh() {
        const term = search ? search.value : "";
        let visible = 0;
        wall.querySelectorAll("a.slot[data-code]").forEach(function (slot) {
            const show = slotMatches(slot) && searchMatches(slot, term);
            const frame = slot.closest("[data-sticker-frame]");
            slot.classList.toggle("filter-hidden", !slotMatches(slot));
            slot.classList.toggle("search-hidden", !searchMatches(slot, term));
            if (frame) frame.hidden = !show;
            if (show) visible += 1;
        });
        wall.querySelectorAll(".sticker-team-block").forEach(function (team) {
            team.style.display = team.querySelector("[data-sticker-frame]:not([hidden])") ? "" : "none";
        });
        wall.querySelectorAll(".sticker-chapter-block").forEach(function (chapter) {
            chapter.style.display = chapter.querySelector("[data-sticker-frame]:not([hidden])") ? "" : "none";
        });
        applyCollapse();
        if (count) count.textContent = String(visible);
        if (feedback) {
            feedback.style.display = normalize(term) ? "block" : "none";
            feedback.textContent = visible ? visible + " Treffer" : "Kein Treffer";
        }
        syncStickyContext();
    }

    function persistChapters() {
        try {
            const expanded = Array.from(wall.querySelectorAll(".album-chapter-title:not(.chapter-collapsed)"))
                .map(function (heading) { return heading.id; });
            window.sessionStorage.setItem(storageKey, JSON.stringify(expanded));
        } catch (_error) {
            return;
        }
    }

    function restoreChapters() {
        try {
            const saved = JSON.parse(window.sessionStorage.getItem(storageKey) || "null");
            if (!Array.isArray(saved)) return;
            const expanded = new Set(saved);
            wall.querySelectorAll(".album-chapter-title").forEach(function (heading) {
                heading.classList.toggle("chapter-collapsed", !expanded.has(heading.id));
            });
        } catch (_error) {
            return;
        }
    }

    function toggleChapter(heading) {
        heading.classList.toggle("chapter-collapsed");
        persistChapters();
        applyCollapse();
        syncStickyContext();
    }

    function stickyTop() {
        const bodyStyle = window.getComputedStyle(document.body);
        return (parseFloat(bodyStyle.getPropertyValue("--stickerwall-app-header-offset")) || 0)
            + (parseFloat(bodyStyle.getPropertyValue("--stickerwall-control-height")) || 0);
    }

    function syncStickyOffsets() {
        const header = document.querySelector(".app-header");
        const controls = document.querySelector(".sticker-wall-controlbar");
        if (!controls) return;
        document.body.style.setProperty("--stickerwall-app-header-offset", Math.ceil(header ? header.getBoundingClientRect().height + 6 : 0) + "px");
        document.body.style.setProperty("--stickerwall-control-height", Math.ceil(controls.getBoundingClientRect().height) + "px");
        syncStickyContext();
    }

    function syncStickyContext() {
        if (!sticky) return;
        const sources = Array.from(wall.querySelectorAll(".album-chapter-title, .team-title")).filter(function (source) {
            return source.offsetParent !== null && !source.closest(".collapse-section-hidden");
        });
        if (!sources.length) {
            sticky.hidden = true;
            return;
        }
        const top = stickyTop();
        stickySource = sources[0];
        sources.forEach(function (source) {
            if (source.getBoundingClientRect().top <= top) stickySource = source;
        });
        const spans = stickySource.querySelectorAll("span");
        sticky.querySelector("[data-sticky-context-label]").textContent = spans[0]?.textContent || "";
        sticky.querySelector("[data-sticky-context-counter]").textContent = spans[spans.length - 1]?.textContent || "";
        const sourceProgress = stickySource.querySelector(".chapter-progress-fill");
        sticky.querySelector("[data-sticky-context-progress]").style.width = sourceProgress?.style.width || "0%";
        const collapsible = stickySource.classList.contains("album-chapter-title");
        sticky.classList.toggle("is-collapsible", collapsible);
        sticky.classList.toggle("chapter-collapsed", stickySource.classList.contains("chapter-collapsed"));
        sticky.hidden = false;
        sticky.setAttribute("aria-hidden", "false");
    }

    restoreChapters();
    wall.querySelectorAll(".album-chapter-title").forEach(function (heading) {
        heading.addEventListener("click", function () { toggleChapter(heading); });
        heading.addEventListener("keydown", function (event) {
            if (event.key !== "Enter" && event.key !== " ") return;
            event.preventDefault();
            toggleChapter(heading);
        });
    });
    document.querySelectorAll(".sticker-filter-pill[data-filter]").forEach(function (pill) {
        pill.setAttribute("aria-pressed", pill.classList.contains("active") ? "true" : "false");
        pill.addEventListener("click", function (event) {
            if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
            event.preventDefault();
            activeFilter = pill.dataset.filter || "all";
            document.querySelectorAll(".sticker-filter-pill[data-filter]").forEach(function (candidate) {
                const active = candidate === pill;
                candidate.classList.toggle("active", active);
                candidate.setAttribute("aria-pressed", active ? "true" : "false");
            });
            const url = new URL(window.location.href);
            if (activeFilter === "all") url.searchParams.delete("filter");
            else url.searchParams.set("filter", activeFilter);
            window.history.replaceState({}, "", url);
            refresh();
        });
    });
    if (search) search.addEventListener("input", refresh);
    if (sticky) sticky.addEventListener("click", function () {
        if (stickySource?.classList.contains("album-chapter-title")) toggleChapter(stickySource);
    });
    window.addEventListener("scroll", syncStickyContext, {passive: true});
    window.addEventListener("resize", syncStickyOffsets);
    syncStickyOffsets();
    refresh();
}());

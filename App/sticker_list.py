"""Frozen Stickerliste product surface.

The feature keeps its route and transfer behavior local while receiving the
small set of established application services it still shares with SAMMLR.
"""

from dataclasses import dataclass
from html import escape
import re
from urllib.parse import quote

from flask import redirect, render_template, request, session

from services.inventory import InventoryReadService


@dataclass(frozen=True)
class StickerListDependencies:
    load_album: object
    all_codes: object
    display_code: object
    ceoklaue_run: object
    ceoklaue_mix_index: object
    ceoklaue_marker_asset: object
    bracket_button_content: object
    feedback_html: object
    consume_trophy_popup_html: object
    app_header_brand_wordmark: object
    global_head: object
    bottom_nav: object
    resolve_code: object
    reached_trophies: object
    history_request_event_key: object
    get_db: object
    current_user_id: object
    remove_sticker_quantity: object
    add_sticker_quantity: object
    record_trophy_unlocks: object
    queue_trophy_popup: object
    ceoklaue_mixing_seed: str


def register_sticker_list_routes(app, dependencies):
    """Register the unchanged public Stickerliste endpoints on ``app``."""
    deps = StickerListDependencies(**dependencies)

    def stickerliste(album_id):
        album, by_code, gesammelt, doppelte, _prozent, total = deps.load_album(
            album_id
        )
        message = request.args.get("message", "")
        codes = deps.all_codes(album_id)
        missing_codes = [
            code
            for code in codes
            if code not in by_code or by_code[code].availability.physical == 0
        ]
        duplicate_codes = [
            code
            for code in codes
            if code in by_code and by_code[code].availability.is_available
        ]
        missing_count = total - gesammelt

        def ink(text, context):
            return deps.ceoklaue_run(
                str(text), f"sticker-list-{album_id}-{context}"
            )

        def bracket(label, context, action, position=0):
            return deps.bracket_button_content(
                label,
                f"sticker-list-{album_id}-{context}",
                action,
                position,
            )

        def middle_dot(context):
            variants = ("01", "02", "04")
            index = deps.ceoklaue_mix_index(
                "·", "·", 0, f"sticker-list-{album_id}-{context}"
            )
            return (
                '<img class="ceoklaue-middle-dot" '
                f'src="/static/ceoklaue-ui/middle-dot-{variants[index]}.svg" '
                'alt=" · ">'
            )

        def list_item(code, mode, instance=1, separator=False):
            label = deps.display_code(code)
            instance_attr = (
                f' data-instance="{instance}"' if mode == "give" else ""
            )
            marker_family = "receive_circle" if mode == "get" else "give_cross"
            marker = deps.ceoklaue_marker_asset(
                marker_family,
                code,
                instance,
                f"sticker-list-{album_id}-marker",
            )
            marker_id = (
                f"marker-{mode}-"
                f"{re.sub(r'[^A-Za-z0-9_-]', '-', code)}-{instance}"
            )
            if mode == "get":
                marker_svg = (
                    '<svg class="sticker-selection-marker" viewBox="0 0 1000 620" '
                    'aria-hidden="true" data-marker-rendering="static">'
                    f'<image href="{marker["url"]}" width="1000" height="620" '
                    'preserveAspectRatio="xMidYMid meet"/></svg>'
                )
            else:
                draw_paths = (
                    '<path class="marker-draw marker-draw-cross marker-draw-one" '
                    'pathLength="1" d="M150 90L850 530"/>'
                    '<path class="marker-draw marker-draw-cross marker-draw-two" '
                    'pathLength="1" d="M850 90L150 530"/>'
                )
                marker_svg = (
                    '<svg class="sticker-selection-marker" viewBox="0 0 1000 620" '
                    'aria-hidden="true" '
                    'data-draw-direction="top-left-to-bottom-right-then-top-right-to-bottom-left">'
                    f'<defs><mask id="{marker_id}">{draw_paths}</mask></defs>'
                    f'<image href="{marker["url"]}" width="1000" height="620" '
                    'preserveAspectRatio="xMidYMid meet" '
                    f'mask="url(#{marker_id})"/></svg>'
                )
            comma = (
                '<span class="sticker-list-comma" aria-hidden="true">'
                f'{ink(",", f"comma-{mode}-{code}-{instance}")}</span>'
                if separator
                else ""
            )
            return f"""
        <span class="sticker-list-entry" data-semantic-separator="{'after' if separator else 'none'}">
            <button type="button" class="sticker-list-item" data-list-mode="{mode}" data-code="{code}" data-display="{label}" aria-pressed="false" data-marker-family="{marker_family}" data-marker-variant="{marker['variant']}"{instance_attr}>
                {ink(label, f"code-{mode}-{code}-{instance}")}
                {marker_svg}
            </button>{comma}
        </span>
        """

        def sticker_list_group_key(code):
            normalized = deps.display_code(code)
            match = re.match(r"([A-Za-z]+)", normalized)
            return match.group(1) if match else normalized

        def grouped_list_html(mode):
            parts = []
            grouped_items = []
            current_group = None
            current_items = []

            for code in codes:
                group = sticker_list_group_key(code)
                availability = by_code[code].availability if code in by_code else None
                if mode == "get":
                    amount = (
                        1
                        if availability is None or availability.physical == 0
                        else 0
                    )
                else:
                    amount = availability.available if availability else 0

                if (
                    current_group is not None
                    and group != current_group
                    and current_items
                ):
                    grouped_items.append((current_group, current_items))
                    current_items = []

                current_group = group
                for index in range(amount):
                    current_items.append((code, index + 1))

            if current_group is not None and current_items:
                grouped_items.append((current_group, current_items))

            for group_index, (_group, items) in enumerate(grouped_items):
                if group_index:
                    parts.append(
                        '<span class="sticker-list-team-break" '
                        'aria-hidden="true"></span>'
                    )
                for item_index, (code, instance) in enumerate(items):
                    parts.append(
                        list_item(
                            code,
                            mode,
                            instance,
                            item_index < len(items) - 1,
                        )
                    )

            return "".join(parts)

        sticker_list_prefixes = {
            sticker_list_group_key(code)
            for code in codes
            if re.match(r"[A-Za-z]+", deps.display_code(code))
        }
        if len(sticker_list_prefixes) > 1:
            missing_html = grouped_list_html("get")
            duplicate_html = grouped_list_html("give")
        else:

            def numeric_list_key(code):
                label = deps.display_code(code)
                match = re.search(r"\d+", label)
                return (int(match.group()) if match else float("inf"), label)

            sorted_missing_codes = sorted(missing_codes, key=numeric_list_key)
            sorted_duplicate_codes = sorted(duplicate_codes, key=numeric_list_key)
            missing_html = "".join(
                list_item(
                    code,
                    "get",
                    1,
                    position < len(sorted_missing_codes) - 1,
                )
                for position, code in enumerate(sorted_missing_codes)
            )
            duplicate_items = [
                (code, index + 1)
                for code in sorted_duplicate_codes
                for index in range(by_code[code].availability.available)
            ]
            duplicate_html = "".join(
                list_item(
                    code,
                    "give",
                    instance,
                    position < len(duplicate_items) - 1,
                )
                for position, (code, instance) in enumerate(duplicate_items)
            )

        missing_empty = (
            '<p class="sticker-list-empty">Keine fehlenden Sticker.</p>'
            if not missing_codes
            else ""
        )
        duplicate_empty = (
            '<p class="sticker-list-empty">Keine doppelten Sticker.</p>'
            if not duplicate_codes
            else ""
        )
        notice = deps.feedback_html(
            message,
            "/undo"
            if "Transfer durchgeführt" in message
            or "Transfer gespeichert" in message
            else None,
        )

        return render_template(
            "sticker_list.html",
            global_head=deps.global_head(),
            trophy_popup=deps.consume_trophy_popup_html(album_id),
            notice=notice,
            album_id=escape(album_id, quote=True),
            wordmark=deps.app_header_brand_wordmark(),
            album_name=ink(album["name"], "album-title"),
            back_label=ink("Zurück zum Album", "back"),
            stats=(
                ink(f"{gesammelt} gesammelt", "summary-a")
                + middle_dot("summary-dot-a")
                + ink(f"{missing_count} fehlend", "summary-b")
                + middle_dot("summary-dot-b")
                + ink(f"{doppelte} doppelt", "summary-c")
            ),
            missing_heading=ink("Fehlende Sticker", "missing-heading"),
            duplicate_heading=ink("Doppelte Sticker", "duplicate-heading"),
            missing_html=missing_html,
            duplicate_html=duplicate_html,
            missing_empty=missing_empty,
            duplicate_empty=duplicate_empty,
            review_get=ink("Du bekommst", "review-get"),
            review_give=ink("Du gibst ab", "review-give"),
            review_title=ink("Auswahl prüfen", "review-title"),
            review_edit=bracket("Bearbeiten", "review-edit", "close", 0),
            review_confirm=bracket(
                "Bestätigen", "review-confirm", "submit", 1
            ),
            trade_heading=ink("Aktueller Tausch", "trade-heading"),
            clear_label=ink("Leeren", "clear"),
            review_button=bracket(
                "Auswahl prüfen", "review-button", "open-review", 0
            ),
            mixing_seed=escape(deps.ceoklaue_mixing_seed, quote=True),
            bottom_navigation=deps.bottom_nav("sammlung"),
        )

    def stickerliste_trade(album_id):
        get_codes = [
            deps.resolve_code(album_id, code)
            for code in request.form.getlist("get_codes")
        ]
        give_codes = [
            deps.resolve_code(album_id, code)
            for code in request.form.getlist("give_codes")
        ]
        get_codes = [code for code in get_codes if code]
        give_codes = [code for code in give_codes if code]
        list_url = f"/album/{album_id}/liste"

        if not get_codes and not give_codes:
            return redirect(
                f"{list_url}?message="
                f"{quote('Bitte markiere mindestens einen Sticker für diesen Transfer.')}"
            )

        vorher_erreicht = deps.reached_trophies(album_id)
        mutation_key = deps.history_request_event_key("sticker-list-paper-trade")

        con = deps.get_db()
        user_id = deps.current_user_id()
        inventory = InventoryReadService(con).album(user_id, album_id)
        give_counts = {}
        for code in give_codes:
            give_counts[code] = give_counts.get(code, 0) + 1

        for code, amount in give_counts.items():
            if (
                amount
                > inventory.availability_snapshot_for(code).effective_available
            ):
                con.close()
                return redirect(
                    f"{list_url}?message="
                    f"{quote('Ein abgegebener Sticker ist nicht mehr ausreichend doppelt vorhanden.')}"
                )

        for index, code in enumerate(give_codes):
            deps.remove_sticker_quantity(
                con,
                user_id,
                album_id,
                code,
                history_event_key=f"{mutation_key}:give:{index}:{code}",
                history_source_type="paper_trade",
            )

        for index, code in enumerate(get_codes):
            deps.add_sticker_quantity(
                con,
                user_id,
                album_id,
                code,
                history_event_key=f"{mutation_key}:receive:{index}:{code}",
                history_source_type="paper_trade",
            )

        con.commit()
        con.close()

        nachher_erreicht = deps.reached_trophies(album_id)
        neue_trophies = deps.record_trophy_unlocks(
            album_id,
            [trophy for trophy in nachher_erreicht if trophy not in vorher_erreicht],
            silent_reached=vorher_erreicht,
        )
        deps.queue_trophy_popup(album_id, neue_trophies)

        session["last_action"] = {
            "action": "transfer",
            "album_id": album_id,
            "get_codes": get_codes,
            "give_codes": give_codes,
            "filter": "all",
        }

        message = (
            f"Transfer gespeichert: {len(get_codes)} erhalten, "
            f"{len(give_codes)} abgegeben."
        )
        return redirect(f"{list_url}?message={quote(message)}")

    app.add_url_rule(
        "/album/<album_id>/liste",
        endpoint="stickerliste",
        view_func=stickerliste,
    )
    app.add_url_rule(
        "/album/<album_id>/stickerliste",
        endpoint="stickerliste_alias",
        view_func=stickerliste,
    )
    app.add_url_rule(
        "/album/<album_id>/liste/trade",
        endpoint="stickerliste_trade",
        view_func=stickerliste_trade,
        methods=["POST"],
    )
    app.add_url_rule(
        "/album/<album_id>/stickerliste/trade",
        endpoint="stickerliste_trade_alias",
        view_func=stickerliste_trade,
        methods=["POST"],
    )
    return stickerliste, stickerliste_trade

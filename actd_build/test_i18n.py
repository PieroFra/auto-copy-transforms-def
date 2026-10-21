# -*- coding: utf-8 -*-
"""Test headless delle traduzioni italiano/inglese della UI."""

import os
import sys
import traceback

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import auto_copy_transforms_def as addon  # noqa: E402

OK, FAIL = [], []


class _FakeLayout:
    """Layout finto per i test: registra label, split e righe della UIList.

    Permette di verificare `ACTD_UL_mapping.draw_item` in headless, senza una
    sessione grafica: ogni chiamata finisce in `record` come tupla
    (tipo, valore, icona).
    """

    def __init__(self, record):
        self._record = record
        self._alignment = 'EXPAND'

    @property
    def alignment(self):
        return self._alignment

    @alignment.setter
    def alignment(self, value):
        self._alignment = value
        self._record.append(("alignment", value, None))

    def label(self, text="", icon='NONE', **kwargs):
        self._record.append(("label", text, icon))
        return self

    def box(self):
        self._record.append(("box", None, None))
        return _FakeLayout(self._record)

    def operator(self, idname, text="", icon='NONE', **kwargs):
        op = _FakeOperator()
        self._record.append(("operator", idname, text, icon, op))
        return op

    def row(self, align=False, **kwargs):
        self._record.append(("row", align, None))
        return _FakeLayout(self._record)

    def column(self, align=False, **kwargs):
        # La UIList impila le voci di una sola riga: `column` è ciò che
        # permette le due righe per voce, quindi va tracciata nei test.
        self._record.append(("column", align, None))
        return _FakeLayout(self._record)

    def split(self, factor=0.0, align=False, percentage=0.0, **kwargs):
        self._record.append(("split", factor, None))
        return _FakeLayout(self._record)


class _FakeItem:
    """Riga minima con la stessa interfaccia di `ACTD_MappingItem`."""

    def __init__(self, source_name, dest_name, status):
        self.source_name = source_name
        self.dest_name = dest_name
        self.status = status


class _FakeOperator:
    """Operatore finto per verificare URL e testo dei link del popup."""

    def __init__(self):
        self.url = None


class _FakePanel:
    """Sostituto di `self` per chiamare `draw` in headless."""

    def __init__(self, record):
        self.layout = _FakeLayout(record)


def _draw_info_popup():
    """Esegue il draw del popup informazioni e restituisce il registrato."""
    record = []
    addon.ACTD_OT_show_info.draw(_FakePanel(record), None)
    return record


def _draw_mapping(item):
    """Esegue draw_item con il layout finto e restituisce il registrato."""
    record = []
    addon.ACTD_UL_mapping.draw_item(
        None, None, _FakeLayout(record), None, item, 'NONE',
        None, "preview_index",
    )
    return record



def check(name, cond, extra=""):
    (OK if cond else FAIL).append(
        name + ("" if cond else "  [" + str(extra) + "]")
    )
    print(
        ("  OK   " if cond else "  FAIL ") + name
        + ("" if cond else "  [" + str(extra) + "]"),
        flush=True,
    )


print("===== TEST I18N =====", flush=True)
addon.register()
original_language = bpy.context.preferences.view.language

try:
    bpy.context.preferences.view.language = 'en_US'
    check("locale inglese attivo",
          bpy.app.translations.locale.lower().startswith("en"),
          bpy.app.translations.locale)
    check("_is_english_ui() vero", addon._is_english_ui() is True)
    check("traduzione etichetta token",
          bpy.app.translations.pgettext("Token di mappatura") == "Mapping tokens",
          bpy.app.translations.pgettext("Token di mappatura"))
    check("traduzione pulsante Applica",
          bpy.app.translations.pgettext("Applica constraint")
          == "Apply constraints")
    # Avvio rapido: ora sono due etichette separate, ciascuna con la sua chiave.
    check("traduzione avvio rapido riga 1",
          bpy.app.translations.pgettext("1. Scegli i token")
          == "1. Choose tokens",
          bpy.app.translations.pgettext("1. Scegli i token"))
    check("traduzione avvio rapido riga 2",
          bpy.app.translations.pgettext("2. Anteprima  3. Applica")
          == "2. Preview  3. Apply",
          bpy.app.translations.pgettext("2. Anteprima  3. Applica"))
    # Etichette corte delle righe spazio/owner: non tradotte e entro 10 caratteri.
    for _space_label in ("Src", "Dest"):
        check(f"etichetta spazio '{_space_label}' corta e non tradotta",
              bpy.app.translations.pgettext(_space_label) == _space_label
              and len(bpy.app.translations.pgettext(_space_label)) <= 10,
              bpy.app.translations.pgettext(_space_label))
    check("traduzione proprietà (contesto Property)",
          bpy.app.translations.pgettext(
              "Token sorgente (Target)", "Property")
          == "Source token (Target)")
    check("etichetta destinazione completa e tradotta",
          bpy.app.translations.pgettext(
              "Destinazione (Owner)", "Property")
          == "Destination (Owner)",
          bpy.app.translations.pgettext(
              "Destinazione (Owner)", "Property"))
    check("etichetta umana del profilo Discord tradotta",
          bpy.app.translations.pgettext("Profilo Discord")
          == "Discord profile",
          bpy.app.translations.pgettext("Profilo Discord"))
    preset_note_en = bpy.app.translations.pgettext(
        "Preset '%s' disabilitato: coincide con la sorgente."
    ) % "DEF_*"
    check("nota preset tradotta in inglese",
          preset_note_en
          == "Preset 'DEF_*' disabled: matches the source token.",
          preset_note_en)
    check("nota Learn tradotta in inglese",
          bpy.app.translations.pgettext(
              "Serve un osso in Pose Mode con un constraint di copia")
          == "Needs a bone in Pose Mode with a copy constraint",
          bpy.app.translations.pgettext(
              "Serve un osso in Pose Mode con un constraint di copia"))
    # Ogni riga delle note spezzate deve stare nella larghezza della UI.
    note_en_lines = addon._ui_report_lines(
        bpy.app.translations.pgettext(
            "Serve un osso in Pose Mode con un constraint di copia"))
    check("nota Learn EN: righe entro la larghezza della UI",
          bool(note_en_lines)
          and all(len(r) <= addon._UI_TEXT_WIDTH for r in note_en_lines),
          note_en_lines)

    popup_en = _draw_info_popup()
    discord_en = [
        r for r in popup_en
        if r[0] == "operator" and r[2] == "Discord profile"
    ]
    check("popup EN: link Discord con etichetta umana",
          len(discord_en) == 1 and discord_en[0][3] == 'URL', discord_en)
    check("popup EN: URL Discord cliccabile",
          len(discord_en) == 1
          and discord_en[0][4].url == addon.DISCORD_URL,
          discord_en)
    check("popup EN: ID numerico non mostrato",
          all(addon.DISCORD_ID not in (r[1] or "")
              for r in popup_en if r[0] == "label"),
          [r[1] for r in popup_en if r[0] == "label"][:6])
    check("traduzione creatore",
          bpy.app.translations.pgettext("Creatore: ") == "Creator: ")
    check("traduzione nota AI",
          bpy.app.translations.pgettext("Sviluppato con assistenza AI")
          == "Developed with AI assistance")
    report = "Coppie valide: 3\nOssa sorgente senza match: 0"
    check("report tradotto in inglese",
          addon._translate_report_text(report)
          == "Valid pairs: 3\nSource bones without match: 0",
          addon._translate_report_text(report))

    # Messaggi della diagnostica e prefissi di livello
    check("diagnostica tradotta (testo dinamico)",
          addon._translate_report_text(
              "3 ossa ambigue (DEF-a, DEF-b). Con 'Risolvi ambiguità' "
              "l'addon sceglie automaticamente."
          ).startswith("3 ambiguous bones (DEF-a, DEF-b)."),
          addon._translate_report_text(
              "3 ossa ambigue (DEF-a, DEF-b). Con 'Risolvi ambiguità' "
              "l'addon sceglie automaticamente."
          ))
    check("prefisso [ERROR] conservato con messaggio tradotto",
          addon._translate_report_text("[ERROR] Nessuna armatura attiva.")
          == "[ERROR] No active armature.",
          addon._translate_report_text("[ERROR] Nessuna armatura attiva."))
    check("prefisso [WARNING] conservato con messaggio tradotto",
          addon._translate_report_text(
              "[WARNING] Armatura sorgente non valida."
          ) == "[WARNING] Source armature is not valid.",
          addon._translate_report_text(
              "[WARNING] Armatura sorgente non valida."
          ))
    check("prefisso [INFO] conservato con messaggio tradotto",
          addon._translate_report_text(
              "[INFO] Spazio consigliato: WORLD (gerarchie miste: WORLD è "
              "il compromesso più sicuro). Attuale: LOCAL."
          ) == ("[INFO] Suggested space: WORLD (mixed hierarchies: WORLD is "
                "the safest compromise). Current: LOCAL."),
          addon._translate_report_text(
              "[INFO] Spazio consigliato: WORLD (gerarchie miste: WORLD è "
              "il compromesso più sicuro). Attuale: LOCAL."
          ))

    # Helper di wrapping usato dai pannelli
    righe = addon._ui_report_lines(
        "Report salvato in: C:\\tmp\\actd_export_2026.csv\nRighe esportate: 3",
        width=24,
    )
    check("righe di report spezzate per la UI",
          len(righe) > 2 and all(len(r) <= 24 for r in righe), righe)
    check("testo vuoto non produce label",
          addon._ui_report_lines("") == [])

    # --- Lista di mappatura: stato tradotto e nomi non troncati ---
    check("STATUS_META resta una tabella unica in italiano",
          addon.STATUS_META['match'] == ("OK", 'CHECKMARK')
          and addon.STATUS_META['resolved'] == ("Risolto", 'INFO')
          and addon.STATUS_META['ambiguous'] == ("Ambiguo", 'ERROR')
          and addon.STATUS_META['unmatched_src'] == ("Senza match", 'CANCEL')
          and addon.STATUS_META['unmatched_dst'] == ("Senza match", 'CANCEL'),
          addon.STATUS_META)
    check("stati tradotti in inglese (nessun residuo italiano)",
          all(
              bpy.app.translations.pgettext(addon.STATUS_META[s][0])
              != addon.STATUS_META[s][0]
              for s in ('resolved', 'ambiguous', 'unmatched_src',
                        'unmatched_dst')
          ),
          [bpy.app.translations.pgettext(addon.STATUS_META[s][0])
           for s in ('resolved', 'ambiguous', 'unmatched_src', 'unmatched_dst')])
    check("stato 'match' identico nelle due lingue",
          bpy.app.translations.pgettext("OK") == "OK")
    check("etichetta 'Senza match' tradotta",
          bpy.app.translations.pgettext("Senza match") == "No match",
          bpy.app.translations.pgettext("Senza match"))

    attese_en = {
        'match': ("OK", 'CHECKMARK'),
        'resolved': ("Resolved", 'INFO'),
        'ambiguous': ("Ambiguous", 'ERROR'),
        'unmatched_src': ("No match", 'CANCEL'),
        'unmatched_dst': ("No match", 'CANCEL'),
        'sconosciuto': ("?", 'QUESTION'),
    }
    for stato, attesa in attese_en.items():
        dati = addon._mapping_row_data(_FakeItem("DEF-a", "MCH-a", stato))
        check(f"riga di mappatura in inglese: {stato}",
              dati == ("DEF-a", "MCH-a", attesa[0], attesa[1]), dati)
    check("nomi assenti sostituiti da trattino",
          addon._mapping_row_data(_FakeItem("", "", 'match'))
          == ("-", "-", "OK", 'CHECKMARK'),
          addon._mapping_row_data(_FakeItem("", "", 'match')))

    riga_en = _draw_mapping(_FakeItem("DEF-upper_arm.L", "MCH-upper_arm.L",
                                       'resolved'))
    label_en = [r for r in riga_en if r[0] == "label"]
    split_en = [r for r in riga_en if r[0] == "split"]
    check("lista di mappatura: due righe in una column, nessuno split",
          len(split_en) == 0 and len(label_en) == 2
          and ("column", True, None) in riga_en, riga_en)
    check("sorgente su riga intera con icona di stato",
          label_en[0] == ("label", "DEF-upper_arm.L", 'INFO'), label_en)
    check("destinazione e stato sulla seconda riga, senza colonne fisse",
          label_en[1] == ("label", "→ MCH-upper_arm.L  ·  Resolved", 'NONE'),
          label_en)
    riga_item = _FakeItem("DEF-a", "MCH-a", 'ambiguous')
    _draw_mapping(riga_item)
    check("draw_item non altera i dati della riga",
          (riga_item.source_name, riga_item.dest_name, riga_item.status)
          == ("DEF-a", "MCH-a", 'ambiguous'),
          (riga_item.source_name, riga_item.dest_name, riga_item.status))

    check("README inglese disponibile",
          bool(addon.README_TEXT_EN.strip())
          and "Creates copy constraints" in addon.README_TEXT_EN)
    check("licenza inglese disponibile",
          bool(addon.LICENSE_NOTICE_EN.strip()))

    bpy.context.preferences.view.language = 'it_IT'
    check("locale italiano attivo",
          not bpy.app.translations.locale.lower().startswith("en"),
          bpy.app.translations.locale)
    check("_is_english_ui() falso", addon._is_english_ui() is False)
    check("etichetta destinazione in italiano",
          bpy.app.translations.pgettext("Destinazione (Owner)")
          == "Destinazione (Owner)")
    preset_note_it = bpy.app.translations.pgettext(
        "Preset '%s' disabilitato: coincide con la sorgente."
    ) % "DEF_*"
    check("nota preset in italiano invariata",
          preset_note_it
          == "Preset 'DEF_*' disabilitato: coincide con la sorgente.",
          preset_note_it)
    check("nota Learn in italiano invariata",
          bpy.app.translations.pgettext(
              "Serve un osso in Pose Mode con un constraint di copia")
          == "Serve un osso in Pose Mode con un constraint di copia",
          bpy.app.translations.pgettext(
              "Serve un osso in Pose Mode con un constraint di copia"))
    note_it_lines = addon._ui_report_lines(
        bpy.app.translations.pgettext(
            "Serve un osso in Pose Mode con un constraint di copia"))
    check("nota Learn IT: righe entro la larghezza della UI",
          bool(note_it_lines)
          and all(len(r) <= addon._UI_TEXT_WIDTH for r in note_it_lines),
          note_it_lines)
    preset_it_lines = addon._ui_report_lines(preset_note_it)
    check("nota preset IT: righe entro la larghezza della UI",
          bool(preset_it_lines)
          and all(len(r) <= addon._UI_TEXT_WIDTH for r in preset_it_lines),
          preset_it_lines)
    popup_it = _draw_info_popup()
    discord_it = [
        r for r in popup_it
        if r[0] == "operator" and r[2] == "Profilo Discord"
    ]
    check("popup IT: link Discord con etichetta umana",
          len(discord_it) == 1 and discord_it[0][3] == 'URL', discord_it)
    check("popup IT: URL Discord cliccabile",
          len(discord_it) == 1
          and discord_it[0][4].url == addon.DISCORD_URL,
          discord_it)
    testi_popup = [
        r[1] for r in popup_it if r[0] == "label"
    ] + [
        r[2] for r in popup_it if r[0] == "operator"
    ]
    check("popup IT: nessun ID Discord numerico visibile",
          all(addon.DISCORD_ID not in (t or "") for t in testi_popup),
          testi_popup[:6])
    check("sorgente italiana invariata",
          bpy.app.translations.pgettext("Token di mappatura")
          == "Token di mappatura")
    check("report italiano invariato",
          addon._translate_report_text(
              "Coppie valide: 3\nOssa sorgente senza match: 0"
          ) == "Coppie valide: 3\nOssa sorgente senza match: 0")
    check("diagnostica italiana invariata",
          addon._translate_report_text("[ERROR] Nessuna armatura attiva.")
          == "[ERROR] Nessuna armatura attiva.",
          addon._translate_report_text("[ERROR] Nessuna armatura attiva."))
    check("wrapping identico nelle due lingue",
          addon._ui_report_lines("[ERROR] Nessuna armatura attiva.", width=20)
          == ['[ERROR] Nessuna', 'armatura attiva.'],
          addon._ui_report_lines("[ERROR] Nessuna armatura attiva.", width=20))

    # --- Lista di mappatura in italiano: nessun residuo inglese ---
    attese_it = {
        'match': ("OK", 'CHECKMARK'),
        'resolved': ("Risolto", 'INFO'),
        'ambiguous': ("Ambiguo", 'ERROR'),
        'unmatched_src': ("Senza match", 'CANCEL'),
        'unmatched_dst': ("Senza match", 'CANCEL'),
        'sconosciuto': ("?", 'QUESTION'),
    }
    for stato, attesa in attese_it.items():
        dati = addon._mapping_row_data(_FakeItem("DEF-a", "MCH-a", stato))
        check(f"riga di mappatura in italiano: {stato}",
              dati == ("DEF-a", "MCH-a", attesa[0], attesa[1]), dati)

    riga_it = _draw_mapping(_FakeItem("DEF_collo", "MCH_collo", 'resolved'))
    label_it = [r for r in riga_it if r[0] == "label"]
    check("lista di mappatura italiana: nomi e stato",
          label_it == [("label", "DEF_collo", 'INFO'),
                       ("label", "→ MCH_collo  ·  Risolto", 'NONE')],
          label_it)
    check("riga di mappatura identica a meno dello stato",
          [r for r in riga_it if r[0] in ("column", "split", "alignment")]
          == [r for r in riga_en if r[0] in ("column", "split", "alignment")],
          [r for r in riga_it if r[0] in ("column", "split", "alignment")])
except Exception:
    traceback.print_exc()
    FAIL.append("ECCEZIONE: " + traceback.format_exc().strip().splitlines()[-1])
finally:
    bpy.context.preferences.view.language = original_language

print("\n===== RIEPILOGO TEST I18N =====", flush=True)
print("Passati: %d" % len(OK), flush=True)
print("Falliti: %d" % len(FAIL), flush=True)
for f in FAIL:
    print("  - " + f, flush=True)
print("RISULTATO: " + ("SUPERATO" if not FAIL else "FALLITO"), flush=True)

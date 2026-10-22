# MODULO actd_logic.py — logica dei preset di destinazione (intestazione di build, non fa parte del monolite)


# =============================================================================
#  PRESET DEL TOKEN DESTINAZIONE
# =============================================================================

# Preset del token destinazione mostrati nella UI: (testo, token, tipo).
# La tabella resta una sola: la usano il menu a tendina e l'operatore storico.
_DEST_PRESETS = (
    ("MCH_", "MCH_", 'PREFIX'),
    ("ORG_", "ORG_", 'PREFIX'),
    ("DEF_", "DEF_", 'PREFIX'),
    ("_ctrl", "_ctrl", 'SUFFIX'),
)

# Voci statiche dell'EnumProperty del menu preset. Sono fisse (non una callback
# dinamica) perche' Blender 5.2 rifiuta la registrazione degli enum con items
# da callback nelle PropertyGroup; l'identificatore e' il token stesso.
DEST_PRESET_ITEMS = [
    (token, label, f"Token destinazione {token}")
    for label, token, _t in _DEST_PRESETS
]


def _dest_preset_is_self_match(settings, preset, token_type):
    """True se il preset coinciderebbe con il token sorgente attivo.

    Un preset uguale alla sorgente (stesso token e stesso tipo) porterebbe a
    mappare ogni osso su se stesso: la UI lo nasconde, senza rimuovere
    l'operatore.
    """
    if settings is None:
        return False
    # `self` puo' non essere ancora un'istanza valida durante la registrazione:
    # qualsiasi accesso fallito vale "non e' un conflitto".
    try:
        source = (getattr(settings, "source_token", "") or "").strip()
        source_type = getattr(settings, "source_token_type", 'PREFIX')
    except Exception:
        return False
    return bool(source) and source == preset and source_type == token_type


def _dest_preset_token_type(preset):
    """Tipo (prefisso/suffisso) associato a un preset, PREFIX se sconosciuto."""
    for _label, token, token_type in _DEST_PRESETS:
        if token == preset:
            return token_type
    return 'PREFIX'


def _apply_dest_preset(settings, preset, token_type):
    """Imposta token e tipo destinazione da un preset (uso unico in UI)."""
    if settings is None or not preset:
        return
    settings.dest_token = preset
    settings.dest_token_type = token_type


def _on_dest_preset_chosen(self, context):
    """Update del menu preset: applica il token scelto alla destinazione.

    Se il preset coincide con il token sorgente attivo (stesso token e stesso
    tipo) la mappatura porterebbe ogni osso su se stesso: in quel caso il
    token destinazione resta invariato e la UI mostra un avviso tradotto.
    """
    settings = None
    scene = getattr(context, "scene", None)
    if scene is not None:
        settings = getattr(scene, "actd_settings", None)
    if settings is None:
        settings = self
    preset = getattr(self, "dest_preset_choice", "")
    token_type = _dest_preset_token_type(preset)
    if _dest_preset_is_self_match(settings, preset, token_type):
        # Il template si traduce prima della sostituzione: la chiave contiene
        # il segnaposto %s, cosi' la UI inglese usa la voce in _EN_TRANSLATIONS.
        template = "Preset '%s' coincide con il token sorgente: non applicato"
        try:
            template = bpy.app.translations.pgettext_iface(template) or template
        except Exception:
            pass
        settings.dest_preset_notice = template % preset
        return
    _apply_dest_preset(settings, preset, token_type)
    settings.dest_preset_notice = ""


# =============================================================================
#  PROPERTY GROUPS
# =============================================================================

def _mark_preview_stale(self, context):
    self.preview_is_stale = True

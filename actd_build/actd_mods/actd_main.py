# MODULO actd_main.py — registrazione classi, register/unregister e avvio (intestazione di build, non fa parte del monolite)


# =============================================================================
#  REGISTRAZIONE
# =============================================================================

_classes = (
    #  I PropertyGroup referenziati da CollectionProperty/PointerProperty
    #  devono stare PRIMA di chi li usa, altrimenti la registrazione fallisce
    #  con "missing bl_rna attribute from '_RNAMetaPropGroup' instance".
    ACTD_DiagnosticItem,
    ACTD_MappingItem,
    ACTD_Settings,
    ACTD_UL_mapping,
    ACTD_OT_dest_preset,
    ACTD_OT_set_source_object,
    ACTD_OT_refresh_constraint_name,
    ACTD_OT_guess_prefixes,
    ACTD_OT_learn_pattern,
    ACTD_OT_preview,
    ACTD_OT_apply,
    ACTD_OT_remove,
    ACTD_OT_clean_registry,
    ACTD_OT_diagnose,
    ACTD_OT_convert_to_manual,
    ACTD_OT_mute_all,
    ACTD_OT_export_csv,
    ACTD_OT_export_json,
    ACTD_OT_show_info,
    ACTD_PT_main,
    ACTD_PT_advanced,
    ACTD_PT_maintenance,
    ACTD_PT_diagnostics,
    ACTD_PT_preview,
)


def _registration_order():
    """Ordina le classi mettendo prima le PropertyGroup referenziate.

    Rete di sicurezza contro il caso in cui una PropertyGroup usata da una
    CollectionProperty non sia elencata in _classes: senza questo controllo la
    registrazione fallisce con un errore poco leggibile.
    """
    order = list(_classes)
    deps = []
    for cls in order:
        annotations = getattr(cls, "__annotations__", {}) or {}
        for prop in annotations.values():
            keywords = getattr(prop, "keywords", None)
            if not isinstance(keywords, dict):
                continue
            dep = keywords.get("type")
            if (
                isinstance(dep, type)
                and issubclass(dep, bpy.types.PropertyGroup)
                and dep not in order
                and dep not in deps
            ):
                deps.append(dep)
    return tuple(deps) + tuple(order)


def _class_is_registered(cls):
    """True se la classe e' gia' registrata in Blender (reload / doppio register)."""
    try:
        return bool(getattr(cls, "is_registered", False))
    except Exception:
        return False


def register():
    registered = []
    try:
        _register_translations()
        for cls in _registration_order():
            if _class_is_registered(cls):
                continue
            try:
                bpy.utils.register_class(cls)
            except ValueError as exc:
                # Classe registrata da una sessione precedente dell'addon:
                # non e' un errore, la consideriamo gia' a posto.
                if "already registered" not in str(exc):
                    raise
                continue
            registered.append(cls)

        if not hasattr(bpy.types.Scene, "actd_settings"):
            bpy.types.Scene.actd_settings = PointerProperty(type=ACTD_Settings)
    except Exception:
        if hasattr(bpy.types.Scene, "actd_settings"):
            try:
                del bpy.types.Scene.actd_settings
            except Exception:
                pass
        for cls in reversed(registered):
            try:
                bpy.utils.unregister_class(cls)
            except Exception:
                pass
        _unregister_translations()
        raise


def unregister():
    _unregister_translations()
    if hasattr(bpy.types.Scene, "actd_settings"):
        try:
            del bpy.types.Scene.actd_settings
        except Exception:
            pass

    for cls in reversed(_registration_order()):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass


if __name__ == "__main__":
    register()
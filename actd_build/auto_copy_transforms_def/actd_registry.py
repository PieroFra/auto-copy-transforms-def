# --- inizio blocco generato dalla build (non modificare a mano) ---
# Importa i nomi dei moduli precedenti del pacchetto: nel monolite erano
# nello stesso spazio dei nomi, qui vanno riportati a mano.
import importlib as _actd_imp

_actd_prec = ("actd_header", "actd_i18n", "actd_tokens",)
for _actd_nome in _actd_prec:
    for _actd_k, _actd_v in vars(
            _actd_imp.import_module("." + _actd_nome, __package__)).items():
        if not _actd_k.startswith("__"):
            globals().setdefault(_actd_k, _actd_v)
del _actd_imp, _actd_prec, _actd_nome, _actd_k, _actd_v
# --- fine blocco generato dalla build ---



# --- Marcatura dei constraint generati -------------------------------------
# I Constraint NON supportano le ID properties (con['x'] = y solleva
# "id properties not supported for this type"), quindi il marcatore non puo'
# stare sul constraint. Usiamo un registro JSON salvato sull'armatura
# destinazione: {osso_dest: {nome_constraint: {"obj": ..., "bone": ...}}}.
_GENERATED_PROP = 'actd_generated'


def _read_registry(owner):
    """Legge il registro dei constraint generati dall'addon."""
    if owner is None:
        return {}
    try:
        raw = owner.get(_GENERATED_PROP)
    except Exception:
        return {}
    if not raw:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    try:
        data = json.loads(raw)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _write_registry(owner, data):
    """Scrive il registro, rimuovendo la proprieta' quando e' vuoto."""
    if owner is None:
        return
    try:
        if data:
            owner[_GENERATED_PROP] = json.dumps(data, sort_keys=True)
        elif _GENERATED_PROP in owner:
            del owner[_GENERATED_PROP]
    except Exception:
        pass


def _mark_generated(owner, pose_bone, con, src_obj, src_bone):
    """Registra un constraint come generato dall'addon.

    Prima di scrivere la voce corrente elimina gli alias di rinomina della
    stessa origine (stesso target/osso e nome non piu' presente tra i
    constraint dell'osso): il registro resta coerente dopo un UPDATE che
    rinomina un constraint generato.
    """
    reg = _read_registry(owner)
    bones = reg.setdefault(pose_bone.name, {})
    presenti = {c.name for c in pose_bone.constraints}
    src_name = src_obj.name if src_obj is not None else ""
    alias = [
        nome for nome, voce in bones.items()
        if nome not in presenti
        and isinstance(voce, dict)
        and voce.get("bone") == src_bone
        and voce.get("type") == con.type
        and (not voce.get("obj") or voce.get("obj") == src_name)
    ]
    for nome in alias:
        bones.pop(nome, None)
    bones[con.name] = {
        "obj": src_name,
        "bone": src_bone,
        "type": con.type,
    }
    _write_registry(owner, reg)


def _forget_generated(owner, pose_bone, con_name):
    """Rimuove una voce dal registro."""
    reg = _read_registry(owner)
    bones = reg.get(pose_bone.name)
    if not bones or con_name not in bones:
        return
    bones.pop(con_name, None)
    if not bones:
        reg.pop(pose_bone.name, None)
    _write_registry(owner, reg)


def _registry_constraint_names(owner, pose_bone):
    """Nomi dei constraint registrati per l'osso (sola lettura).

    Criterio di base condiviso con ``_is_generated`` (che aggiunge il solo
    fallback di rinomina) e con la classificazione REPLACE di
    ``actd_operators``: si legge soltanto il registro e si confrontano i nomi
    dei constraint. Nessuna scrittura durante una lettura: l'aggiornamento del
    registro spetta alle funzioni di marcatura.
    """
    if pose_bone is None:
        return frozenset()
    bones = _read_registry(owner).get(pose_bone.name)
    if not isinstance(bones, dict):
        return frozenset()
    return frozenset(bones.keys())


def _is_generated(owner, pose_bone, con):
    """True se il constraint e' stato creato dall'addon.

    Criterio principale: nome del constraint presente nel registro (lo stesso
    della classificazione REPLACE). In piu' si accetta il caso della rinomina
    manuale: una voce registrata vale come fallback solo se il suo nome non
    esiste piu' tra i constraint dell'osso (altrimenti sarebbe un omonimo
    manuale) e se target/subtarget coincidono. La lettura non scrive mai nel
    registro: l'allineamento spetta a ``_mark_generated``.
    """
    bones = _read_registry(owner).get(pose_bone.name)
    if not isinstance(bones, dict) or not bones:
        return False
    if con.name in bones:
        return True
    presenti = {c.name for c in pose_bone.constraints}
    target_obj = getattr(con, "target", None)
    target_name = target_obj.name if target_obj is not None else ""
    for old_name, entry in bones.items():
        if old_name in presenti or not isinstance(entry, dict):
            continue
        if entry.get("bone") != getattr(con, "subtarget", ""):
            continue
        if entry.get("obj") and entry.get("obj") != target_name:
            continue
        return True
    return False


def _constraint_subtarget_valid(con):
    """True se il subtarget del constraint esiste ancora nell'armatura target."""
    subtarget = getattr(con, "subtarget", "")
    if not subtarget:
        return True
    target = getattr(con, "target", None)
    if target is None or getattr(target, "type", None) != 'ARMATURE':
        return False
    # In Edit Mode le ossa non sono ancora nella collezione data.bones:
    # non e' un errore, si rimanda il controllo.
    if getattr(target, "mode", None) == 'EDIT':
        return True
    try:
        return subtarget in target.data.bones
    except (AttributeError, TypeError):
        return False


def _prune_registry(owner, pose_bones=None):
    """Elimina dal registro le voci orfane o non piu' coerenti.

    Una voce viene rimossa se il constraint non esiste, se il tipo e' cambiato
    rispetto a quello registrato o se il subtarget non esiste piu'.
    """
    reg = _read_registry(owner)
    if not reg:
        return 0
    if pose_bones is None:
        pose_bones = owner.pose.bones if owner is not None else ()
    removed = 0
    for bone_name in list(reg.keys()):
        pose_bone = pose_bones.get(bone_name)
        if pose_bone is None:
            removed += len(reg.pop(bone_name, {}) or {})
            continue
        existing = {con.name: con for con in pose_bone.constraints}
        entries = reg.get(bone_name, {})
        if not isinstance(entries, dict):
            reg.pop(bone_name, None)
            continue
        for con_name in list(entries.keys()):
            con = existing.get(con_name)
            entry = entries.get(con_name)
            stale = con is None
            if not stale:
                registered_type = (
                    entry.get("type") if isinstance(entry, dict) else None
                )
                if registered_type and registered_type != con.type:
                    stale = True
                elif not _constraint_subtarget_valid(con):
                    stale = True
            if stale:
                entries.pop(con_name, None)
                removed += 1
        if not entries:
            reg.pop(bone_name, None)
    _write_registry(owner, reg)
    return removed


def _is_pose_bone_selected(pb) -> bool:
    """Compatibilità selezione PoseBone tra Blender 3.6 (pb.bone.select) e 4.0+/5.x (pb.select)."""
    if hasattr(pb, "select"):
        return bool(pb.select)
    return bool(pb.bone and pb.bone.select)


def _find_all_generated(arm_obj, pose_bone, con_type=None):
    """Ritorna i constraint creati da questo addon sull'osso."""
    return [
        con for con in pose_bone.constraints
        if (con_type is None or con.type == con_type)
        and _is_generated(arm_obj, pose_bone, con)
    ]


def _find_generated_constraint(arm_obj, pose_bone, con_type=None):
    """Ritorna il primo constraint creato da questo addon."""
    generated = _find_all_generated(arm_obj, pose_bone, con_type)
    return generated[0] if generated else None


def _find_matching_copy(pose_bone, target_obj, src_name, settings):
    """Cerca un constraint equivalente a quello che si vorrebbe creare.

    Considera anche il tipo: con Copy Rotation selezionato, un Copy Transforms
    presente sull'osso non e' un duplicato, e viceversa.
    """
    for con in pose_bone.constraints:
        if _configured_constraint_matches(con, target_obj, src_name, settings):
            return con
    return None


def _apply_stack_position(pose_bone, con, settings):
    """Sposta il constraint nella posizione richiesta dentro lo stack dell'osso.

    Blender indicizza lo stack dall'alto: 0 = primo eseguito, vince sugli altri.
    """
    position = getattr(settings, "stack_position", 'BOTTOM') or 'BOTTOM'
    constraints = pose_bone.constraints
    if len(constraints) < 2 or position == 'BOTTOM':
        return

    current_index = constraints.find(con.name)
    if current_index == -1:
        return

    if position == 'TOP':
        target_index = 0
    elif position == 'BEFORE_IK':
        # Primo constraint IK eseguito prima del nostro: ci mettiamo davanti
        target_index = None
        for i, other in enumerate(constraints):
            if other is con:
                continue
            if other.type == 'IK' and i < current_index:
                target_index = i
                break
        if target_index is None:
            return
    else:
        return

    if current_index == target_index:
        return
    constraints.move(current_index, target_index)


def _configure_constraint(con, con_name, target_obj, src_name, settings):
    """Imposta nome, target, subtarget, spazi, influenza e opzioni fini.

    Ritorna una lista di avvisi (stringhe) relativi a opzioni che il tipo di
    constraint scelto non supporta, cosi' l'operatore puo' riportarle.
    """
    warnings = []
    con_type = getattr(con, "type", _constraint_type(settings))

    con.name = con_name
    con.target = target_obj
    con.subtarget = src_name

    try:
        con.target_space = settings.target_space
    except (TypeError, ValueError):
        pass
    try:
        con.owner_space = settings.owner_space
    except (TypeError, ValueError):
        pass

    con.influence = settings.influence

    # --- Modulo 2 + 5: mix adattato al tipo di constraint ---
    mix_value, mix_note = _resolved_mix_mode(settings, con_type)
    if mix_note:
        warnings.append(mix_note)
    if mix_value and mix_value != 'REPLACE':
        try:
            con.mix_mode = mix_value
        except (AttributeError, TypeError, ValueError):
            warnings.append(
                f"Impossibile impostare il mix '{mix_value}' su {con_type}."
            )

    # use_offset autonomo solo su Copy Location/Scale (su Copy Rotation è mix)
    wants_offset = bool(getattr(settings, "use_offset", False))
    if _constraint_supports_offset(con_type):
        try:
            con.use_offset = wants_offset
        except (AttributeError, TypeError, ValueError):
            warnings.append("Impossibile impostare 'Usa offset'.")
    elif wants_offset:
        label = CONSTRAINT_TYPE_LABELS.get(con_type, con_type)
        if _constraint_supports(con_type, "use_offset"):
            warnings.append(
                f"Su {label} 'Usa offset' dipende da Mix: usa 'Mix' = Offset."
            )
        else:
            warnings.append(f"'Usa offset' non esiste su {label}: ignorato.")

    # remove_target_shear esiste solo su Copy Transforms
    if getattr(settings, "remove_target_shear", False):
        if _constraint_supports(con_type, "remove_target_shear"):
            try:
                con.remove_target_shear = True
            except (AttributeError, TypeError, ValueError):
                warnings.append("Impossibile impostare 'Rimuovi shear'.")
        else:
            warnings.append(
                f"'Rimuovi shear' non esiste su "
                f"{CONSTRAINT_TYPE_LABELS.get(con_type, con_type)}: ignorato."
            )

    return warnings


def _configured_constraint_matches(con, target_obj, src_name, settings):
    """True se il constraint esistente corrisponde gia' alla configurazione.

    Usato dal controllo duplicati: se il tipo o le opzioni differiscono, il
    constraint non e' equivalente e va aggiornato o ignorato, non riusato.
    """
    if con.type != _constraint_type(settings):
        return False
    if con.target != target_obj or con.subtarget != src_name:
        return False
    if getattr(con, "owner_space", None) != settings.owner_space:
        return False
    if getattr(con, "target_space", None) != settings.target_space:
        return False
    if not _float_close(con.influence, settings.influence):
        return False

    mix_value, _ = _resolved_mix_mode(settings, con.type)
    if mix_value and getattr(con, "mix_mode", 'REPLACE') != mix_value:
        return False

    wants_offset = bool(getattr(settings, "use_offset", False))
    if _constraint_supports_offset(con.type):
        if bool(getattr(con, "use_offset", False)) != wants_offset:
            return False

    wants_shear = bool(getattr(settings, "remove_target_shear", False))
    if _constraint_supports(con.type, "remove_target_shear"):
        if bool(getattr(con, "remove_target_shear", False)) != wants_shear:
            return False

    return True

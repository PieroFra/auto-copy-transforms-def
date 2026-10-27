# NON MODIFICARE DIRETTAMENTE.
# Generato da packaging\build_package.py - non modificare a mano.
# A.C.T.D. (Auto Copy Transforms DEF) versione 1.2.0
# Edita i moduli in actd_build\actd_mods\ e ricostruisci il pacchetto.
import importlib

_ORDER = (
    "actd_header",
    "actd_i18n",
    "actd_tokens",
    "actd_registry",
    "actd_logic",
    "actd_properties",
    "actd_operators",
    "actd_ui",
    "actd_main",
)

_mods = []
for _name in _ORDER:
    _m = importlib.import_module("." + _name, __name__)
    globals().update(
        {_k: _v for _k, _v in vars(_m).items() if not _k.startswith("__")})
    _mods.append(_m)

# Seconda passata: ogni modulo vede anche i nomi definiti piu' avanti
# nell'ordine, cosi' i riferimenti a runtime si risolvono come nel monolite.
_ns = {_k: _v for _k, _v in globals().items() if not _k.startswith("__")}
for _m in _mods:
    _m.__dict__.update(_ns)
del _m, _mods, _name, _ns

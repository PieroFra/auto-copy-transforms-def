@{
    # Sorgente principale (monolite) e moduli da compilare.
    Monolith      = 'actd_build\auto_copy_transforms_def.py'
    Sources       = @('actd_build\actd_mods')
    # Runner dei test: produce sia la tabella per suite sia il riepilogo.
    Runner        = 'actd_build\run_all_tests.ps1'
    RunnerArgs    = @('-MaxParallel', '8')
    # Totale atteso della regressione completa (12 suite).
    ExpectedTotal = 644
    # Path sui quali viene misurata l'ampiezza del diff.
    DiffPaths     = @('actd_build/actd_mods', 'actd_build/auto_copy_transforms_def.py')
    # Indice AST dei simboli (mappa per l'Architetto).
    IndexOutput   = 'actd_build\INDEX.md'
    # Build step: i moduli sono la fonte di verita', il monolite e' l'artefatto
    # che i test importano. Senza build i test girerebbero su codice vecchio.
    Build         = 'packaging\build_monolith.py'
}

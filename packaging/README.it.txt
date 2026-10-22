AUTO COPY TRANSFORMS DEF v1.1.5
===============================

Creatore: Pierfrancesco Diodato
Discord: https://discord.com/users/1176582483165327382
Licenza: GPL-3.0-or-later


COSA FA
-------
Crea constraint di copia sulle ossa di destinazione (MCH_, ORG_, ecc.)
mappando automaticamente i nomi delle ossa sorgente (DEF_).
Default: COPY_TRANSFORMS, token DEF_ / MCH_.


FUNZIONI PRINCIPALI
-------------------
- Anteprima della mappatura e applicazione dei constraint.
- Tipi Copy Transforms, Copy Rotation, Copy Location, Copy Scale.
- Mix, spazi, influenza, offset e posizione nello stack.
- Filtro per bone collection e solo ossa deform.
- Diagnostica pre-flight del rig.
- Auto-prefisso e apprendimento del pattern da un constraint esistente.
- Manutenzione: converti in manuali, pulisci registro, mute, export CSV/JSON.
- Pulsante "Informazioni / README" nella sidebar con autore, Discord e licenza.


INSTALLAZIONE COME ESTENSIONE (Blender 4.2+ / 5.x)
--------------------------------------------------
1. Apri Blender.
2. Edit > Preferences > Get Extensions.
3. Freccia in alto a destra > "Install from Disk...".
4. Seleziona il file auto_copy_transforms_def-1.1.5.zip.
5. Attiva "Auto Copy Transforms DEF".
6. Nella 3D View premi N e cerca la scheda "Auto Copy Transforms".


INSTALLAZIONE COME ADD-ON CLASSICO (Blender 4.2+ / 5.x)
-------------------------------------------------------
Il file .py standalone legacy è incluso solo nel RAR abbinato, non nello ZIP
dell'estensione.
1. Edit > Preferences > Add-ons.
2. Freccia in alto a destra > "Install from Disk...".
3. Estrai legacy/auto_copy_transforms_def.py dal RAR e selezionalo.
4. Attiva "Rigging: Auto Copy Transforms DEF".


COMPATIBILITA
-------------
Testato ufficialmente solo su Blender 5.2 LTS. Entrambi i percorsi di
installazione (add-on classico e manifest dell'estensione) dichiarano
Blender 4.2+. Blender 4.2-5.1 sono dichiarate compatibili ma non sono state
verificate con le suite documentate.

L'interfaccia segue la lingua di Blender: italiano o inglese.


NOTA SULL'AI
------------
Sviluppato con l'assistenza di AI (OpenCode), sotto la direzione e la
revisione di Pierfrancesco Diodato. L'autore resta responsabile del codice
e dei test.


LICENZA
-------
GPL-3.0-or-later. Il testo completo e' in LICENSE.txt.

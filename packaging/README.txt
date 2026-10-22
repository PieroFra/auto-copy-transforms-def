AUTO COPY TRANSFORMS DEF v1.1.4
===============================

Creator: Pierfrancesco Diodato
Discord: https://discord.com/users/1176582483165327382
License: GPL-3.0-or-later


WHAT IT DOES
------------
Creates copy constraints on destination bones (MCH_, ORG_, ...) by
automatically mapping the names of source bones (DEF_).
Defaults: COPY_TRANSFORMS, tokens DEF_ / MCH_.


MAIN FEATURES
-------------
- Mapping preview before applying constraints.
- Copy Transforms, Copy Rotation, Copy Location, Copy Scale.
- Mix, spaces, influence, offset and stack position.
- Bone-collection and deform-only filters.
- Pre-flight rig diagnostics.
- Auto-prefix and pattern learning from an existing constraint.
- Maintenance: convert to manual, clean registry, mute, CSV/JSON export.
- "Info / README" button in the sidebar with author, Discord and license.


INSTALL AS AN EXTENSION (Blender 4.2+ / 5.x)
--------------------------------------------
1. Open Blender.
2. Edit > Preferences > Get Extensions.
3. Top-right arrow > "Install from Disk...".
4. Select auto_copy_transforms_def-1.1.4.zip.
5. Enable "Auto Copy Transforms DEF".
6. In the 3D View press N and open the "Auto Copy Transforms" tab.


INSTALL AS A LEGACY ADD-ON (Blender 4.2+ / 5.x)
-----------------------------------------------
The standalone legacy .py is included only in the companion RAR, not in the
extension ZIP.
1. Edit > Preferences > Add-ons.
2. Top-right arrow > "Install from Disk...".
3. Extract legacy/auto_copy_transforms_def.py from the RAR and select it.
4. Enable "Rigging: Auto Copy Transforms DEF".


COMPATIBILITY
-------------
Tested on Blender 5.2 LTS only. Both installation paths (legacy add-on and
extension manifest) declare Blender 4.2+. Blender 4.2 to 5.1 are declared
compatible but have not been tested with the documented suites.

The interface follows Blender's interface language: Italian or English.


AI DISCLOSURE
-------------
Developed with AI assistance (OpenCode), under the direction and review of
Pierfrancesco Diodato. The author remains responsible for the code and tests.


LICENSE
-------
GPL-3.0-or-later. Full text in LICENSE.txt.

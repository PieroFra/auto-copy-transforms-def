AUTO COPY TRANSFORMS DEF v1.1.0
===============================

Creator: Pierfrancesco Diodato
Discord: https://discord.com/users/1176582483165327382
License: GPL-3.0-or-later


WHAT IT DOES
------------
Creates copy constraints on destination bones (MCH-, ORG-, ...) by
automatically mapping the names of source bones (DEF-).


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
4. Select auto_copy_transforms_def-1.1.0.zip.
5. Enable "Auto Copy Transforms DEF".
6. In the 3D View press N and open the "Auto Copy Transforms" tab.


INSTALL AS A LEGACY ADD-ON (Blender 3.6 / 4.x)
-----------------------------------------------
1. Edit > Preferences > Add-ons.
2. Top-right arrow > "Install from Disk...".
3. Select legacy/auto_copy_transforms_def.py.
4. Enable "Rigging: Auto Copy Transforms DEF".


COMPATIBILITY
-------------
Tested on Blender 5.2 LTS. The code contains fallbacks for Blender 3.6/4.x,
but those versions have not been tested.


LICENSE
-------
GPL-3.0-or-later. Full text in LICENSE.txt.

# Copy-Paste Kit: Rigging Suite (Fase 3 e Fase 4)

Testi pronti all'incolla, in inglese, zero em-dash. Fase 3 = scheda Blender
Extensions di `CTRL_DEF`; Fase 4 = canali esterni (Reddit, LinkedIn, ArtStation).

---

## 1. Fase 3 - Scheda Blender Extensions di CTRL_DEF (v0.3.0)

Da incollare appena la release v0.3.0 dell'altra chat ha finito.

### Tagline

Standard bone chains from Bendy Bones, controllers from DEF_ chains: your rig, engine-ready.

### Descrizione (sostituisce la descrizione italiana attuale)

**Rig for the engine, not just for the viewport.**

BBone to Bones converts Blender Bendy Bones into standard bone chains, so your
facial, spine and tail B-Bones survive the trip to game engines. Every chain it
creates is a real armature bone you can skin, export and animate in Unity,
Unreal or Godot, and the non-destructive Revert brings everything back in one
click when you need to rework the rig.

Working on realistic rigs means your `DEF_` chains also need controllers. The
Rigging Suite workflow keeps them consistent:

- **BBone to Bones** (this add-on) turns Bendy Bones into engine-ready chains with non-destructive Revert.
- **[DEF Controller Auto](https://extensions.blender.org/add-ons/ctrl-def/)** (CTRL_DEF) generates FK controllers with shared custom shapes directly from those `DEF_` chains.
- **[Auto Copy Transforms DEF](https://extensions.blender.org/add-ons/auto-copy-transforms-def/)** (A.C.T.D.) builds the Copy Transforms constraint stack between armatures in a few clicks.

All three add-ons are standalone (zero dependencies), but when installed
together they unify automatically into a single **Rigging Suite** tab in the
Blender Sidebar, with a shared pipeline: B-Bone to chain, chain to controller,
controller to constraint.

Verified headless with 666+ automated checks, plus batch import tests in
Godot 4.7.2 and Unity 6000.6. Designed for Blender 4.2 and above.

---

## 2. Fase 4 - Post per r/godot e r/Unity3D

Corpo senza link (anti-filtro); il primo commento porta i link.

### Titolo (entrambi i sub)

I exported a Blender rig with Bendy Bones to the game engine, here is what survived (and what I fixed)

### Corpo del post

Ran into this last week: a character rig with 12 B-Bone chains for facial and
spine deformation. In Blender it looked perfect. In the engine, the bones were
gone: most engines just do not understand B-Bones, they expect regular bones
with transforms.

Round trip: 96 B-Bones in, 96 standard bones out, same deformations, still
keyframable. The trick is baking the bend into standard bones instead of
hoping the engine will interpret them.

What I did:

- converted every B-Bone into a ready-to-skin armature bone, with rotation
  baked and roll preserved
- kept the original B-Bones untouched, so the rig still works in Blender
- added a one-click Revert that removes the generated chain and puts the
  B-Bones back exactly as they were
- verified the result by batch-importing into the engine: a 96-bone chain
  imports clean every time

For anyone else doing stylized characters with soft bodies, tails, tentacles
or facial B-Bones: how do you handle the export today? Manual rebinding
before every build, or skipping B-Bones entirely?

(first comment below for links, mods)

### Primo commento

OP here: this was done with my free add-on **BBone to Bones** (Blender 4.2+),
it turns Bendy Bones into standard bone chains and the Revert is
non-destructive: https://github.com/PieroFra/bbone-to-bones

It is part of a small suite I keep together: **DEF Controller Auto** for
generating FK controllers with shared custom shapes directly from DEF_ chains
(https://extensions.blender.org/add-ons/ctrl-def/) and **A.C.T.D.** for the
Copy Transforms constraint stack between armatures
(https://extensions.blender.org/add-ons/auto-copy-transforms-def/). All three
unify into a single Rigging Suite tab when installed together.

---

## 3. Fase 4 - Post LinkedIn

### Titolo

Blender to game engine: making Bendy Bones survive the export

### Testo

If you rig stylized characters in Blender, chances are you use Bendy Bones
(B-Bones) for tails, spines, tentacles and facial deformations. And if you
export to Unity, Unreal or Godot, you already know what happens: the engine
ignores them.

Game engines understand one thing: standard bones with transforms. B-Bones
are a Blender-only deformation trick, so every soft curve you drawn in the
viewport is lost the moment the FBX/GLTF touches the engine.

The non-destructive fix is modular, three small add-ons that also work
together as a single Rigging Suite tab:

1. BBone to Bones: converts every B-Bone into a real, skinnable, exportable
   bone chain, with one-click non-destructive Revert if you need to rework
   the rig.
2. DEF Controller Auto (CTRL_DEF): generates FK controllers with shared
   custom shapes directly from the DEF_ chains, so animators get a clean
   control rig instead of grabbing deformation bones.
3. A.C.T.D. (Auto Copy Transforms DEF): builds the Copy Transforms stack
   between armatures with deterministic name mapping, preview before apply
   and full cleanup, tracked per armature.

Each add-on is standalone and dependency-free. Installed together, they share
one tab and one pipeline: B-Bone to chain, chain to controller, controller to
constraint.

Reliability is not a promise, it is measured: 666+ automated headless checks
across 12 test suites, plus batch import verification in real engines, Godot
4.7.2 and Unity 6000.6.

What else breaks between Blender and the engine on your pipeline? Happy to
look at the next pain point.

#blender #gamedev #rigging #technicalart #unity #unreal #godot

---

## 4. Fase 4 - Breakdown per progetto ArtStation

### Titolo progetto

Blender to Game Engine Rigging Suite

### Descrizione

A three-piece toolkit that takes a Blender character rig from viewport to game
engine without losing deformation quality. BBone to Bones converts Bendy Bones
into standard, engine-ready bone chains (96-bone round trip verified) with a
non-destructive Revert that restores the original rig in one click. DEF
Controller Auto generates FK controllers with shared custom shapes directly
from the DEF_ chains. A.C.T.D. builds the Copy Transforms constraint stack
between armatures, with deterministic mapping, preview and per-armature
tracking in a JSON registry.

All add-ons are standalone and unify into a single Rigging Suite tab in the
Blender Sidebar. Reliability verified with 666+ automated headless checks
across 12 suites and batch engine import tests in Godot 4.7.2 and Unity 6000.6.

### Media da caricare

1. Hero shot: character rig in Blender with B-Bone chains colored, sidebar
   Rigging Suite tab visible.
2. Before/after graph: B-Bone render vs generated standard bone chain.
3. Screen capture: one-click Revert, B-Bones come back untouched.
4. Side-by-side: Blender viewport vs Godot 4.7.2 import vs Unity 6000.6
   import, same pose.
5. Close-up: FK controllers with shared custom shapes generated on DEF_ chains.
6. Close-up: Copy Transforms preview before apply, constraint registry panel.
7. Repeatable pipeline shot: suite tab with the three add-ons unified, arrows
   showing B-Bone to chain, chain to controller, controller to constraint.

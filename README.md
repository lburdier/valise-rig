# Valise Rig

Extension Blender (4.4 → 5.x) qui pilote le rig de la **valise casque** (`RIG_Valise`) et génère des animations prêtes à l'emploi, avec l'inertie des câbles calculée automatiquement.

Panneau : **Vue 3D → barre latérale (N) → onglet « Valise »**.

## Installation

1. Télécharger `valise_rig-X.Y.Z.zip` depuis la page [Releases](https://github.com/lburdier/valise-rig/releases).
2. Blender → *Édition → Préférences → Extensions* → menu ⌄ → **Installer depuis le disque…** → choisir le zip.
3. Ouvrir `valise_casque_v2.blend` : l'onglet **Valise** apparaît dans la barre latérale.

Les mises à jour sont ensuite automatiques : au démarrage (une fois par jour max), l'add-on regarde la dernière release GitHub et l'installe (désactivable dans les préférences de l'extension).

## Fonctions

### Contrôle direct
Curseurs reliés aux contrôleurs du rig : couvercle (0–130°), 4 fermoirs, écran du laptop, poignée avant, poignées gauche / droite, hauteur de la valise.
- **Insérer une clé** : enregistre l'état des curseurs à l'image courante.
- Lire la pose / Pose de repos.

### Presets d'animation
Chaque preset crée une nouvelle action `Valise_…` (ou une piste NLA), avec réglage de l'image de départ, de la vitesse et de l'amplitude de l'inertie des câbles.

| Preset | Contenu |
|---|---|
| Ouverture complète | Fermoirs un par un → couvercle avec léger rebond → écran du laptop |
| Fermeture | Écran rabattu → couvercle qui retombe avec rebond → fermoirs verrouillés |
| Cycle complet | Ouverture puis fermeture |
| Ouverture rapide | Fermoirs claqués, couvercle projeté qui dépasse puis se stabilise |
| Coup d'œil | Couvercle entrouvert (~25°), refermé, reverrouillé |
| Déverrouiller / Verrouiller | Les 4 fermoirs en cascade |
| Laptop : ouvrir / fermer | Valise ouverte, l'écran s'ouvre puis se referme |
| Soulever (transport) | Poignée levée, valise soulevée qui se balance, reposée |
| Poignées latérales | Les deux poignées se lèvent puis retombent |
| Repos | Une clé « tout fermé » |

### Inertie des câbles
Ressort amorti piloté par l'accélération du couvercle et de la valise : les câbles du couvercle « gonflent » et oscillent (leurs extrémités restent sur les connecteurs grâce à un IK), les câbles intérieurs rebondissent quand le couvercle les libère.
**Recalculer l'inertie** la régénère sur l'animation active après des retouches manuelles.

### Export
- **Cuire pour l'export** : copie `…_EXPORT` de l'animation avec les contraintes cuites (Visual Keying), pour FBX / moteur de jeu.
- **Exporter pour Substance Painter** : FBX propre, un objet par matériau `M_*` (= un Texture Set), pose fermée, triangulé, une seule couche UV dans 0–1, normales d'origine conservées, sans armature.

## Publier une nouvelle version

1. Modifier le code, augmenter `version` dans `blender_manifest.toml` (ex. `1.0.0` → `1.1.0`).
2. `git commit` puis `git push` sur `main`.
3. Le workflow **Release** (GitHub Actions) construit `valise_rig-1.1.0.zip` et publie la release `v1.1.0` automatiquement. Les utilisateurs la reçoivent via l'updater intégré.

Construire le zip en local : `python tools/build.py`.

## Licence

GPL-3.0-or-later

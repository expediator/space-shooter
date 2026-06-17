# 🚀 Space Shooter

A self-contained 2D arcade space shooter that runs instantly in any browser — pure JavaScript Canvas, no plugins or installs.

**Play:** [expediator.github.io/space-shooter](https://expediator.github.io/space-shooter/) &nbsp;·&nbsp; **Portfolio:** [expediator.github.io/resume](https://expediator.github.io/resume/)

---

## Controls

| Key | Action |
|---|---|
| `W` / `↑` | Thrust forward |
| `A` / `←` | Rotate left |
| `D` / `→` | Rotate right |
| `S` / `↓` | Brake (friction) |
| `Space` / Click | Shoot |
| `P` | Pause / unpause |
| `R` | Restart (after game over) |

Touch/tap also fires bullets on mobile.

## Gameplay

- Enemies spawn from screen edges and increase in count each level
- Kill enough enemies to advance to the next level (faster spawns, more enemies)
- Two enemy types:
  - **Red circles** — seek the player directly
  - **Orange stars** — wander and occasionally dash + shoot projectiles
- Pick up power-ups dropped by enemies:
  - **R (green)** — Rapid Fire for 7 seconds
  - **S (blue)** — Shield for 6 seconds (absorbs hits)
- Lives: 3. Lose all HP → lose a life → respawn with 3s invulnerability
- Score: 100 pts (basic enemy), 250 pts (big enemy), 60 pts (collision kill)

## Tech

- **JavaScript** — game loop with `requestAnimationFrame`, delta-time physics
- **Canvas API** — all rendering (no sprites, procedural shapes only)
- **HTML/CSS** — single self-contained file
- **GitHub Pages** — deployed from `/docs/index.html`

Originally built in **Python/pygame**, then rewritten in JavaScript so it runs in-browser without WebAssembly overhead.

## Files

```
space-shooter/
├── docs/
│   └── index.html       ← Full game (deployed to GitHub Pages)
├── space_adventure.py   ← Original Python/pygame source
└── README.md
```

## Run the Python Version

```bash
pip install pygame
python space_adventure.py
```

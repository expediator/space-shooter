# Space Shooter

A self-contained 2D arcade space shooter built with **pygame**.

## Features

- Player ship with rotation, thrust, and inertia
- Two enemy types: basic (seek player) and big (wander + dash + shoot back)
- Power-ups: **rapid-fire** and **shield** (random drops on enemy kill)
- Particle explosions, wrap-around screen edges
- HUD: score, level, health bar, lives, active power-up timers
- Pause (`P`), restart on game-over (`R`)
- Procedural starfield background

## Controls

| Key | Action |
|---|---|
| W / ↑ | Thrust forward |
| A / ← | Rotate left |
| D / → | Rotate right |
| S / ↓ | Brake |
| SPACE or click | Shoot |
| P | Pause |
| R | Restart (after game over) |
| ESC | Quit |

## Run

```bash
pip install pygame
python space_adventure.py
```

## Stack

`Python` · `pygame` · `OOP (Player, Enemy, Bullet, PowerUp, Particle, HUD, Game)`

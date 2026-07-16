# Overhead

App for the EMF [Tildagon Badge](https://tildagon.badge.emfcamp.org/),
which shows which objcects are passing overhead right now, and uses the badge lights to point the direction.

## Features

- ISS, Tiangong and Hubble, propagated with SGP4 (works fully offline)
- The moon and the naked-eye planets, from on-board ephemeris
- Aircraft overhead, live from ADS-B
- Counts down to the next pass and points at where it will rise
- Flashes `LOOK UP` and strobes the ring when the ISS is actually visible

<p align="center">
<img src="https://pixelflare.cc/i/wq5guw?segment=foreground" width="600" />
</p>

## Usage

- `LEFT` / `RIGHT`  switch between objects
- `CONFIRM`  show the debug log
- `CANCEL`  exit

It needs wifi once to set the clock (it says `NO CLOCK` until then). After that,
positions need no network.

## Developing

`app.py` and `hud.py` are the app, `emflib/` is the core.
The tests need only Python 3, nothing else, just run `make test`

The simulator needs SDL and a few Python packages (the app itself has no deps).

Ubuntu:

```bash
sudo apt install -y git python3 python3-venv libsdl2-2.0-0   # tools + SDL for the sim window
```

NixOS:

```bash
nix-shell -p git python3 gnumake SDL2                        # a shell with the tools
# the pip wheels below need nix-ld enabled, or an FHS shell, to load
```

Then on either:

```bash
python3 -m venv .venv && . .venv/bin/activate                 # isolated python env
pip install pygame==2.6.1 wasmtime==39.0.0 requests==2.32.3   # what the simulator runs on
git clone https://github.com/emfcamp/badge-2024-software ../badge-2024-software  # the simulator
bash tools/sim.sh                                             # launch Overhead, F quits
```

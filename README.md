# Overhead

Point your badge at the sky. Overhead tracks the ISS and other things passing
over you and lights the LED ring toward whatever is up there, all worked out on
the badge itself.

## Features

- ISS, Tiangong and Hubble, propagated with SGP4 (works fully offline)
- The moon and the naked-eye planets, from on-board ephemeris
- Aircraft overhead, live from ADS-B
- Counts down to the next pass and points at where it will rise
- Flashes `LOOK UP` and strobes the ring when the ISS is actually visible

<p align="center">
<img src="pixelflare.cc/i/wq5guw?segment=foreground" width="600" />
</p>

## Usage

- `LEFT` / `RIGHT`  switch between objects
- `CONFIRM`  show the debug log
- `CANCEL`  exit

It needs wifi once to set the clock (it says `NO CLOCK` until then). After that,
positions need no network.

## Developing

`app.py` and `hud.py` are the app, `emflib/` is the core (pure Python, runs under
both CPython and MicroPython).

    make test          # unit tests for the core, no badge or sim needed

Run it in the badge simulator (checked out next to this repo):

    git clone https://github.com/emfcamp/badge-2024-software ../badge-2024-software
    bash tools/sim.sh  # keys A-F are the hex buttons, F to quit

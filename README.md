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

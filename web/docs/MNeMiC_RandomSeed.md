# 🎲 Random Seed

Produces a fresh random seed on every run, from 0 to 2^64-1. Wire it into any
node that takes a seed when you want that node to vary every queue without
touching its widget.

## Inputs

None.

## Outputs

- **seed** — A new random number each execution.

## How it works

The node reports a changing fingerprint to ComfyUI, so it never reuses a cached
result. That also means everything downstream of it re-runs on every queue.
If you want a *repeatable* run, use a fixed seed widget instead.

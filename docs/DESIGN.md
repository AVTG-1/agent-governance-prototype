# Visual design

The prototype must look like the proposal deck it sits beside. `reference/proposal-deck.html` is the deck itself: open it in a browser for the look and feel. Reuse `design/tokens.css` and the fonts in `design/fonts/` unchanged.

## Colour means something, and only this

| Token | Meaning | Use |
|---|---|---|
| `--brand` / `--brand-line` (cobalt) | Deterministic control and active UI | Gateway, policy, selected states, primary buttons |
| `--allow` (green) | Went ahead | Allowed decisions, reached systems, passing checks |
| `--deny` (red) | Stopped, or harm in today mode | Denials, the leak in today mode, quarantine |
| `--hold` (amber) | Waiting for a person | Maker-checker holds, owner approval |
| `--ai` (violet) | AI, advisory only | Agent plan, investigator output |

- Status is **never colour alone**: always an icon plus a word.
- Dark mode is set with `<html data-theme="dark">`. Both themes share token names, so use tokens, never fixed hex values.
- **Default theme for the demo: dark** (projectors and screen-share favour it). Light is one key (D) away.

## Type and layout

- Fonts: Instrument Sans (400/700) for everything, and IBM Plex Mono only for policy snippets and JSON.
- Caption bar: about 22–24 px, one sentence, high contrast. It's the most important text on screen.
- Timeline rows: 15–16 px; tabular numbers for ms and times.
- One screen at 1440×900 with no page scroll. Panels scroll internally if needed.
- Motion only where it shows a change: edges flashing on decisions, counters ticking during shadow replay, the envelope countdown, the approval countdown. Respect `prefers-reduced-motion`.

## Components to reuse in spirit from the deck

- **Tags:** pill, icon plus word, tinted background.
- **Segmented controls** for speed.
- **Deep navy panels** (`--deep`) for the policy snippet and the evidence pack.
- **The capability intersection table** from the deck's "Agent to agent" chapter, for Act 4.
- **The verifier list:** one row per proposed change, a ✓/✗ tag and the reason.

## Key-view mode (SPEC §5.8)

- A recording badge sits in the header in the neutral info style (never green, red or amber), for example "Key view 5 of 8 · recorded from this run at 11:42 · no live calls".
- Filmstrip: eight equal cards, each with its number, title and a small act colour bar. Show it as an overlay above the console, not a new page.
- No motion in key-view mode: transitions off, countdowns frozen, nothing pulses.
- The exported file adds a full-width banner, "Recorded from a live run on … · playback only", in the same neutral style.

## Checklist before calling M6 done

- [x] Every decision row shows agent, action, resource, tag (icon plus word), `rule@version` and ms.
- [x] Today-mode edges are dashed and visibly bypass the plane.
- [x] The poisoned note's injected sentence is highlighted.
- [x] Nothing is cut off at 1440×900 in either theme.
- [x] The token is never visible except as `••••` plus the last 4 characters.

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

- Fonts: Instrument Sans (400/700) for everything, and IBM Plex Mono only for technical ids, policy snippets and JSON.
- **One focal point.** Two areas and a slim ticker: the agent-action map on the left (about 60%), the act panel on the right (about 40%), then the caption and a one-row decision ticker. The header holds only the title, the act stepper, the clock and the controls; the rulebook version and the deck chapter live in the act panel's header.
- **The map is the deck's "The estate today", live:** agents on the left, the six parts as a thin labelled band in the middle (the part in use lights up), systems on the right grouped by business area, "outside the firm" set apart with a dashed red border. Edges carry the decision colour; thickness is usage in the recorded week; grey dashed is observed in shadow; dotted is reach nobody has checked; a red ✕ at the band is a stop.
- **The act panel:** one card per beat, a big number or a short list (about six items at most) and one line of explanation. Earlier beats compact into one line as the act moves on.
- **Plain language first, the technical id underneath** in small mono, never truncated ("Export client file to shared drive" / `fileshare.export`).
- Caption bar: fixed height, about 1.4 rem, at most two lines, high contrast. It's the most important text on screen. Pause, error and signature states never appear in it: they float over the act panel.
- **Sizing:** everything is in rem and the root size follows the viewport (`min(1.16vw, 1.86vh)`), so one layout fits 1280×720 to 1920×1080 at 90–110% zoom with nothing to scroll. Drawers (all decisions, a decision record, the rulebook lines) scroll with wheel, trackpad, touch and keyboard, with a visible scrollbar.
- Motion only where it shows a change: an edge brightening with a dot along it, the lit part of the band, counters during the shadow replay, the envelope countdown, the signature countdown. Respect `prefers-reduced-motion`.

## Components to reuse in spirit from the deck

- **Tags:** pill, icon plus word, tinted background.
- **Segmented controls** for speed.
- **The signature card** from the deck's "Human in the loop": amber, a person icon, the countdown, and the words "auto-signs … in the demo only".
- **Deep navy panels** (`--deep`) for the policy snippet and the evidence pack.
- **The capability intersection** from the deck's "Agent to agent" chapter, as one line in Act 5.
- **The verifier list:** one row per proposed change, a ✓/✗ tag and the reason.

## Key-view mode (SPEC §5.8)

- A recording badge sits in the header, in place of the act stepper, in the neutral info style (never green, red or amber), for example "Key view 5 of 8 · recorded from this run at 11:42 · no live calls".
- Filmstrip: eight equal cards, each with its number, title and a small act colour bar. Show it as an overlay above the console, not a new page.
- No motion in key-view mode: transitions off, countdowns frozen, nothing pulses.
- The exported file adds a full-width banner, "Recorded from a live run on … · playback only", in the same neutral style.

## Checklist (M13)

- [x] Every decision in the drawer shows agent, plain action and id, resource, tag (icon plus word), `rule@version` and ms.
- [x] Today-mode lines are dashed and go straight through the plane band.
- [x] Nothing overflows or is clipped at 1280×720, 1366×768, 1536×864, 1440×900 and 1920×1080, at 90/100/110% zoom, in both themes.
- [x] Errors and pauses never change the layout; the caption keeps a fixed height.

## Checklist before calling M6 done

- [x] Every decision row shows agent, action, resource, tag (icon plus word), `rule@version` and ms.
- [x] Today-mode edges are dashed and visibly bypass the plane.
- [x] The poisoned note's injected sentence is highlighted.
- [x] Nothing is cut off at 1440×900 in either theme.
- [x] The token is never visible except as `••••` plus the last 4 characters.

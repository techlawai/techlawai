# Agent Town — handoff

A little 3D Harvest-Moon-style town where every Claude Code session and subagent on your machine is a
character. Working sessions walk to their agency's cottage and sit at a desk; off-duty ones rest at home,
grab coffee, sit by the campfire, soak in the hot spring. Buildings are see-through so you can watch them.
It's Halloween-dressed, dusk-lit, and 100% original art (procedural textures, no game assets).

Made by Jorge (Rebel Tech Miami) with Claude, Sept 2026. Give this folder + this file to your Claude and it
can set the whole thing up for you.

## What's in this folder

| File | What it is |
|---|---|
| `index.html` | The whole town (Three.js r128 from cdnjs, one file, no build step). |
| `serve.py` | Tiny Python server: serves the page on http://127.0.0.1:5180 and relays the office WebSocket. |
| `agent-town.bat` | One-click launcher: starts Pixel Agents (port 5177) if needed, starts serve.py, opens the browser. |

## What you need installed

1. **Claude Code** (desktop app or CLI) — the thing whose sessions become characters.
2. **Node.js** (for `npx`) and **Python 3** on your PATH.
3. **Pixel Agents** — the open-source "pixel office" that watches Claude Code sessions. The town doesn't watch
   Claude itself; it listens to Pixel Agents. Install it once with:
   ```
   npx -y pixel-agents --port 5177
   ```
   The first run creates `~/.pixel-agents/` (that's `C:\Users\<you>\.pixel-agents\`) and installs hooks into
   `~/.claude/settings.json` so every Claude session reports in. Open http://127.0.0.1:5177 once to confirm
   you see the pixel office.

## Run it

Double-click `agent-town.bat` (or run it from a terminal in this folder). It opens http://127.0.0.1:5180.
Start a Claude Code session anywhere and a character appears at a house within a few seconds. Spawn a
subagent and a named character walks to work.

Controls: drag = orbit, right-drag = pan, wheel = zoom, click a building or a roster card = fly there,
`H` = hide the roster.

## How it works (so your Claude can fix it if something breaks)

- Pixel Agents runs a WebSocket at `ws://127.0.0.1:5177/ws?token=…` (token in `~/.pixel-agents/server.json`).
  It only accepts same-origin browsers, so `serve.py` exposes `/ws` on port 5180 and relays the bytes to
  5177 with the `Origin` header stripped. The page just connects to its own origin. Don't open `index.html`
  as a file — always go through the server.
- Feed messages the page uses: `existingAgents`, `agentCreated` (`teammateName` = the subagent slug),
  `agentTeamInfo`, `agentStatus` (active/waiting), `agentToolStart/Done/Clear`, `agentClosed`.
- The office flips sessions to "waiting" between every tool call, so the town treats anyone active in the
  last 45 s as working (`isWorking`). That's why characters don't bounce home between tool calls.
- Simulation runs on `setInterval` (not requestAnimationFrame) so characters keep moving when the tab is
  hidden.
- Plain top-level sessions have NO name in the feed (only subagents do). The town gives them a townsperson
  name from a pool and remembers it in the browser (`localStorage['town-names']`).

## Make it YOURS — the four things to edit in `index.html`

Everything is near the top of the `<script>`.

### 1. Your agencies (buildings)
```js
const AGENCIES = [
  {key:'agency', name:'Rebel Tech Agency', wall:0xd9c3a0, roof:0x8a4a1f, pos:[-24,0,-16],
   match:/hunter|vale|gia|dante|lucy|rocky/i,    // agent slugs that belong here
   folders:/^C--Vault$/,                        // project folder names (Claude encodes C:\Vault as C--Vault)
   hint:/Agents[\\/]Personal|PIPELINE/i,         // words in tool activity that mean "this building"
   accent:0x3f8fdf},                              // scarf + sign color
  ...
];
```
Rename them, change colors, change the `match`/`folders`/`hint` regexes to your agent slugs and project
folders. Keep 4 buildings (positions are ±24, ±16) or add more with new `pos`. A session with no match and
a default folder goes to the FIRST agency; unmatched sessions from other folders wait in the town square.

### 2. Names + positions over heads
```js
const ROLES=[[/hunter/i,'Hunter','Lead Scout'],[/vale/i,'Vale','Closer · WhatsApp'], ...];
const NAMES=['Mateo','Sofia','Luca', ...];   // pool for unnamed sessions
```
One row per agent: regex on the subagent slug → display name → position. Unmatched slugs fall back to
the slug's first word capitalized. Your agents live in `~/.claude/agents/<slug>.md`; name them
`<name>-<role>` (e.g. `maya-researcher.md`) and the town reads it automatically.

### 3. Avatars
`PRESETS` = 14 looks (hair: spiky/bob/long/ponytail/pigtails/short; hats: cap/straw/top hat/bandana/
headband; outfits: overalls/dress/vest/shirt). A session gets `PRESETS[id % 14]`. Add/edit entries to
change the cast. Skin tones in `SKIN`. The scarf is always the agency accent color.

### 4. Hangouts + off-duty behavior
```js
const ACTIVITY=[['home',34],['coffee',20],['park',14],['spring',12],['rec',12],['library',8]]; // weights %
```
Venues are built with `cottage({...decorate})` — copy the café block to add a gym, a bar, whatever. Each
venue returns `seats` (`{pos,yaw}`); off-duty characters reserve a seat for 30–90 s then pick again.

### Optional
- Not Halloween? Delete the `pumpkin(...)`, `bat()`, `ghost(...)`, `deadTree` calls and the 🎃 in `clock()`.
- Too dark? Raise the `HemisphereLight` intensity (0.45) and change `scene.background`/`scene.fog`.
- Different ports: `PORT` in `serve.py` and the two `findstr` lines in the .bat; Pixel Agents port in the
  .bat and in `serve.py`'s fallback (5177).

## Gotchas we hit

- `THREE.CapsuleGeometry` doesn't exist in r128 — everything is spheres/cylinders/boxes/cones/torus.
- If the page says "office offline", Pixel Agents isn't running on 5177, or the token in
  `~/.pixel-agents/server.json` changed (restart both via the .bat).
- Browser caches: `serve.py` sends `Cache-Control: no-store`, so a plain reload shows edits.
- When debugging with the camera, the homes row is at z=36 — looking from `theta≈0` puts the camera inside
  their roofs; use `theta≈π` to look at characters from the street.

## Paste this into your Claude to set it up

> I have a folder called `town-handoff` with `index.html`, `serve.py`, `agent-town.bat` and a README.
> Read the README first. Then: (1) install Pixel Agents with `npx -y pixel-agents --port 5177` and confirm
> http://127.0.0.1:5177 shows the office; (2) edit `AGENCIES`, `ROLES` and `NAMES` in `index.html` to match
> my agents in `~/.claude/agents/` and my project folders; (3) run `agent-town.bat` and open
> http://127.0.0.1:5180; (4) spawn one test subagent and confirm its character walks into the right
> building. Keep all the WebSocket/relay logic exactly as it is — only change the config blocks the README
> names.

# Wayfield

A city builder without a grid, in one HTML file. Open `index.html` in a browser; there is nothing to install.

## How it plays

- **Roads at any angle.** Draw straight or curved streets, avenues and highways. Roads that cross split into junctions automatically, and roads over water become bridges at four times the price.
- **Parcels cut to fit.** Every new road cuts land along both sides into parcels of whatever shape the road allows. A tight curve makes fans and wedges, and a parcel that would hit water, another road or a building is shortened or left out.
- **Procedural buildings.** Each building is generated from its parcel's shape, zone and level: gabled and hipped houses with gardens, apartment towers on podiums, shops with awnings, stepped glass offices, and factories with sawtooth roofs, chimneys and tanks. They rebuild taller as land value lets them level up (1 to 5).
- **Zoning and demand.** Paint housing (low and high density), commercial, office and industrial zones with a brush. The R / C / I / O bars show demand: homes need jobs, shops need customers, and taxes push back.
- **Utilities over the network.** Power and water reach every building on roads connected to a plant, pump or tower. A shortage leaves some buildings dark, and they are abandoned if it lasts.
- **Services and land value.** Police, fire, clinics, schools and parks cover a radius and raise land value and happiness; industry and coal plants pollute around them.
- **Traffic.** Cars and trucks route between homes, workplaces and the regional highway, choosing paths by length and congestion. The traffic view shows where roads jam.
- **Milestones.** Population milestones pay a grant and unlock avenues, apartments, services, offices and highways.
- **Saves itself** to the browser at the start of every month.

## Controls

| Input | Action |
| --- | --- |
| Right-drag, WASD, or drag with no tool | Pan |
| Wheel, + / − | Zoom |
| Q / E, Shift-wheel, Ctrl+right-drag | Rotate |
| C | Straight or curved roads |
| Shift while drawing | Snap the road angle to 15° steps |
| Esc, right-click | Stop drawing, or put the tool away |
| R / Z / B | Roads / zoning / bulldoze |
| Space, 1 2 3 | Pause and speed |
| Two fingers | Pan, pinch and twist on touch screens |

## Source

The game is split into `parts/` and assembled by `build.sh`:

| File | Contents |
| --- | --- |
| `core.js` | Maths, geometry, spatial hash, terrain and trees |
| `net.js` | Road graph, crossings, parcel cutting, service placement, connectivity |
| `gen.js` | Procedural buildings and service building looks |
| `sim.js` | Demand, growth, levels, utilities, economy, traffic routing, saving |
| `render.js` | The tilted, rotatable 2.5D view: extruded buildings, roofs, windows, shadows, day and night |
| `ui.js` | Tools, input, panels, HUD and the main loop |

Run `sh build.sh` after editing to regenerate `index.html` (standalone) and `wayfield.html` (the same page without the document wrapper, for hosts that add their own).

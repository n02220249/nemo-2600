# Checkpoints

| Version | Meaning | Status |
|---|---|---|
| v0.5 | Static scanline-aware rainbow experiment | historical foundation |
| v0.6.2 | Absolute-fixup and stack crash fixes | engineering checkpoint |
| v0.6.3 | Static rather than scrolling behavior | tested |
| v0.6.4 | Full 128 TIA hue/luminance space | **tested in Stella** |
| v0.7 | P0 joystick directions through RIOT `SWCHA` | **tested in Stella** |
| Compiler v0.1 | `.nm` compiler prototype | development stage |

The v0.6.4 source models 16 hues × 8 luminance levels across the 192 visible scanlines. The v0.7 source exposes P0 directions; the tested host mapping used W/A/S/D respectively.

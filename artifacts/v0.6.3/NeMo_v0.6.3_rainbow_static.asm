; NeMo v0.6.3 - Atari 2600 NTSC static rainbow scanline demo
; Derived from the running v0.6.2 ROM. Phase is intentionally not incremented.
; 4 KiB ROM; NTSC frame model: 3 VSYNC + 37 VBLANK + 192 visible + 30 overscan.

RESET:
    SEI
    CLD
    LDX #$FF
    TXS
    LDA #$00
    STA $80
    STA $81
    STA $01
    STA $00

MAIN:
    JSR FRAME
    JMP MAIN

FRAME:
    LDA #$02
    STA $00
    STA $02
    STA $02
    STA $02
    LDA #$00
    STA $00
    LDA #$02
    STA $01
    LDX #37
VBLANK_LOOP:
    STA $02
    DEX
    BNE VBLANK_LOOP
    LDA #$00
    STA $01
    LDA #$00
    STA $81
    LDY #16
VISIBLE_LOOP:
    STA $02
    LDA $80
    CLC
    ADC $81
    AND #$07
    TAX
    LDA PALETTE,X
    STA $09
    DEY
    BNE VISIBLE_LOOP
    LDY #16
    INC $81
    LDA $81
    CMP #12
    BNE VISIBLE_LOOP
    LDA #$02
    STA $01
    LDX #30
OVERSCAN_LOOP:
    STA $02
    DEX
    BNE OVERSCAN_LOOP
    NOP
    NOP
    LDA #$00
    STA $01
    RTS

PALETTE:
    .byte $04, $14, $34, $54, $74, $94, $B4, $D4

; Vectors at $FFFA/$FFFC/$FFFE point to RESET.

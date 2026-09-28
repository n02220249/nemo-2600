#!/usr/bin/env python3
"""NeMo Compiler v0.1 -- experimental Atari 2600 compiler.

This first compiler intentionally supports a small, validated NeMo subset centered on
our confirmed v0.6.4 static rainbow and v0.7 P0-input proof programs.

No third-party packages are required.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ROM_SIZE = 4096
ROM_BASE = 0xF000
ROM_END = 0x10000
TABLE_ADDR = 0xF100
TABLE_LEN = 192
VECTOR_ADDRS = (0xFFFA, 0xFFFC, 0xFFFE)
RESET_ADDR = 0xF000

# TIA 7-bit color encoding: HHHH LLL0.
TIA128 = [((i >> 3) << 4) | ((i & 7) << 1) for i in range(128)]
RAINBOW_TABLE = bytes(TIA128[(scanline * 128) // 192] for scanline in range(TABLE_LEN))

OP_SIZE = {
    0xEA: 1,  # NOP padding
    0x78: 1, 0xD8: 1, 0xA2: 2, 0x9A: 1, 0xA9: 2, 0x85: 2,
    0x4C: 3, 0x20: 3, 0xAD: 3, 0xA5: 2, 0x29: 2, 0xF0: 2,
    0xD0: 2, 0xCA: 1, 0xBD: 3, 0xE8: 1, 0xE0: 2, 0x60: 1,
}


class NeMoError(Exception):
    pass


@dataclass
class SourceModel:
    version: str
    lines: list[str]
    text: str
    has_tia128: bool = False
    has_static_rainbow: bool = False
    has_p0_input: bool = False
    host_map: dict[str, str] = field(default_factory=dict)
    input_bits: dict[str, int] = field(default_factory=dict)

    @classmethod
    def parse(cls, text: str) -> "SourceModel":
        raw_lines = text.splitlines()
        nonblank = [ln.strip() for ln in raw_lines if ln.strip() and not ln.strip().startswith("//")]
        if not nonblank or not nonblank[0].startswith("NeMo v"):
            raise NeMoError("source must begin with 'NeMo v...' header")
        version = nonblank[0].split(maxsplit=1)[1]
        if "machine Atari2600" not in text:
            raise NeMoError("v0.1 requires 'machine Atari2600'")
        if "cpu 6507" not in text or "video TIA" not in text or "io RIOT" not in text:
            raise NeMoError("v0.1 requires cpu 6507, video TIA, and io RIOT")

        model = cls(version=version, lines=raw_lines, text=text)
        model.has_tia128 = bool(re.search(r"^palette\s+TIA128\b", text, re.M) or "TIA128[" in text)
        model.has_static_rainbow = (
            "function rainbow_color(scanline)" in text
            and "floor(scanline * 128 / 192)" in text
            and (
                "TIA.background = rainbow_color(scanline)" in text
                or "TIA.background = color" in text
                or "TIA.background = state.mode_color" in text
            )
        )
        model.has_p0_input = "input P0" in text and "raw.SWCHA" in text and "sample_input()" in text

        for key, bit in re.findall(r"^\s*(up|down|left|right)\s*=\s*raw\.SWCHA\.bit([0-7])\s+active_low", text, re.M):
            model.input_bits[key] = int(bit)
        for host, logical in re.findall(r"^\s*([WASD])\s*->\s*P0\.(up|down|left|right)\s*$", text, re.M):
            model.host_map[host] = logical
        return model


class Assembler6507:
    """Tiny 6507 assembler for the currently supported NeMo lowering patterns.

    It deliberately separates opcode emission from absolute/relative fixups so the
    mistake from v0.6 cannot happen again: fixups patch operand bytes only.
    """

    def __init__(self, base: int = ROM_BASE):
        self.base = base
        self.code = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, str, str]] = []  # operand_pos, label, kind

    @property
    def pc(self) -> int:
        return self.base + len(self.code)

    def label(self, name: str) -> None:
        if name in self.labels:
            raise NeMoError(f"duplicate label {name}")
        self.labels[name] = self.pc

    def emit(self, *bs: int) -> None:
        for b in bs:
            if not 0 <= b <= 0xFF:
                raise NeMoError(f"byte out of range: {b}")
            self.code.append(b)

    def imm(self, opcode: int, value: int) -> None:
        self.emit(opcode, value & 0xFF)

    def zp(self, opcode: int, address: int) -> None:
        if not 0 <= address <= 0xFF:
            raise NeMoError(f"zero-page address out of range: ${address:04X}")
        self.emit(opcode, address)

    def abs(self, opcode: int, address: int) -> None:
        self.emit(opcode, address & 0xFF, (address >> 8) & 0xFF)

    def branch(self, opcode: int, label: str) -> None:
        operand_pos = len(self.code) + 1
        self.emit(opcode, 0)
        self.fixups.append((operand_pos, label, "rel"))

    def jump(self, opcode: int, label: str) -> None:
        operand_pos = len(self.code) + 1
        self.emit(opcode, 0, 0)
        self.fixups.append((operand_pos, label, "abs"))

    def resolve(self) -> None:
        instruction_starts = decode_starts(bytes(self.code), self.base)
        for operand_pos, label, kind in self.fixups:
            if label not in self.labels:
                raise NeMoError(f"unknown label: {label}")
            target = self.labels[label]
            if kind == "abs":
                # CRITICAL: operand_pos is byte 1 of the instruction, never the opcode.
                self.code[operand_pos] = target & 0xFF
                self.code[operand_pos + 1] = (target >> 8) & 0xFF
                if target not in instruction_starts:
                    raise NeMoError(f"absolute target {label}=${target:04X} is not an opcode boundary")
            elif kind == "rel":
                pc_after = self.base + operand_pos + 1
                delta = target - pc_after
                if not -128 <= delta <= 127:
                    raise NeMoError(f"branch out of range: {label} delta={delta}")
                self.code[operand_pos] = delta & 0xFF
                if target not in instruction_starts:
                    raise NeMoError(f"branch target {label}=${target:04X} is not an opcode boundary")
            else:
                raise NeMoError(f"unknown fixup kind: {kind}")

    def bytes(self) -> bytes:
        self.resolve()
        return bytes(self.code)


def decode_starts(code: bytes, base: int = ROM_BASE) -> set[int]:
    starts: set[int] = set()
    i = 0
    while i < len(code):
        starts.add(base + i)
        opcode = code[i]
        size = OP_SIZE.get(opcode)
        if size is None:
            raise NeMoError(f"unsupported/unknown opcode ${opcode:02X} at ${base+i:04X}")
        i += size
        if i > len(code):
            raise NeMoError(f"instruction at ${base + i - size:04X} overruns emitted code")
    return starts


def make_base_rom() -> bytearray:
    return bytearray([0xEA] * ROM_SIZE)


def place_vectors(rom: bytearray) -> None:
    for addr in VECTOR_ADDRS:
        off = addr - ROM_BASE
        rom[off:off + 2] = bytes([RESET_ADDR & 0xFF, RESET_ADDR >> 8])


def place_table(rom: bytearray) -> None:
    off = TABLE_ADDR - ROM_BASE
    if not (0 <= off and off + TABLE_LEN <= ROM_SIZE):
        raise NeMoError("rainbow table falls outside 4 KiB ROM")
    rom[off:off + TABLE_LEN] = RAINBOW_TABLE


def emit_rainbow_core(a: Assembler6507, with_input: bool = False) -> None:
    """Lower our currently supported static rainbow kernel (and optional P0 input)."""
    a.label("RESET")
    a.emit(0x78)                 # SEI
    a.emit(0xD8)                 # CLD
    a.imm(0xA2, 0xFF)            # LDX #$FF
    a.emit(0x9A)                 # TXS
    a.imm(0xA9, 0x00)            # LDA #0
    if with_input:
        clear_addrs = (0x80, 0x81, 0x82, 0x83, 0x01, 0x00)
    else:
        clear_addrs = (0x80, 0x81, 0x01, 0x00)
    for addr in clear_addrs:
        a.zp(0x85, addr)
    a.jump(0x4C, "MAIN")

    a.label("MAIN")
    a.jump(0x20, "FRAME")
    a.jump(0x4C, "MAIN")

    a.label("FRAME")
    a.imm(0xA9, 0x02)
    a.zp(0x85, 0x00)             # VSYNC on
    a.zp(0x85, 0x02)
    a.zp(0x85, 0x02)
    a.zp(0x85, 0x02)
    a.imm(0xA9, 0x00)
    a.zp(0x85, 0x00)             # VSYNC off

    a.imm(0xA9, 0x02)
    a.zp(0x85, 0x01)             # VBLANK on

    if with_input:
        a.abs(0xAD, 0x0280)      # LDA SWCHA
        a.zp(0x85, 0x82)         # raw input
        a.imm(0xA9, 0x00)
        a.zp(0x85, 0x83)         # mode_color = 0
        # Canonical v0.7 priority: up, left, down, right.
        for mask, target in ((0x80, "SET_UP"), (0x20, "SET_LEFT"), (0x40, "SET_DOWN"), (0x10, "SET_RIGHT")):
            a.zp(0xA5, 0x82)
            a.imm(0x29, mask)
            a.branch(0xF0, target)
        a.jump(0x4C, "INPUT_DONE")
        for name, color in (("SET_UP", 0x1E), ("SET_LEFT", 0x4E), ("SET_DOWN", 0x8E), ("SET_RIGHT", 0xCE)):
            a.label(name)
            a.imm(0xA9, color)
            a.zp(0x85, 0x83)
            if name != "SET_RIGHT":
                a.jump(0x4C, "INPUT_DONE")
        a.label("INPUT_DONE")

    if with_input:
        a.imm(0xA9, 0x02)       # restore A=VBLANK value after input sampling
    a.imm(0xA2, 0x25)            # 37 VBLANK iterations
    a.label("VBLANK_LOOP")
    a.zp(0x85, 0x02)
    a.emit(0xCA)                 # DEX
    a.branch(0xD0, "VBLANK_LOOP")

    a.imm(0xA9, 0x00)
    a.zp(0x85, 0x01)             # VBLANK off
    a.imm(0xA2, 0x00)            # X = scanline index
    a.label("VISIBLE_LOOP")
    a.zp(0x85, 0x02)             # WSYNC
    if with_input:
        a.zp(0xA5, 0x83)
        a.branch(0xD0, "WRITE_MODE")
        a.abs(0xBD, TABLE_ADDR)  # LDA TABLE,X
        a.jump(0x4C, "WRITE_COLOR")
        a.label("WRITE_MODE")
        a.zp(0xA5, 0x83)
        a.label("WRITE_COLOR")
    else:
        a.abs(0xBD, TABLE_ADDR)  # LDA TABLE,X
    a.zp(0x85, 0x09)             # COLUBK
    a.emit(0xE8)                 # INX
    a.imm(0xE0, 0xC0)            # CPX #192
    a.branch(0xD0, "VISIBLE_LOOP")

    a.imm(0xA9, 0x02)
    a.zp(0x85, 0x01)             # VBLANK on
    a.imm(0xA2, 0x1E)            # 30 overscan iterations
    a.label("OVERSCAN_LOOP")
    a.zp(0x85, 0x02)
    a.emit(0xCA)
    a.branch(0xD0, "OVERSCAN_LOOP")
    a.imm(0xA9, 0x00)
    a.zp(0x85, 0x01)
    a.emit(0x60)                 # RTS


def compile_model(model: SourceModel) -> tuple[bytes, str, dict]:
    if not model.has_tia128 or not model.has_static_rainbow:
        raise NeMoError(
            "v0.1 currently supports the validated TIA128 static-rainbow kernel. "
            "The source must define TIA128 and rainbow_color(scanline) using floor(scanline * 128 / 192)."
        )

    with_input = model.has_p0_input
    if with_input:
        required = {"up": 7, "down": 6, "left": 5, "right": 4}
        if model.input_bits != required:
            raise NeMoError(f"v0.1 P0 input requires SWCHA bits {required}; got {model.input_bits}")

    a = Assembler6507()
    emit_rainbow_core(a, with_input=with_input)
    code = a.bytes()
    if TABLE_ADDR - ROM_BASE < len(code):
        raise NeMoError("generated code overlaps rainbow table")

    rom = make_base_rom()
    rom[:len(code)] = code
    place_table(rom)
    place_vectors(rom)

    validate_rom(bytes(rom), with_input=with_input)

    asm = render_asm(model, a, with_input)
    report = {
        "compiler": "NeMo Compiler v0.1",
        "source_version": model.version,
        "rom_size": len(rom),
        "code_bytes": len(code),
        "table_address": f"${TABLE_ADDR:04X}",
        "table_bytes": TABLE_LEN,
        "vectors": {f"${v:04X}": f"${RESET_ADDR:04X}" for v in VECTOR_ADDRS},
        "p0_input": with_input,
        "sha256": hashlib.sha256(rom).hexdigest(),
    }
    return bytes(rom), asm, report


def render_asm(model: SourceModel, a: Assembler6507, with_input: bool) -> str:
    lines = [
        f"; Generated by NeMo Compiler v0.1 from NeMo {model.version}",
        "; This is diagnostic assembly representation; .bin is the executable artifact.",
        "; Fixups are resolved by the compiler, with operand-only absolute patching.",
        "",
        f"TABLE = ${TABLE_ADDR:04X}",
        "SWCHA = $0280",
        "COLUBK = $0009",
        "WSYNC = $0002",
        "VSYNC = $0000",
        "VBLANK = $0001",
        "",
    ]
    # The compiler's internal labels are enough for a useful report. The full source is
    # regenerated as normalized pseudo-assembly elsewhere only as the backend evolves.
    for name, addr in sorted(a.labels.items(), key=lambda kv: kv[1]):
        lines.append(f"{name} = ${addr:04X}")
    if with_input:
        lines += [
            "",
            "; P0: up=bit7, down=bit6, left=bit5, right=bit4 active-low",
            "; Host keyboard mapping is external to the ROM (e.g. Stella).",
        ]
    lines += ["", "; Emitted bytes (first 64 bytes):"]
    hex_bytes = a.bytes()[:64]
    for i in range(0, len(hex_bytes), 16):
        lines.append(f"; ${ROM_BASE+i:04X}: " + " ".join(f"{b:02X}" for b in hex_bytes[i:i+16]))
    lines.append(f"; table: ${TABLE_ADDR:04X}-${TABLE_ADDR+TABLE_LEN-1:04X}")
    return "\n".join(lines) + "\n"


def validate_rom(rom: bytes, *, with_input: bool) -> None:
    if len(rom) != ROM_SIZE:
        raise NeMoError(f"ROM must be exactly 4096 bytes, got {len(rom)}")
    # Vectors
    for addr in VECTOR_ADDRS:
        off = addr - ROM_BASE
        if rom[off:off+2] != bytes([RESET_ADDR & 0xFF, RESET_ADDR >> 8]):
            raise NeMoError(f"vector ${addr:04X} does not point to RESET $F000")
    # Decode emitted code up to the table and ensure every instruction is known.
    code = rom[:TABLE_ADDR - ROM_BASE]
    starts = decode_starts(code)

    # Verify every absolute/relative control transfer lands on an instruction boundary.
    i = 0
    while i < len(code):
        addr = ROM_BASE + i
        op = code[i]
        if op == 0x4C or op == 0x20:
            target = code[i+1] | (code[i+2] << 8)
            if target not in starts:
                raise NeMoError(f"control transfer at ${addr:04X} lands on ${target:04X}, not an opcode")
        elif op in (0xF0, 0xD0):
            delta = code[i+1] if code[i+1] < 0x80 else code[i+1] - 0x100
            target = addr + 2 + delta
            if target not in starts:
                raise NeMoError(f"branch at ${addr:04X} lands on ${target:04X}, not an opcode")
        i += OP_SIZE[op]

    table = rom[TABLE_ADDR-ROM_BASE:TABLE_ADDR-ROM_BASE+TABLE_LEN]
    expected = RAINBOW_TABLE
    if table != expected:
        raise NeMoError("rainbow table differs from the validated NeMo v0.6.4 table")
    if set(table) != set(TIA128):
        raise NeMoError("rainbow table does not contain all 128 TIA color codes")
    if with_input:
        for mask in (0x80, 0x20, 0x40, 0x10):
            if bytes((0xA5, 0x82, 0x29, mask)) not in code:
                raise NeMoError(f"missing P0 input mask ${mask:02X}")


def default_output(src: Path) -> Path:
    return src.with_suffix(".bin")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="nemo", description="NeMo Compiler v0.1")
    p.add_argument("source", help="NeMo source file (.nm or .nemo)")
    p.add_argument("-o", "--output", type=Path, help="output ROM path; default is source with .bin")
    p.add_argument("--asm", type=Path, help="also write diagnostic backend assembly report")
    p.add_argument("--report", action="store_true", help="print compiler/ROM validation report")
    p.add_argument("--check", action="store_true", help="validate only; do not write a ROM")
    args = p.parse_args(argv)

    src = Path(args.source)
    if not src.exists():
        print(f"NeMo: error: source not found: {src}", file=sys.stderr)
        return 2
    try:
        model = SourceModel.parse(src.read_text(encoding="utf-8"))
        rom, asm, report = compile_model(model)
        if args.check:
            print(f"NeMo: OK — {src.name}")
        else:
            out = args.output or default_output(src)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(rom)
            print(f"NeMo: compiled {src.name} -> {out}")
        if args.asm:
            args.asm.parent.mkdir(parents=True, exist_ok=True)
            args.asm.write_text(asm, encoding="utf-8")
        if args.report:
            for k, v in report.items():
                print(f"{k}: {v}")
        return 0
    except (OSError, UnicodeError, NeMoError) as exc:
        print(f"NeMo: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

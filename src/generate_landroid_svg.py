#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import urllib.request
from dataclasses import dataclass
from typing import List, Tuple

EIGENGRAU = "#16161D"
EIGENGRAU2 = "#292936"
EIGENGRAU3 = "#3C3C4F"
EIGENGRAU4 = "#A7A7CA"
CONSOLE = "#B7B7FF"
TRACK_GREEN = "#34A853"
AUTOPILOT_BLUE = "#4285F4"
FLAG_CHARTREUSE = "#C6FF00"
THRUST_ORANGE = "#FF8800"

FALLBACK_CYCLE = ["#34A853", "#4285F4", "#C6FF00", "#E8F5E9"]

STAR_CLASS_COLORS = {
    "O": "#6666FF", "B": "#CCCCFF", "A": "#EEEEFF", "F": "#FFFFFF",
    "G": "#FFFF66", "K": "#FFCC33", "M": "#FF8800",
}

LANGUAGE_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5",
    "Kotlin": "#A97BFF", "Java": "#b07219", "Go": "#00ADD8", "Rust": "#dea584",
    "C++": "#f34b7d", "C": "#555555", "C#": "#178600", "Swift": "#F05138",
    "Ruby": "#701516", "PHP": "#4F5D95", "Shell": "#89e051", "HTML": "#e34c26",
    "CSS": "#563d7c", "Dart": "#00B4AB", "Vue": "#41b883", "Zig": "#ec915c",
    "Scala": "#c22d40", "Elixir": "#6e4a7e", "Haskell": "#5e5086",
}

SPACESHIP_PATH = (
    "M11.853 0 C11.853 -4.418 8.374 -8 4.083 -8 L-5.5 -8 "
    "C-6.328 -8 -7 -7.328 -7 -6.5 C-7 -5.672 -6.328 -5 -5.5 -5 "
    "L-2.917 -5 C-1.26 -5 0.083 -3.657 0.083 -2 L0.083 2 "
    "C0.083 3.657 -1.26 5 -2.917 5 L-5.5 5 C-6.328 5 -7 5.672 -7 6.5 "
    "C-7 7.328 -6.328 8 -5.5 8 L4.083 8 C8.374 8 11.853 4.418 11.853 0 Z"
)

SPACESHIP_LEGS = (
    "M-7 -6.5 l-3.5 0 l-1 -2 l0 4 l1 -2 Z "
    "M-7 6.5 l-3.5 0 l-1 -2 l0 4 l1 -2 Z"
)

def flag_path() -> str:

    h = 80.0
    return f"M0 0 L{h} 0 L{h*0.875} {h*0.25} L{h*0.75} 0 Z"

SHIP_SCALE = 1.9
FLAG_SCALE = 0.34

def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))

def stable_hash_unit(s: str, salt: str) -> float:
    h = hashlib.sha256((s + "|" + salt).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF

Pt = Tuple[float, float]

def catmull_rom_closed_to_bezier(pts: List[Pt], tension: float = 6.0) -> List[Tuple[Pt, Pt, Pt, Pt]]:
    n = len(pts)
    segs = []
    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i % n]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / tension, p1[1] + (p2[1] - p0[1]) / tension)
        c2 = (p2[0] - (p3[0] - p1[0]) / tension, p2[1] - (p3[1] - p1[1]) / tension)
        segs.append((p1, c1, c2, p2))
    return segs

def bezier_point(p0: Pt, p1: Pt, p2: Pt, p3: Pt, t: float) -> Pt:
    mt = 1 - t
    x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
    y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
    return (x, y)

def path_d_from_segments(segs: List[Tuple[Pt, Pt, Pt, Pt]]) -> str:
    p0 = segs[0][0]
    d = [f"M{p0[0]:.2f} {p0[1]:.2f}"]
    for (_, c1, c2, p2) in segs:
        d.append(f"C{c1[0]:.2f} {c1[1]:.2f} {c2[0]:.2f} {c2[1]:.2f} {p2[0]:.2f} {p2[1]:.2f}")
    d.append("Z")
    return " ".join(d)

def arclength_fractions(segs: List[Tuple[Pt, Pt, Pt, Pt]], samples: int = 40) -> List[float]:
    seg_lens = []
    total = 0.0
    for seg in segs:
        length = 0.0
        prev = bezier_point(*seg, 0.0)
        for k in range(1, samples + 1):
            t = k / samples
            cur = bezier_point(*seg, t)
            length += math.dist(prev, cur)
            prev = cur
        seg_lens.append(length)
        total += length
    fracs = [0.0]
    acc = 0.0
    for length in seg_lens[:-1]:
        acc += length
        fracs.append(acc / total)
    return fracs

def wavy_ring_path(cx: float, cy: float, r_lo: float, r_hi: float, points: int,
                    phase: float = 0.0) -> str:

    n = max(6, points)
    verts: List[Pt] = []
    step = 2 * math.pi / n
    for i in range(n):
        a_inner = phase + step * i
        a_outer = phase + step * (i + 0.5)
        verts.append((cx + r_lo * math.cos(a_inner), cy + r_lo * math.sin(a_inner)))
        verts.append((cx + r_hi * math.cos(a_outer), cy + r_hi * math.sin(a_outer)))
    segs = catmull_rom_closed_to_bezier(verts, tension=3.2)
    return path_d_from_segments(segs)

@dataclass
class Repo:
    name: str
    stars: int = 0
    language: str = ""
    url: str = ""

@dataclass
class Planet:
    repo: Repo
    x: float
    y: float
    r: float
    color: str
    orbit_r: float

@dataclass
class Star:
    x: float
    y: float
    r: float
    color: str

def layout_system(repos: List[Repo], width: float, height: float,
                   star_class: str) -> Tuple[Star, List[Planet]]:
    n = len(repos)
    cx, cy = width * 0.5, height * 0.5
    star_r = 24.0
    star = Star(cx, cy, star_r, STAR_CLASS_COLORS.get(star_class, STAR_CLASS_COLORS["G"]))

    ordered = sorted(repos, key=lambda r: r.stars)
    max_stars = max((r.stars for r in repos), default=1) or 1

    ex = width * 0.5 - 130
    ey = height * 0.5 - 70
    aspect = ey / ex if ex > 0 else 1.0
    inner = star_r + 70
    outer = min(ex, ey / aspect if aspect > 0 else ey)

    planets = []
    for i, repo in enumerate(ordered):
        t = i / max(1, n - 1) if n > 1 else 0.0
        orbit_r = inner + (outer - inner) * (0.25 + 0.75 * t)
        rx = orbit_r
        ry = orbit_r * aspect
        angle = -math.pi / 2 + 2 * math.pi * i / n + (stable_hash_unit(repo.name, "ang") - 0.5) * 0.25
        x = cx + rx * math.cos(angle)
        y = cy + ry * math.sin(angle)
        r = 16 + 22 * (math.log1p(repo.stars) / math.log1p(max_stars))
        color = LANGUAGE_COLORS.get(repo.language) or FALLBACK_CYCLE[i % len(FALLBACK_CYCLE)]
        planets.append(Planet(repo, x, y, r, color, orbit_r))
    return star, planets

@dataclass
class Timeline:
    dur: float
    key_points: List[float]
    key_times: List[float]

    def arrival_window(self, k: int) -> Tuple[float, float]:

        return self.key_times[2 * k], self.key_times[2 * k + 1]

def build_timeline(fracs: List[float], cruise_per_unit: float = 6.0,
                    base_cruise: float = 2.4, dwell: float = 1.5) -> Timeline:
    n = len(fracs)
    key_points = [0.0]
    key_times = [0.0]
    t = 0.0
    ext = fracs + [1.0]
    for i in range(n):
        f_next = ext[i + 1]
        f_prev = ext[i]
        span = (f_next - f_prev) % 1.0
        if span == 0.0:
            span = 1.0 / n
        t += base_cruise + cruise_per_unit * span
        key_points.append(f_next if i < n - 1 else 1.0)
        key_times.append(t)
        t += dwell
        key_points.append(f_next if i < n - 1 else 1.0)
        key_times.append(t)
    total = t
    key_times_norm = [round(x / total, 5) for x in key_times]
    for i in range(1, len(key_times_norm)):
        if key_times_norm[i] <= key_times_norm[i - 1]:
            key_times_norm[i] = key_times_norm[i - 1] + 0.0001
    return Timeline(round(total, 2), key_points, key_times_norm)

def dwell_gated_values(timeline: Timeline, n: int, visible_during_cruise: bool) -> Tuple[str, str]:

    cruise_v = "1" if visible_during_cruise else "0"
    dwell_v = "0" if visible_during_cruise else "1"
    values = [cruise_v]
    times = [0.0]
    for k in range(n):
        arr_t, dwell_end_t = timeline.arrival_window(k)
        values += [cruise_v, dwell_v]
        times += [arr_t, arr_t]
        values += [dwell_v, cruise_v]
        times += [dwell_end_t, dwell_end_t]
    values.append(cruise_v)
    times.append(1.0)
    for i in range(1, len(times)):
        if times[i] <= times[i - 1]:
            times[i] = times[i - 1] + 0.0001
    return ";".join(values), ";".join(f"{tv:.5f}" for tv in times)

def make_starfield(width: float, height: float, count: int = 150) -> str:
    out = []
    for i in range(count):
        x = stable_hash_unit(f"star{i}", "x") * width
        y = stable_hash_unit(f"star{i}", "y") * height
        r = 0.4 + stable_hash_unit(f"star{i}", "r") * 1.1
        base_op = 0.12 + stable_hash_unit(f"star{i}", "o") * 0.6
        twinkle = stable_hash_unit(f"star{i}", "t") < 0.15
        if twinkle:
            dur = 2.2 + stable_hash_unit(f"star{i}", "d") * 3.4
            delay = stable_hash_unit(f"star{i}", "dl") * dur
            out.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="#EDEDFF">'
                f'<animate attributeName="opacity" values="{base_op:.2f};{min(1,base_op+0.55):.2f};{base_op:.2f}" '
                f'dur="{dur:.2f}s" begin="-{delay:.2f}s" repeatCount="indefinite"/></circle>'
            )
        else:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="#EDEDFF" opacity="{base_op:.2f}"/>')
    return "\n".join(out)

def make_pulse_rings(cx: float, cy: float, base_r: float, color: str, span: float,
                      count: int = 3, opacity: float = 0.35, seed: str = "") -> str:

    out = []
    for k in range(count):
        dur = 3.0 + stable_hash_unit(seed + str(k), "pd") * 1.2
        delay = (dur / count) * k
        out.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{base_r:.1f}" fill="none" '
            f'stroke="{color}" stroke-width="1" opacity="0">'
            f'<animate attributeName="r" values="{base_r:.1f};{base_r+span:.1f}" '
            f'dur="{dur:.2f}s" begin="-{delay:.2f}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;{opacity};0" '
            f'dur="{dur:.2f}s" begin="-{delay:.2f}s" repeatCount="indefinite"/>'
            f'</circle>'
        )
    return "\n".join(out)

def make_star_svg(star: Star) -> str:
    corona1 = wavy_ring_path(star.x, star.y, star.r + 40, star.r + 95, 15)
    corona2 = wavy_ring_path(star.x, star.y, star.r + 15, star.r + 78, 16, phase=0.4)
    pulses = make_pulse_rings(star.x, star.y, star.r, star.color, span=70,
                               count=3, opacity=0.22, seed="starpulse")
    return f"""
  <g id="star">
    {pulses}
    <g>
      <path d="{corona1}" fill="none" stroke="{star.color}" stroke-width="2" opacity="0.5" stroke-linejoin="round"/>
      <animateTransform attributeName="transform" type="rotate" additive="sum"
                         from="0 {star.x:.1f} {star.y:.1f}" to="360 {star.x:.1f} {star.y:.1f}"
                         dur="46s" repeatCount="indefinite"/>
    </g>
    <g>
      <path d="{corona2}" fill="none" stroke="{star.color}" stroke-width="1.6" opacity="0.4" stroke-linejoin="round"/>
      <animateTransform attributeName="transform" type="rotate" additive="sum"
                         from="360 {star.x:.1f} {star.y:.1f}" to="0 {star.x:.1f} {star.y:.1f}"
                         dur="38s" repeatCount="indefinite"/>
    </g>
    <circle cx="{star.x:.1f}" cy="{star.y:.1f}" r="{star.r:.1f}" fill="{star.color}"/>
  </g>"""

def make_planet(p: Planet, idx: int, arrival_t0: float, arrival_t1: float, always_on: bool) -> str:

    repo = p.repo
    tex_a = 40 + stable_hash_unit(repo.name, "tex1") * 260
    clip_id = f"clip{idx}"
    texture_and_ring = f"""
      <path d="M {p.x - p.r*0.7:.1f} {p.y - p.r*0.15:.1f} a {p.r*0.5:.1f} {p.r*0.22:.1f} 0 1 0 {p.r*1.1:.1f} {p.r*0.05:.1f}"
            fill="none" stroke="{p.color}" stroke-width="{max(1.1,p.r*0.05):.1f}" opacity="0.55" clip-path="url(#{clip_id})"/>
      <path d="M {p.x - p.r*0.3:.1f} {p.y + p.r*0.5:.1f} a {p.r*0.35:.1f} {p.r*0.18:.1f} {tex_a:.0f} 1 1 {p.r*0.75:.1f} {p.r*0.1:.1f}"
            fill="none" stroke="{p.color}" stroke-width="{max(1,p.r*0.04):.1f}" opacity="0.4" clip-path="url(#{clip_id})"/>
      <circle cx="{p.x:.1f}" cy="{p.y:.1f}" r="{p.r:.1f}" fill="none" stroke="{p.color}" stroke-width="2"/>"""

    base = (f'\n  <g class="planet">'
            f'\n    <clipPath id="{clip_id}"><circle cx="{p.x:.1f}" cy="{p.y:.1f}" r="{p.r:.1f}"/></clipPath>'
            f'\n    <circle cx="{p.x:.1f}" cy="{p.y:.1f}" r="{p.r:.1f}" fill="{EIGENGRAU}"/>')

    if always_on:
        unexplored = ""
        explored = f'\n    <g>{texture_and_ring}\n    </g>'
    else:
        unexplored = (
            f'\n    <g>'
            f'\n      <animate attributeName="opacity" dur="{{DUR}}s" repeatCount="indefinite" '
            f'values="1;1;0;0" keyTimes="0;{arrival_t0:.5f};{arrival_t1:.5f};1"/>'
            f'\n      <circle cx="{p.x:.1f}" cy="{p.y:.1f}" r="{p.r:.1f}" fill="none" stroke="{EIGENGRAU4}" stroke-width="2"/>'
            f'\n    </g>'
        )
        explored = (
            f'\n    <g opacity="0">'
            f'\n      <animate attributeName="opacity" dur="{{DUR}}s" repeatCount="indefinite" '
            f'values="0;0;1;1" keyTimes="0;{arrival_t0:.5f};{arrival_t1:.5f};1"/>'
            f'{texture_and_ring}'
            f'\n    </g>'
        )
    return base + unexplored + explored + "\n  </g>"

def make_label(p: Planet, star: Star, width: float, height: float) -> str:
    repo = p.repo
    dx, dy = p.x - star.x, p.y - star.y
    mag = math.hypot(dx, dy) or 1.0
    ux, uy = dx / mag, dy / mag
    name = esc(repo.name)
    stars_lang = f"\u2605 {repo.stars}"
    if repo.language:
        stars_lang += f"   {esc(repo.language)}"

    if abs(ux) > abs(uy) * 0.55:
        anchor = "start" if ux > 0 else "end"
        tx = p.x + ux * (p.r + 16)
        ty1 = p.y - 4
        ty2 = p.y + 14
    else:
        anchor = "middle"
        tx = p.x
        if uy < 0:
            ty1 = p.y - p.r - 20
            ty2 = ty1 - 14
        else:
            ty1 = p.y + p.r + 20
            ty2 = ty1 + 14

    tx = max(70, min(width - 70, tx))
    ty1 = max(14, min(height - 6, ty1))
    ty2 = max(14, min(height - 6, ty2))
    return f"""
  <g font-family="ui-monospace,SFMono-Regular,'JetBrains Mono',Menlo,Consolas,monospace" text-anchor="{anchor}">
    <text x="{tx:.1f}" y="{ty1:.1f}" font-size="13" fill="{CONSOLE}" font-weight="600">{name}</text>
    <text x="{tx:.1f}" y="{ty2:.1f}" font-size="10.5" fill="{EIGENGRAU4}">{esc(stars_lang)}</text>
  </g>"""

def make_flag(p: Planet, arrival_t: float, always_on: bool) -> str:
    ang = -75 + stable_hash_unit(p.repo.name, "flagang") * 60
    fx = p.x + math.cos(math.radians(ang)) * (p.r - 1)
    fy = p.y + math.sin(math.radians(ang)) * (p.r - 1)
    if always_on:
        anim = ""
        pop = ""
        opacity_attr = 'opacity="1"'
    else:
        t0, t1 = arrival_t, min(0.999, arrival_t + 0.012)
        opacity_attr = 'opacity="0"'
        anim = (f'<animate attributeName="opacity" dur="{{DUR}}s" repeatCount="indefinite" '
                f'values="0;0;1;1" keyTimes="0;{t0:.5f};{t1:.5f};1"/>')
        pop = (f'<animateTransform attributeName="transform" type="scale" additive="sum" '
               f'dur="{{DUR}}s" repeatCount="indefinite" '
               f'values="1;1;1.3;0.92;1;1" '
               f'keyTimes="0;{t0:.5f};{min(0.999,t0+0.02):.5f};{min(0.999,t0+0.05):.5f};{min(0.999,t0+0.08):.5f};1"/>')
    return f"""
  <g transform="translate({fx:.1f} {fy:.1f}) rotate({ang:.1f})" {opacity_attr}>
    {anim}
    <g>
      {pop}
      <path d="{flag_path()}" transform="scale({FLAG_SCALE})" fill="none"
            stroke="{FLAG_CHARTREUSE}" stroke-width="{2/FLAG_SCALE:.1f}" stroke-linejoin="round"/>
    </g>
  </g>"""

def make_ping(p: Planet, arrival_t: float) -> str:
    t0 = arrival_t
    t1 = min(0.999, arrival_t + 0.05)
    return f"""
  <circle cx="{p.x:.1f}" cy="{p.y:.1f}" r="{p.r:.1f}" fill="none" stroke="{FLAG_CHARTREUSE}"
          stroke-width="1.6" opacity="0">
    <animate attributeName="r" dur="{{DUR}}s" repeatCount="indefinite"
             values="{p.r:.1f};{p.r:.1f};{p.r+22:.1f};{p.r:.1f}" keyTimes="0;{t0:.5f};{t1:.5f};1"/>
    <animate attributeName="opacity" dur="{{DUR}}s" repeatCount="indefinite"
             values="0;0;0.9;0;0" keyTimes="0;{t0:.5f};{min(0.999,t0+0.003):.5f};{t1:.5f};1"/>
  </circle>"""

def make_reticle(p: Planet, t0: float, t1: float) -> str:

    ring_r = p.r + 20
    sides = 15
    pts = []
    for i in range(sides):
        a = 2 * math.pi * i / sides
        pts.append(f"{p.x + ring_r*math.cos(a):.1f},{p.y + ring_r*math.sin(a):.1f}")
    poly = " ".join(pts)
    band_r = p.r + 9
    t_show0 = t0
    t_show1 = min(t1 - 0.001, t0 + (t1 - t0) * 0.18)
    t_hide0 = t1
    t_hide1 = min(0.999, t1 + 0.01)
    return f"""
  <g opacity="0">
    <animate attributeName="opacity" dur="{{DUR}}s" repeatCount="indefinite"
             values="0;0;0;1;1;0;0" keyTimes="0;{t_show0:.5f};{t_show1:.5f};{min(t_show1+0.002,0.998):.5f};{t_hide0:.5f};{t_hide1:.5f};1"/>
    <circle cx="{p.x:.1f}" cy="{p.y:.1f}" r="{band_r:.1f}" fill="none" stroke="{AUTOPILOT_BLUE}"
            stroke-width="5" opacity="0.18"/>
    <g>
      <polygon points="{poly}" fill="none" stroke="{AUTOPILOT_BLUE}" stroke-width="1.1" opacity="0.55"/>
      <animateTransform attributeName="transform" type="rotate" additive="sum"
                         from="0 {p.x:.1f} {p.y:.1f}" to="360 {p.x:.1f} {p.y:.1f}"
                         dur="10s" repeatCount="indefinite"/>
    </g>
  </g>"""

def build_svg(repos: List[Repo], width: int = 1200, height: int = 520,
              caption: str = "autopilot // exploring repositories",
              star_class: str = "G") -> str:
    if len(repos) < 2:
        raise ValueError("need at least 2 repos to build a flight path (got %d)" % len(repos))

    star, planets = layout_system(repos, width, height, star_class)

    pts = [(p.x, p.y) for p in planets]
    segs = catmull_rom_closed_to_bezier(pts)
    path_d = path_d_from_segments(segs)
    fracs = arclength_fractions(segs)
    timeline = build_timeline(fracs)
    n = len(planets)
    DUR = timeline.dur

    def sub_dur(s: str) -> str:
        return s.replace("{DUR}", f"{DUR}")

    starfield_svg = make_starfield(width, height)
    star_svg = make_star_svg(star)

    ex = width * 0.5 - 130
    ey = height * 0.5 - 70
    aspect = ey / ex if ex > 0 else 1.0
    orbits_svg = "\n".join(
        f'<ellipse cx="{star.x:.1f}" cy="{star.y:.1f}" rx="{p.orbit_r:.1f}" '
        f'ry="{p.orbit_r * aspect:.1f}" fill="none" '
        f'stroke="{EIGENGRAU3}" stroke-width="1" stroke-dasharray="2 6" opacity="0.5"/>'
        for p in planets
    )

    planets_svg_parts = []
    labels_svg_parts = []
    flags_svg_parts = []
    pings_svg_parts = []
    reticles_svg_parts = []
    pulses_svg_parts = []

    for i, p in enumerate(planets):
        always_on = (i == 0)
        if always_on:
            t0 = t1 = 0.0
        else:
            t0, t1 = timeline.arrival_window(i - 1)
        planets_svg_parts.append(sub_dur(make_planet(p, i, t0, t1, always_on)))
        labels_svg_parts.append(make_label(p, star, width, height))
        flags_svg_parts.append(make_flag(p, t1, always_on))
        pulses_svg_parts.append(make_pulse_rings(p.x, p.y, p.r, p.color, span=26, count=2,
                                                  opacity=0.16, seed=p.repo.name))
        if not always_on:
            pings_svg_parts.append(make_ping(p, t1))
            reticles_svg_parts.append(make_reticle(p, t0, t1))

    flags_svg = sub_dur("\n".join(flags_svg_parts))
    planets_svg = "\n".join(planets_svg_parts)
    labels_svg = "\n".join(labels_svg_parts)
    pings_svg = sub_dur("\n".join(pings_svg_parts))
    reticles_svg = sub_dur("\n".join(reticles_svg_parts))
    pulses_svg = "\n".join(pulses_svg_parts)

    thrust_values, thrust_times = dwell_gated_values(timeline, n, visible_during_cruise=True)
    legs_values, legs_times = dwell_gated_values(timeline, n, visible_during_cruise=False)

    key_points_str = ";".join(f"{v:.5f}" for v in timeline.key_points)
    key_times_str = ";".join(f"{v:.5f}" for v in timeline.key_times)

    ship_d = SPACESHIP_PATH
    legs_d = SPACESHIP_LEGS
    thrust_pts = "-5,3 -12,0 -5,-3"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="0 0 {width} {height}" width="{width}" height="{height}"
     role="img" aria-labelledby="landroidTitle landroidDesc">
  <title id="landroidTitle">LandDroid autopilot — repository flyby</title>
  <desc id="landroidDesc">Autoplaying starmap. A ship on autopilot orbits a
    star and visits each repository, shown as a planet colored by language
    and sized by star count, planting a flag on arrival. Ported from the
    AOSP LandDroid easter egg (android-17_0_0_r1, packages/EasterEgg,
    com.android.egg.landroid); no script, pure SVG/SMIL.</desc>
  <defs>
    <radialGradient id="bgGrad" cx="50%" cy="46%" r="75%">
      <stop offset="0%" stop-color="{EIGENGRAU2}"/>
      <stop offset="100%" stop-color="{EIGENGRAU}"/>
    </radialGradient>
    <path id="flightPath" d="{path_d}"/>
  </defs>

  <rect x="0" y="0" width="{width}" height="{height}" fill="url(#bgGrad)"/>
  <g id="stars">{starfield_svg}
  </g>

  <g id="orbits">{orbits_svg}</g>

  {star_svg}

  <path d="{path_d}" fill="none" stroke="{TRACK_GREEN}" stroke-width="1.1" opacity="0.3"/>

  <g id="gravity-pulses">{pulses_svg}
  </g>

  <g id="reticles">{reticles_svg}
  </g>

  <g id="planets">{planets_svg}
  </g>

  {pings_svg}

  <g id="ship" transform="scale({SHIP_SCALE})">
    <g opacity="1">
      <animate attributeName="opacity" values="{legs_values}" keyTimes="{legs_times}"
               dur="{DUR}s" repeatCount="indefinite"/>
      <path d="{legs_d}" fill="none" stroke="#CCCCCC" stroke-width="{1.1/SHIP_SCALE:.2f}"/>
    </g>
    <path d="{ship_d}" fill="{EIGENGRAU}"/>
    <path d="{ship_d}" fill="none" stroke="#FFFFFF" stroke-width="{1.4/SHIP_SCALE:.2f}"/>
    <g opacity="1">
      <animate attributeName="opacity" values="{thrust_values}" keyTimes="{thrust_times}"
               dur="{DUR}s" repeatCount="indefinite"/>
      <polygon points="{thrust_pts}" fill="{THRUST_ORANGE}">
        <animate attributeName="opacity" values="1;0.55;1" dur="0.12s" repeatCount="indefinite"/>
        <animateTransform attributeName="transform" type="scale" additive="sum"
                           values="1 1;1.35 0.85;1 1" dur="0.15s" repeatCount="indefinite"/>
      </polygon>
    </g>
    <animateMotion dur="{DUR}s" repeatCount="indefinite" rotate="auto"
                    calcMode="linear" keyPoints="{key_points_str}" keyTimes="{key_times_str}">
      <mpath href="#flightPath" xlink:href="#flightPath"/>
    </animateMotion>
  </g>

  <g id="labels">{labels_svg}
  </g>

  {flags_svg}

  <text x="18" y="{height-16}" font-family="ui-monospace,SFMono-Regular,'JetBrains Mono',Menlo,Consolas,monospace"
        font-size="11" fill="{EIGENGRAU3}" letter-spacing="1">{esc(caption)}</text>
</svg>
"""
    return svg

DEMO_REPOS = [
    Repo("orbit-cli", 412, "Rust"),
    Repo("quiet-signal", 189, "TypeScript"),
    Repo("flux-router", 731, "Go"),
    Repo("terra-notes", 96, "Python"),
    Repo("pale-blue-dot", 1240, "Kotlin"),
    Repo("night-shift", 58, "Shell"),
]

def load_repos_json(path: str) -> List[Repo]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Repo(d["name"], int(d.get("stars", 0)), d.get("language", ""), d.get("url", "")) for d in data]

def fetch_github_repos(username: str, limit: int, min_stars: int) -> List[Repo]:
    url = f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated"
    req = urllib.request.Request(url, headers={"User-Agent": "landroid-svg-generator"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode())
    repos = [
        Repo(d["name"], d.get("stargazers_count", 0), d.get("language") or "", d.get("html_url", ""))
        for d in data
        if not d.get("fork") and d.get("stargazers_count", 0) >= min_stars
    ]
    repos.sort(key=lambda r: r.stars, reverse=True)
    return repos[:limit]

def main():
    ap = argparse.ArgumentParser(description="Generate an animated LandDroid SVG for a GitHub README.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--demo", action="store_true", help="use built-in placeholder repos")
    src.add_argument("--username", help="GitHub username; fetches public, non-fork repos via the GitHub API")
    src.add_argument("--repos", help="path to a repos.json file (see README.md for the schema)")
    ap.add_argument("-o", "--out", default="landroid.svg", help="output SVG path")
    ap.add_argument("--limit", type=int, default=6, help="max planets/repos to show (--username mode)")
    ap.add_argument("--min-stars", type=int, default=0, help="skip repos with fewer stars (--username mode)")
    ap.add_argument("--width", type=int, default=1200)
    ap.add_argument("--height", type=int, default=520)
    ap.add_argument("--caption", default="autopilot // exploring repositories")
    ap.add_argument("--star-class", default="G", choices=list(STAR_CLASS_COLORS.keys()),
                     help="spectral class for the central star (O/B/A/F/G/K/M), default G (sun-like)")
    args = ap.parse_args()

    if args.demo:
        repos = DEMO_REPOS
    elif args.repos:
        repos = load_repos_json(args.repos)
    else:
        try:
            repos = fetch_github_repos(args.username, args.limit, args.min_stars)
        except Exception as e:
            print(f"error: GitHub fetch failed ({e}). Use --repos with a local JSON file instead.",
                  file=sys.stderr)
            sys.exit(1)
        if not repos:
            print("error: no matching repos found (check username / --min-stars).", file=sys.stderr)
            sys.exit(1)

    svg = build_svg(repos, width=args.width, height=args.height, caption=args.caption,
                     star_class=args.star_class)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {args.out}  ({len(repos)} planets, star class {args.star_class})")

if __name__ == "__main__":
    main()

"""SVG Path Parser and Polyline Scaler for Whiteboard Doodle Rendering.
Pure Python, zero external C-dependencies. Supports standard SVG path commands:
M, m, L, l, H, h, V, v, C, c, S, s, Q, q, T, t, Z, z, plus <circle>, <rect>, <polyline>, <polygon>, <line>.
"""

import math
import re
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple


def _tokenize_path(d: str) -> List[str]:
    """Tokenize SVG path string into commands and numeric arguments."""
    # Insert spaces around command letters
    pattern = r"([a-zA-Z])|([-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?)"
    tokens = []
    for match in re.finditer(pattern, d):
        cmd, num = match.groups()
        if cmd:
            tokens.append(cmd)
        elif num:
            tokens.append(num)
    return tokens


def _eval_cubic_bezier(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    num_points: int = 12
) -> List[Tuple[float, float]]:
    """Sample points along a cubic Bezier curve."""
    pts = []
    for i in range(num_points + 1):
        t = i / float(num_points)
        mt = 1.0 - t
        x = (mt**3) * p0[0] + 3 * (mt**2) * t * p1[0] + 3 * mt * (t**2) * p2[0] + (t**3) * p3[0]
        y = (mt**3) * p0[1] + 3 * (mt**2) * t * p1[1] + 3 * mt * (t**2) * p2[1] + (t**3) * p3[1]
        pts.append((round(x, 2), round(y, 2)))
    return pts


def _eval_quadratic_bezier(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    num_points: int = 10
) -> List[Tuple[float, float]]:
    """Sample points along a quadratic Bezier curve."""
    pts = []
    for i in range(num_points + 1):
        t = i / float(num_points)
        mt = 1.0 - t
        x = (mt**2) * p0[0] + 2 * mt * t * p1[0] + (t**2) * p2[0]
        y = (mt**2) * p0[1] + 2 * mt * t * p1[1] + (t**2) * p2[1]
        pts.append((round(x, 2), round(y, 2)))
    return pts


def parse_svg_path_data(d: str, sample_steps: int = 10) -> List[List[Tuple[float, float]]]:
    """Parse SVG path 'd' attribute string into a list of polylines."""
    tokens = _tokenize_path(d)
    if not tokens:
        return []

    strokes: List[List[Tuple[float, float]]] = []
    current_stroke: List[Tuple[float, float]] = []

    curr_x, curr_y = 0.0, 0.0
    start_x, start_y = 0.0, 0.0
    last_cp: Optional[Tuple[float, float]] = None  # for smooth bezier S/s, T/t

    i = 0
    cmd = ""
    while i < len(tokens):
        t = tokens[i]
        if t.isalpha():
            cmd = t
            i += 1
        # Now process parameters according to current cmd
        if not cmd:
            break

        is_rel = cmd.islower()
        c = cmd.upper()

        if c == "M":
            if i + 1 < len(tokens) and not tokens[i].isalpha() and not tokens[i + 1].isalpha():
                x = float(tokens[i])
                y = float(tokens[i + 1])
                i += 2
                if is_rel:
                    curr_x += x
                    curr_y += y
                else:
                    curr_x = x
                    curr_y = y
                start_x, start_y = curr_x, curr_y
                if current_stroke:
                    strokes.append(current_stroke)
                current_stroke = [(round(curr_x, 2), round(curr_y, 2))]
                last_cp = None
                # Subsequent coordinates after M are treated as L
                cmd = "l" if is_rel else "L"
            else:
                break

        elif c == "L":
            if i + 1 < len(tokens) and not tokens[i].isalpha() and not tokens[i + 1].isalpha():
                x = float(tokens[i])
                y = float(tokens[i + 1])
                i += 2
                if is_rel:
                    curr_x += x
                    curr_y += y
                else:
                    curr_x = x
                    curr_y = y
                current_stroke.append((round(curr_x, 2), round(curr_y, 2)))
                last_cp = None
            else:
                break

        elif c == "H":
            if i < len(tokens) and not tokens[i].isalpha():
                x = float(tokens[i])
                i += 1
                curr_x = (curr_x + x) if is_rel else x
                current_stroke.append((round(curr_x, 2), round(curr_y, 2)))
                last_cp = None
            else:
                break

        elif c == "V":
            if i < len(tokens) and not tokens[i].isalpha():
                y = float(tokens[i])
                i += 1
                curr_y = (curr_y + y) if is_rel else y
                current_stroke.append((round(curr_x, 2), round(curr_y, 2)))
                last_cp = None
            else:
                break

        elif c == "C":
            # Cubic bezier: x1 y1, x2 y2, x y
            if i + 5 < len(tokens) and all(not tokens[i + k].isalpha() for k in range(6)):
                x1, y1 = float(tokens[i]), float(tokens[i + 1])
                x2, y2 = float(tokens[i + 2]), float(tokens[i + 3])
                x, y = float(tokens[i + 4]), float(tokens[i + 5])
                i += 6
                if is_rel:
                    p1 = (curr_x + x1, curr_y + y1)
                    p2 = (curr_x + x2, curr_y + y2)
                    p3 = (curr_x + x, curr_y + y)
                else:
                    p1 = (x1, y1)
                    p2 = (x2, y2)
                    p3 = (x, y)
                p0 = (curr_x, curr_y)
                curve_pts = _eval_cubic_bezier(p0, p1, p2, p3, num_points=sample_steps)
                current_stroke.extend(curve_pts[1:])
                curr_x, curr_y = p3
                last_cp = p2
            else:
                break

        elif c == "S":
            # Smooth cubic bezier: x2 y2, x y
            if i + 3 < len(tokens) and all(not tokens[i + k].isalpha() for k in range(4)):
                x2, y2 = float(tokens[i]), float(tokens[i + 1])
                x, y = float(tokens[i + 2]), float(tokens[i + 3])
                i += 4
                if last_cp is not None:
                    p1 = (2 * curr_x - last_cp[0], 2 * curr_y - last_cp[1])
                else:
                    p1 = (curr_x, curr_y)
                if is_rel:
                    p2 = (curr_x + x2, curr_y + y2)
                    p3 = (curr_x + x, curr_y + y)
                else:
                    p2 = (x2, y2)
                    p3 = (x, y)
                p0 = (curr_x, curr_y)
                curve_pts = _eval_cubic_bezier(p0, p1, p2, p3, num_points=sample_steps)
                current_stroke.extend(curve_pts[1:])
                curr_x, curr_y = p3
                last_cp = p2
            else:
                break

        elif c == "Q":
            # Quadratic bezier: x1 y1, x y
            if i + 3 < len(tokens) and all(not tokens[i + k].isalpha() for k in range(4)):
                x1, y1 = float(tokens[i]), float(tokens[i + 1])
                x, y = float(tokens[i + 2]), float(tokens[i + 3])
                i += 4
                if is_rel:
                    p1 = (curr_x + x1, curr_y + y1)
                    p2 = (curr_x + x, curr_y + y)
                else:
                    p1 = (x1, y1)
                    p2 = (x, y)
                p0 = (curr_x, curr_y)
                curve_pts = _eval_quadratic_bezier(p0, p1, p2, num_points=sample_steps)
                current_stroke.extend(curve_pts[1:])
                curr_x, curr_y = p2
                last_cp = p1
            else:
                break

        elif c == "Z":
            if current_stroke:
                current_stroke.append((round(start_x, 2), round(start_y, 2)))
                strokes.append(current_stroke)
                current_stroke = []
            curr_x, curr_y = start_x, start_y
            last_cp = None
            cmd = ""
        else:
            # Skip unhandled token
            i += 1

    if current_stroke:
        strokes.append(current_stroke)

    # Filter out strokes with < 2 points
    return [s for s in strokes if len(s) >= 2]


def parse_svg_content(svg_text: str) -> List[List[Tuple[float, float]]]:
    """Parse entire SVG XML string, extracting <path>, <circle>, <rect>, <polyline>, <polygon>."""
    strokes: List[List[Tuple[float, float]]] = []

    # Strip XML namespace for clean tag matching
    clean_xml = re.sub(r'\sxmlns="[^"]+"', '', svg_text)
    try:
        root = ET.fromstring(clean_xml)
    except Exception:
        # Fallback regex for d attributes
        for m in re.finditer(r'd="([^"]+)"', svg_text):
            strokes.extend(parse_svg_path_data(m.group(1)))
        return strokes

    for elem in root.iter():
        tag = elem.tag.split("}")[-1].lower()

        if tag == "path":
            d = elem.get("d", "")
            if d:
                strokes.extend(parse_svg_path_data(d))

        elif tag == "circle":
            try:
                cx = float(elem.get("cx", 0))
                cy = float(elem.get("cy", 0))
                r = float(elem.get("r", 0))
                if r > 0:
                    c_pts = []
                    steps = 28
                    for step in range(steps + 1):
                        ang = (step / float(steps)) * 2 * math.pi
                        c_pts.append((round(cx + r * math.cos(ang), 2), round(cy + r * math.sin(ang), 2)))
                    strokes.append(c_pts)
            except Exception:
                pass

        elif tag == "rect":
            try:
                rx = float(elem.get("x", 0))
                ry = float(elem.get("y", 0))
                rw = float(elem.get("width", 0))
                rh = float(elem.get("height", 0))
                if rw > 0 and rh > 0:
                    rect_pts = [
                        (rx, ry),
                        (rx + rw, ry),
                        (rx + rw, ry + rh),
                        (rx, ry + rh),
                        (rx, ry),
                    ]
                    strokes.append(rect_pts)
            except Exception:
                pass

        elif tag in ("polyline", "polygon"):
            raw_pts = elem.get("points", "")
            nums = [float(n) for n in re.findall(r"[-+]?(?:\d*\.\d+|\d+)", raw_pts)]
            pts = [(nums[k], nums[k + 1]) for k in range(0, len(nums) - 1, 2)]
            if tag == "polygon" and pts:
                pts.append(pts[0])
            if len(pts) >= 2:
                strokes.append(pts)

        elif tag == "line":
            try:
                x1 = float(elem.get("x1", 0))
                y1 = float(elem.get("y1", 0))
                x2 = float(elem.get("x2", 0))
                y2 = float(elem.get("y2", 0))
                strokes.append([(x1, y1), (x2, y2)])
            except Exception:
                pass

    return strokes


def scale_and_center_strokes(
    strokes: List[List[Tuple[float, float]]],
    center_x: float,
    center_y: float,
    target_width: float = 380.0,
    target_height: Optional[float] = None,
) -> List[List[Tuple[float, float]]]:
    """
    Uniformly scale and center an arbitrary set of SVG stroke polylines
    into the specified canvas area (center_x, center_y), maintaining aspect ratio.
    """
    if not strokes:
        return []

    # Calculate global bounding box
    all_pts = [pt for stroke in strokes for pt in stroke]
    if not all_pts:
        return []

    min_x = min(pt[0] for pt in all_pts)
    max_x = max(pt[0] for pt in all_pts)
    min_y = min(pt[1] for pt in all_pts)
    max_y = max(pt[1] for pt in all_pts)

    src_w = max(max_x - min_x, 1e-3)
    src_h = max(max_y - min_y, 1e-3)

    if target_height is not None:
        scale = min(target_width / src_w, target_height / src_h)
    else:
        scale = target_width / src_w

    src_cx = min_x + src_w / 2.0
    src_cy = min_y + src_h / 2.0

    scaled_strokes: List[List[Tuple[float, float]]] = []
    for stroke in strokes:
        scaled_stroke = []
        for x, y in stroke:
            nx = center_x + (x - src_cx) * scale
            ny = center_y + (y - src_cy) * scale
            scaled_stroke.append((round(nx, 2), round(ny, 2)))
        scaled_strokes.append(scaled_stroke)

    return scaled_strokes

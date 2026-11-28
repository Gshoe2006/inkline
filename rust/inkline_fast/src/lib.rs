//! inkline_fast: Rust versions of the slowest inner loops in Inkline's Python engine.
//!
//! Every function gives exactly the numbers the Python code gives (same operations, same order, same
//! rounding), so a page looks the same with or without this module. Inkline works without it: the Python
//! code is used whenever `import inkline_fast` fails. See docs/performance.md.
//!
//!   contour_level      marching squares for one contour level (inkengine/patterns/contour.py)
//!   error_diffusion    Floyd-Steinberg and Atkinson dithering (inkengine/photo.py, _error_diffusion)
//!   stipple_sites      which work pixels get a stipple dot (inkengine/photo.py, stipple_sites)
//!   engrave_band       one engraving line's stretches (inkengine/photo.py, _engrave_band)
//!   gauss_blur         separable Gaussian blur (inkengine/photo.py: line drawing, colour by number)
//!   despeckle          clear away small black blobs (inkengine/photo.py: line drawing)
//!   chamfer            the two chamfer passes of a distance map (inkengine/cbn.py, distance)

use numpy::ndarray::Array2;
use numpy::{IntoPyArray, PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;

/// For each corner pattern (top-left, top-right, bottom-right, bottom-left above the level = 8, 4, 2, 1):
/// the cell edges the line crosses, as pairs. 0 = top, 1 = right, 2 = bottom, 3 = left; -1 = no second segment.
/// The same table as contour.py's _SEGMENTS, in the same order.
const SEGMENTS: [[(i8, i8); 2]; 16] = [
    [(-1, -1), (-1, -1)], // 0: nothing
    [(3, 2), (-1, -1)],   // 1: L-B
    [(2, 1), (-1, -1)],   // 2: B-R
    [(3, 1), (-1, -1)],   // 3: L-R
    [(0, 1), (-1, -1)],   // 4: T-R
    [(0, 1), (3, 2)],     // 5: T-R, L-B
    [(0, 2), (-1, -1)],   // 6: T-B
    [(3, 0), (-1, -1)],   // 7: L-T
    [(3, 0), (-1, -1)],   // 8: L-T
    [(0, 2), (-1, -1)],   // 9: T-B
    [(3, 0), (2, 1)],     // 10: L-T, B-R
    [(0, 1), (-1, -1)],   // 11: T-R
    [(3, 1), (-1, -1)],   // 12: L-R
    [(2, 1), (-1, -1)],   // 13: B-R
    [(3, 2), (-1, -1)],   // 14: L-B
    [(-1, -1), (-1, -1)], // 15: nothing
];

fn contour_segments(f: &numpy::ndarray::ArrayView2<f64>, level: f64, box_x: f64, box_y: f64, step: i64) -> Vec<f64> {
    let (rows, cols) = f.dim();
    let stepf = step as f64;
    let mut out = Vec::new();
    if rows < 2 || cols < 2 {
        return out;
    }
    for j in 0..rows - 1 {
        // row by row, left to right: the order numpy's nonzero gives, and the JavaScript's loops
        let y0 = box_y + ((j as i64 * step) as f64);
        for i in 0..cols - 1 {
            let a = f[(j, i)];
            let b = f[(j, i + 1)];
            let c = f[(j + 1, i + 1)];
            let d = f[(j + 1, i)];
            let idx = ((a > level) as usize) * 8
                | ((b > level) as usize) * 4
                | ((c > level) as usize) * 2
                | ((d > level) as usize);
            if idx == 0 || idx == 15 {
                continue;
            }
            let x0 = box_x + ((i as i64 * step) as f64);
            // the same expressions as contour.py, evaluated left to right as numpy does
            let edge = |e: i8| -> (f64, f64) {
                match e {
                    0 => (x0 + stepf * (level - a) / (b - a), y0),
                    1 => (x0 + stepf, y0 + stepf * (level - b) / (c - b)),
                    2 => (x0 + stepf * (level - d) / (c - d), y0 + stepf),
                    _ => (x0, y0 + stepf * (level - a) / (d - a)),
                }
            };
            for &(p, q) in SEGMENTS[idx].iter() {
                if p < 0 {
                    break;
                }
                let (px, py) = edge(p);
                let (qx, qy) = edge(q);
                out.extend_from_slice(&[px, py, qx, qy]);
            }
        }
    }
    out
}

/// contour_level(F, level, box_x, box_y, step) -> float64 array (n, 4): each segment's x0, y0, x1, y1.
/// F is the height grid (rows, cols); cell (j, i) has its top-left corner at (box_x + i*step, box_y + j*step).
#[pyfunction]
fn contour_level<'py>(
    py: Python<'py>,
    f: PyReadonlyArray2<'py, f64>,
    level: f64,
    box_x: f64,
    box_y: f64,
    step: i64,
) -> PyResult<Bound<'py, PyArray2<f64>>> {
    let view = f.as_array();
    let flat = py.allow_threads(|| contour_segments(&view, level, box_x, box_y, step));
    let n = flat.len() / 4;
    let arr = Array2::from_shape_vec((n, 4), flat).map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok(arr.into_pyarray(py))
}

fn diffuse(lum: &[f32], mask: &[u8], ww: usize, wh: usize, t: f64, atkinson: bool) -> Vec<u8> {
    // L holds 32-bit floats, and every update is done in double precision then rounded back to 32 bits:
    // exactly what Python does with array("f") (and the JavaScript with a Float32Array).
    let mut l: Vec<f32> = lum.to_vec();
    let mut out = vec![255u8; ww * wh];
    const FS: [(i64, i64, f64); 4] = [(1, 0, 7.0 / 16.0), (-1, 1, 3.0 / 16.0), (0, 1, 5.0 / 16.0), (1, 1, 1.0 / 16.0)];
    const AT: [(i64, i64); 6] = [(1, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (0, 2)];
    let (wwi, whi) = (ww as i64, wh as i64);
    for y in 0..whi {
        let s: i64 = if y & 1 == 1 { -1 } else { 1 }; // serpentine scan avoids directional streaks
        let row = y * wwi;
        for k in 0..wwi {
            let x = if s > 0 { k } else { wwi - 1 - k };
            let i = (row + x) as usize;
            if mask[i] == 0 {
                continue;
            }
            let v = l[i] as f64;
            let o = if v < t { 0.0 } else { 255.0 };
            let e = v - o;
            out[i] = o as u8;
            if atkinson {
                let w8 = e * 0.125;
                for &(dx, dy) in AT.iter() {
                    let (xx, yy) = (x + dx * s, y + dy);
                    if xx >= 0 && xx < wwi && yy < whi {
                        let j = (yy * wwi + xx) as usize;
                        if mask[j] != 0 {
                            l[j] = (l[j] as f64 + w8) as f32;
                        }
                    }
                }
            } else {
                for &(dx, dy, wt) in FS.iter() {
                    let (xx, yy) = (x + dx * s, y + dy);
                    if xx >= 0 && xx < wwi && yy < whi {
                        let j = (yy * wwi + xx) as usize;
                        if mask[j] != 0 {
                            l[j] = (l[j] as f64 + e * wt) as f32;
                        }
                    }
                }
            }
        }
    }
    out
}

/// error_diffusion(lum, mask, ww, wh, t, atkinson) -> bytes of 0 and 255, one per pixel.
/// lum: float32 array of ww*wh tones; mask: uint8 array, 0 where there is no picture (left white, takes no part).
#[pyfunction]
fn error_diffusion<'py>(
    py: Python<'py>,
    lum: PyReadonlyArray1<'py, f32>,
    mask: PyReadonlyArray1<'py, u8>,
    ww: usize,
    wh: usize,
    t: f64,
    atkinson: bool,
) -> PyResult<Bound<'py, PyBytes>> {
    let (lum, mask) = (lum.as_slice()?, mask.as_slice()?);
    if lum.len() != ww * wh || mask.len() != ww * wh {
        return Err(PyValueError::new_err("lum and mask need ww * wh values each"));
    }
    let out = py.allow_threads(|| diffuse(lum, mask, ww, wh, t, atkinson));
    Ok(PyBytes::new(py, &out))
}

/// darkness 0..1 of a tone, as photo.py's _darkness: 1 - min(255, max(0, v)) / 255, flipped when inverted
#[inline]
fn darkness(v: f64, inv: bool) -> f64 {
    let d = 1.0 - v.max(0.0).min(255.0) / 255.0;
    if inv {
        1.0 - d
    } else {
        d
    }
}

/// photo.py's _js_round: floor(x + 0.5)
#[inline]
fn js_round(x: f64) -> i64 {
    (x + 0.5).floor() as i64
}

/// photo.py's stipple_nudge: a fixed pseudo-random number in [-1, 1) for site i (32-bit multiplies, as Math.imul)
#[inline]
fn stipple_nudge(i: u32, k: u32) -> f64 {
    let mut h = i.wrapping_mul(374761393) ^ k.wrapping_mul(668265263);
    h = (h ^ (h >> 13)).wrapping_mul(1274126177);
    h ^= h >> 16;
    h as f64 / 2147483648.0 - 1.0
}

const STIPPLE_WOBBLE: f64 = 0.15;

fn stipple(lum: &[f32], mask: &[u8], ww: usize, wh: usize, inv: bool, table: &[f32]) -> Vec<i64> {
    let n = ww * wh;
    let mut l = vec![0f32; n];
    for i in 0..n {
        if mask[i] != 0 {
            l[i] = table[js_round(darkness(lum[i] as f64, inv) * 255.0) as usize];
        }
    }
    const FS: [(i64, i64, f64); 4] = [(1, 0, 7.0 / 16.0), (-1, 1, 3.0 / 16.0), (0, 1, 5.0 / 16.0), (1, 1, 1.0 / 16.0)];
    let (wwi, whi) = (ww as i64, wh as i64);
    let mut sites = Vec::new();
    for y in 0..whi {
        let s: i64 = if y & 1 == 1 { -1 } else { 1 };
        for k in 0..wwi {
            let x = if s > 0 { k } else { wwi - 1 - k };
            let i = (y * wwi + x) as usize;
            if mask[i] == 0 {
                continue;
            }
            let v = l[i] as f64;
            let o = if v >= 0.5 + STIPPLE_WOBBLE * stipple_nudge(i as u32, 3) { 1.0 } else { 0.0 };
            let err = v - o;
            if o > 0.0 {
                sites.push(i as i64);
            }
            for &(dx, dy, wt) in FS.iter() {
                let (xx, yy) = (x + dx * s, y + dy);
                if xx >= 0 && xx < wwi && yy < whi {
                    let j = (yy * wwi + xx) as usize;
                    if mask[j] != 0 {
                        l[j] = (l[j] as f64 + err * wt) as f32;
                    }
                }
            }
        }
    }
    sites.sort_unstable();
    sites
}

/// stipple_sites(lum, mask, ww, wh, inv, table) -> int64 array: the dotted work pixels, sorted.
/// table is photo.py's STIPPLE_F (256 float32 values: darkness -> share of sites to dot).
#[pyfunction]
fn stipple_sites<'py>(
    py: Python<'py>,
    lum: PyReadonlyArray1<'py, f32>,
    mask: PyReadonlyArray1<'py, u8>,
    ww: usize,
    wh: usize,
    inv: bool,
    table: PyReadonlyArray1<'py, f32>,
) -> PyResult<Bound<'py, PyArray1<i64>>> {
    let (lum, mask, table) = (lum.as_slice()?, mask.as_slice()?, table.as_slice()?);
    if lum.len() != ww * wh || mask.len() != ww * wh {
        return Err(PyValueError::new_err("lum and mask need ww * wh values each"));
    }
    if table.len() != 256 {
        return Err(PyValueError::new_err("table needs 256 values"));
    }
    if ww * wh > u32::MAX as usize {
        return Err(PyValueError::new_err("picture too big"));
    }
    let sites = py.allow_threads(|| stipple(lum, mask, ww, wh, inv, table));
    Ok(sites.into_pyarray(py))
}

#[allow(clippy::too_many_arguments)]
fn engrave(lum: &[f32], mask: &[u8], ww: usize, wh: usize, inv: bool, band: usize, pitch: usize, step: usize) -> (Vec<f64>, Vec<i64>) {
    let mut pts: Vec<f64> = Vec::new();
    let mut lens: Vec<i64> = Vec::new();
    let y0 = band * pitch;
    if y0 >= wh || ww == 0 {
        return (pts, lens);
    }
    let y1 = wh.min(y0 + pitch);
    let mid = (y0 + y1) as f64 / 2.0;
    let p = pitch as f64;
    let mut seg = 0usize;
    let mut end = |pts: &mut Vec<f64>, seg: usize| {
        if seg >= 2 {
            lens.push(seg as i64);
        } else {
            pts.truncate(pts.len() - 3 * seg); // a stretch of one point draws nothing
        }
    };
    let mut x = 0usize;
    while x <= ww {
        let xi = (ww - 1).min(x);
        let (mut dark, mut n) = (0.0f64, 0usize);
        for yy in y0..y1 {
            let i = yy * ww + xi;
            if mask[i] != 0 {
                dark += darkness(lum[i] as f64, inv);
            }
            n += 1;
        }
        let hw = (dark / n as f64) * ((y1 - y0) as f64) / 2.0;
        let cy = mid + (x as f64 * 0.11 + band as f64 * 0.04).sin() * p * 0.22;
        if hw > 0.04 {
            pts.extend_from_slice(&[x as f64, cy, hw]);
            seg += 1;
        } else {
            end(&mut pts, seg);
            seg = 0;
        }
        x += step;
    }
    end(&mut pts, seg);
    (pts, lens)
}

/// engrave_band(lum, mask, ww, wh, inv, band, pitch, step) -> (points float64 (n, 3): x, cy, hw; lengths int64):
/// the stretches of one engraving line that have two points or more, as photo.py's _engrave_band.
#[pyfunction]
#[allow(clippy::too_many_arguments)]
fn engrave_band<'py>(
    py: Python<'py>,
    lum: PyReadonlyArray1<'py, f32>,
    mask: PyReadonlyArray1<'py, u8>,
    ww: usize,
    wh: usize,
    inv: bool,
    band: usize,
    pitch: usize,
    step: usize,
) -> PyResult<(Bound<'py, PyArray2<f64>>, Bound<'py, PyArray1<i64>>)> {
    let (lum, mask) = (lum.as_slice()?, mask.as_slice()?);
    if lum.len() != ww * wh || mask.len() != ww * wh {
        return Err(PyValueError::new_err("lum and mask need ww * wh values each"));
    }
    if pitch == 0 || step == 0 {
        return Err(PyValueError::new_err("pitch and step must be at least 1"));
    }
    let (pts, lens) = engrave(lum, mask, ww, wh, inv, band, pitch, step);
    let n = pts.len() / 3;
    let arr = Array2::from_shape_vec((n, 3), pts).map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok((arr.into_pyarray(py), lens.into_pyarray(py)))
}

fn blur(src: &[f32], w: usize, h: usize, k: &[f64]) -> Vec<f32> {
    // tap by tap, left to right, each product rounded then added in 64 bits, edges clamped: the same sums as
    // photo.py's numpy version (and the JavaScript), so the same 32-bit results
    // (each output's taps are still added in order; looping over the taps outside lets the compiler vectorise
    // across the row, which changes nothing in any one sum)
    let r = k.len() / 2;
    let hi = h as i64;
    let mut tmp = vec![0f32; w * h];
    let mut pad = vec![0f64; w + 2 * r];
    let mut acc = vec![0f64; w];
    for y in 0..h {
        let row = &src[y * w..(y + 1) * w];
        for (j, p) in pad.iter_mut().enumerate() {
            *p = row[j.saturating_sub(r).min(w - 1)] as f64;   // clamped edges
        }
        acc.iter_mut().for_each(|v| *v = 0.0);
        for (n, &kn) in k.iter().enumerate() {
            for (a, &v) in acc.iter_mut().zip(&pad[n..n + w]) {
                *a += v * kn;
            }
        }
        for (t, &a) in tmp[y * w..(y + 1) * w].iter_mut().zip(&acc) {
            *t = a as f32;
        }
    }
    let mut out = vec![0f32; w * h];
    for y in 0..hi {
        acc.iter_mut().for_each(|v| *v = 0.0);
        for (n, &kn) in k.iter().enumerate() {
            let yy = (y + n as i64 - r as i64).clamp(0, hi - 1) as usize;
            let row = &tmp[yy * w..(yy + 1) * w];
            for (a, &v) in acc.iter_mut().zip(row) {
                *a += v as f64 * kn;
            }
        }
        for (o, &a) in out[y as usize * w..(y as usize + 1) * w].iter_mut().zip(&acc) {
            *o = a as f32;
        }
    }
    out
}

/// gauss_blur(src, w, h, k) -> float32 array: src (float32, w*h) blurred across then down with the taps k
/// (float64, an odd number of them, already rounded as photo.py rounds them), edges clamped.
#[pyfunction]
fn gauss_blur<'py>(
    py: Python<'py>,
    src: PyReadonlyArray1<'py, f32>,
    w: usize,
    h: usize,
    k: PyReadonlyArray1<'py, f64>,
) -> PyResult<Bound<'py, PyArray1<f32>>> {
    let (src, k) = (src.as_slice()?, k.as_slice()?);
    if src.len() != w * h || w == 0 || h == 0 {
        return Err(PyValueError::new_err("src needs w * h values"));
    }
    if k.len() % 2 != 1 {
        return Err(PyValueError::new_err("k needs an odd number of taps"));
    }
    let out = py.allow_threads(|| blur(src, w, h, k));
    Ok(out.into_pyarray(py))
}

fn despeckle_blobs(img: &mut [u8], w: usize, h: usize, min_size: usize) {
    let mut seen = vec![false; w * h];
    let mut stack: Vec<usize> = Vec::new();
    let mut blob: Vec<usize> = Vec::new();
    for i in 0..w * h {
        if img[i] != 0 || seen[i] {
            continue;
        }
        stack.clear();
        blob.clear();
        stack.push(i);
        seen[i] = true;
        while let Some(q) = stack.pop() {
            blob.push(q);
            let (x, y) = ((q % w) as i64, (q / w) as i64);
            for dy in -1..=1i64 {
                let yy = y + dy;
                if yy < 0 || yy >= h as i64 {
                    continue;
                }
                for dx in -1..=1i64 {
                    let xx = x + dx;
                    if xx < 0 || xx >= w as i64 {
                        continue;
                    }
                    let j = yy as usize * w + xx as usize;
                    if img[j] == 0 && !seen[j] {
                        seen[j] = true;
                        stack.push(j);
                    }
                }
            }
        }
        if blob.len() < min_size {
            for &j in blob.iter() {
                img[j] = 255;
            }
        }
    }
}

/// despeckle(img, w, h, min_size) -> bytes: img (w*h bytes of 0 and 255) with the black blobs (8-connected)
/// smaller than min_size pixels turned white.
#[pyfunction]
fn despeckle<'py>(py: Python<'py>, img: &[u8], w: usize, h: usize, min_size: usize) -> PyResult<Bound<'py, PyBytes>> {
    if img.len() != w * h {
        return Err(PyValueError::new_err("img needs w * h bytes"));
    }
    let mut out = img.to_vec();
    py.allow_threads(|| despeckle_blobs(&mut out, w, h, min_size));
    Ok(PyBytes::new(py, &out))
}

fn chamfer_passes(d: &mut [f32], w: usize, h: usize) {
    // index.html's two passes, cell by cell: the smallest neighbour plus 1 or sqrt 2, in 64 bits, stored in 32
    let s2 = std::f64::consts::SQRT_2;
    if h < 2 || w < 3 {
        return;
    }
    for y in 1..h {
        for x in 1..w - 1 {
            let i = y * w + x;
            let cur = d[i];
            if cur <= 1.0 {
                continue;
            }
            let near = (d[i - 1] as f64 + 1.0)
                .min(d[i - w] as f64 + 1.0)
                .min(d[i - w - 1] as f64 + s2)
                .min(d[i - w + 1] as f64 + s2);
            d[i] = (cur as f64).min(near) as f32;
        }
    }
    for y in (0..h - 1).rev() {
        for x in (1..w - 1).rev() {
            let i = y * w + x;
            let cur = d[i];
            if cur <= 1.0 {
                continue;
            }
            let near = (d[i + 1] as f64 + 1.0)
                .min(d[i + w] as f64 + 1.0)
                .min(d[i + w + 1] as f64 + s2)
                .min(d[i + w - 1] as f64 + s2);
            d[i] = (cur as f64).min(near) as f32;
        }
    }
}

/// chamfer(d, w, h) -> float32 array: the forward and backward chamfer passes over a distance map whose cells
/// start at 0 (outside every region), 1 (on a region's edge) or 1e9 (inside), as cbn.py's distance.
#[pyfunction]
fn chamfer<'py>(py: Python<'py>, d: PyReadonlyArray1<'py, f32>, w: usize, h: usize) -> PyResult<Bound<'py, PyArray1<f32>>> {
    let src = d.as_slice()?;
    if src.len() != w * h {
        return Err(PyValueError::new_err("d needs w * h values"));
    }
    let mut out = src.to_vec();
    py.allow_threads(|| chamfer_passes(&mut out, w, h));
    Ok(out.into_pyarray(py))
}

#[pymodule]
fn inkline_fast(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(contour_level, m)?)?;
    m.add_function(wrap_pyfunction!(error_diffusion, m)?)?;
    m.add_function(wrap_pyfunction!(stipple_sites, m)?)?;
    m.add_function(wrap_pyfunction!(engrave_band, m)?)?;
    m.add_function(wrap_pyfunction!(gauss_blur, m)?)?;
    m.add_function(wrap_pyfunction!(despeckle, m)?)?;
    m.add_function(wrap_pyfunction!(chamfer, m)?)?;
    Ok(())
}

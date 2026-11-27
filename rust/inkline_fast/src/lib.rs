//! inkline_fast: Rust versions of two inner loops in Inkline's Python engine, as a trial.
//!
//! Both give exactly the numbers the Python code gives (same operations, same order, same rounding), so a
//! page looks the same with or without this module. Inkline works without it: the Python code is used
//! whenever `import inkline_fast` fails. See docs/performance.md.
//!
//!   contour_level      marching squares for one contour level (inkengine/patterns/contour.py)
//!   error_diffusion    Floyd-Steinberg and Atkinson dithering (inkengine/photo.py, _error_diffusion)

use numpy::ndarray::Array2;
use numpy::{IntoPyArray, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
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

#[pymodule]
fn inkline_fast(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(contour_level, m)?)?;
    m.add_function(wrap_pyfunction!(error_diffusion, m)?)?;
    Ok(())
}

# Emulsion Droplets Analysis Toolkit

A unified toolkit for comprehensive emulsion droplet analysis, integrating segmentation, spatial distribution analysis, and shape characterization into a single pipeline.

## Pipeline Overview

This toolkit supports the complete analysis workflow for emulsion droplet images:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌──────────────────────┐
│   Raw Images    │───▶│   ① Segmentation  │───▶│ ② Spatial Stats │───▶│ ③ Shape Analysis     │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └──────────────────────┘
                      Cellpose + ImageJ           RDF + Voronoi           Polygon Fitting
                      → particle.csv              → CN, g(r)              → best_n, rms_error
```

| Stage | Module | Description |
|-------|--------|-------------|
| ① Segmentation | `segmentation/` | Segment droplets from images, measure area/roundness, filter by quality |
| ② Spatial Stats | `spatial_analysis/` | Compute radial distribution function (RDF) and coordination number |
| ③ Shape Analysis | `shape_analysis/` | Fit convex polygons (3–20 sides) to droplet contours |

---

## Directory Structure

```
emulsion_droplets_analysis/
├── README.md
├── requirements.txt
├── segmentation/                         # Stage ①: Segmentation & Measurement
│   ├── CB3.sh                            #   CellPose batch script
│   ├── cell_count_4_batch.ijm            #   ImageJ macro: area/diameter measurement
│   └── batch_filter.py                   #   Filter by roundness threshold
├── spatial_analysis/                      # Stage ②: Spatial Distribution
│   ├── RDF_calculate.py                  #   Compute radial distribution function g(r)
│   ├── RDF_coordination.py               #   Derive coordination number from RDF
│   └── voronoi_coordination.py           #   Voronoi tessellation coordination number
└── shape_analysis/                        # Stage ③: Shape Fitting
    ├── Export_Contours_WithEdgeFilter.ijm #   ImageJ macro: export droplet contours
    ├── polygon_fit_cmd.py                 #   Fit convex polygons to contours
    └── run_pipeline.sh                   #   Batch processing script (Linux/macOS)
```

---

## Stage ① — Segmentation & Measurement (`segmentation/`)

**Goal:** Convert raw microscopy images into a CSV table of particle coordinates and properties.

### Workflow

```
Raw Images (.tif)
    │
    ▼  CB3.sh (CellPose)
Segmented Masks + Overlays
    │
    ▼  cell_count_4_batch.ijm (ImageJ)
Measurements CSV (area, diameter, roundness, x, y, ...)
    │
    ▼  batch_filter.py
Filtered CSV (roundness ≥ threshold)
```

### Step 1 — CellPose Segmentation

```bash
chmod +x CB3.sh
./CB3.sh
```

- Runs CellPose in batch mode on all images in the designated directory.
- Outputs masks and overlay images.

### Step 2 — ImageJ Measurement

Open Fiji/ImageJ and run `cell_count_4_batch.ijm`, or use headless mode:

```bash
fiji --headless --console -macro cell_count_4_batch.ijm "input=/path/to/images output=/path/to/results"
```

**Scale reference** (set in ImageJ before running):

| Magnification | Physical Size | Pixels |
|----------------|---------------|--------|
| 80× | 8 μm | 100 px |
| 40× | 16 μm | 100 px |
| 20× | 32 μm | 100 px |
| 4.2× | 153 μm | 100 px |

**Tip:** Use `scale_bar.ijm` (from original repo) to add scale bars to output images.

### Step 3 — Filter by Roundness

```bash
python batch_filter.py /path/to/measurements --threshold 0.85
```

- Default threshold: **roundness ≥ 0.85**
- Output: filtered CSV retaining only high-quality, roughly circular droplets.

---

## Stage ② — Spatial Distribution (`spatial_analysis/`)

**Goal:** Characterize the spatial arrangement of droplets — are they randomly distributed, clustered, or ordered?

### Requirements

```bash
pip install numpy scipy pandas matplotlib
```

### Tool 1 — Radial Distribution Function (RDF)

```bash
python RDF_calculate.py -i /path/to/scatter -o rdf_results --rmax 50.0 --dr 0.05 --x-col 3 --y-col 4
```

| Argument | Default | Description |
|----------|---------|-------------|
| `-i, --input` | `.` | Root input directory (recursive) |
| `-o, --output` | `rdf_results` | Output root directory |
| `--rmax` | `50.0` | Maximum distance |
| `--dr` | `0.05` | Bin width |
| `--x-col` | `3` | X column index (0-based) |
| `--y-col` | `4` | Y column index (0-based) |

Outputs: `*_rdf.txt` data files and `.png` plots per input CSV.

### Tool 2 — Coordination Number from RDF

```bash
python RDF_coordination.py -i /path/to/original -o /path/to/rdf_results \
    --rmax 50.0 --rc-method radius --radius-factor 1.2 \
    --x-col 3 --y-col 4 --area-col 1
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--rc-method` | `radius` | `auto` (first RDF minimum) or `radius` (2×mean_radius × factor) |
| `--radius-factor` | `1.2` | Multiplier for radius method |

Output: `subfolder.txt` with columns: `Contact_Threshold(rc)`, `Coordination_Number(CN)`, `Number_of_Points(N)`, `Global_Density(rho)`, `Mean_Radius`.

### Tool 3 — Voronoi Coordination Number

```bash
python voronoi_coordination.py -b /path/to/data -o voronoi_results.txt --x-col 4 --y-col 5
```

Outputs per-file mean and std of the number of Voronoi natural neighbors.

---

## Stage ③ — Shape Analysis (`shape_analysis/`)

**Goal:** Determine which regular polygon best describes each droplet's shape.

### Requirements

```bash
pip install numpy pandas opencv-python shapely tqdm
```

### Workflow

```
Images (.tif) + ROI zip files
    │
    ▼  Export_Contours_WithEdgeFilter.ijm (ImageJ)
Contour CSVs (*_contour.csv)
    │
    ▼  polygon_fit_cmd.py (Python)
Polygon fit results (*_polygon.csv)
```

### Batch Processing (Linux/macOS)

```bash
chmod +x run_pipeline.sh
./run_pipeline.sh /path/to/images /path/to/output
```

### Individual Steps

**Export contours only:**

```bash
fiji --headless --console -macro Export_Contours_WithEdgeFilter.ijm "/path/to/image.tif||/path/to/output"
```

**Fit polygons only:**

```bash
python polygon_fit_cmd.py -i /path/to/contour.csv -o result.csv
```

Optional arguments:
- `--n-min N` — minimum number of polygon sides (default: 3)
- `--n-max N` — maximum number of polygon sides (default: 20)
- `--min-points N` — minimum contour points to process (default: 10)

### Output

`*_polygon.csv` contains:

| Column | Description |
|--------|-------------|
| `roi_id` | Droplet ID |
| `best_n` | Best-fit polygon number of sides |
| `rms_error` | RMS distance from contour to fitted polygon (pixels) |
| `num_points` | Number of contour points |

**Notes:**
- Lower `rms_error` → better polygon fit.
- Filter out `num_points < 20` to remove spurious fits.
- `rms_error = 0` usually indicates a perfect geometric shape (rare for real droplets).

### Adjusting Edge/Convexity Filter

If too many valid droplets are filtered out, edit `Export_Contours_WithEdgeFilter.ijm` and increase the convexity threshold (default: `1.02`) to e.g. `1.05`, or comment out the convexity filter loop.

---

## Full Pipeline Integration

The three stages are designed to be used sequentially:

```
# Stage ①: Get particle coordinates
./segmentation/CB3.sh
# → produces measurement CSVs

# Stage ②: Analyze spatial distribution
python spatial_analysis/RDF_calculate.py -i ./scatter -o ./rdf_results
python spatial_analysis/RDF_coordination.py -i . -o ./rdf_results --rc-method radius
python spatial_analysis/voronoi_coordination.py -b . -o voronoi.txt

# Stage ③: Analyze droplet shape
./shape_analysis/run_pipeline.sh /path/to/images /path/to/output
```

---

## Requirements Summary

### Python Dependencies

```txt
# Core
numpy
scipy
pandas
matplotlib

# Shape analysis
opencv-python
shapely
tqdm
```

Install all at once:

```bash
pip install numpy scipy pandas matplotlib opencv-python shapely tqdm
```

### External Tools

| Tool | Purpose | Link |
|------|---------|------|
| **CellPose** | Deep-learning-based cell/droplet segmentation | https://www.cellpose.org/ |
| **Fiji / ImageJ** | Image processing, ROI management, measurement macros | https://fiji.sc/ |

---

## Original Repositories

This toolkit merges the following three repositories:

| Original Repo | Function |
|--------------|----------|
| `Batch4Images-main` | Image segmentation via CellPose + ImageJ measurement + roundness filtering |
| `emulsion_droplets_coordination_calculation-main` | RDF calculation, RDF-based and Voronoi coordination numbers |
| `emulsion_droplets_fit_ploygon-main` | Contour extraction + convex polygon fitting |

---

## License & Contact

Please refer to the original repositories for individual licenses. For issues or questions, open an issue in this merged repository or contact the original maintainers.

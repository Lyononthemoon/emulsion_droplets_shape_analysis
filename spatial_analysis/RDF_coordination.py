"""
RDF_coordination.py
基于 RDF 数据计算配位数（最近邻数）。
支持两种方法：'auto'（自动找谷底）和 'radius'（基于平均半径）。
需要原始 CSV 文件（含面积列）以计算平均半径和全局密度。
"""

import os
import numpy as np
import pandas as pd
import argparse

DEFAULT_INPUT_DIR = "."          # 原始数据根目录（包含子文件夹）
DEFAULT_OUTPUT_DIR = "rdf_results" # RDF 结果根目录（绝对或相对路径）
DEFAULT_RMAX = 50.0
DEFAULT_RC_METHOD = "radius"    # 'auto' 或 'radius'
DEFAULT_RADIUS_FACTOR = 1.2
DEFAULT_CSV_HAS_HEADER = True
DEFAULT_CSV_X_COL = 3           # D列（0-based）
DEFAULT_CSV_Y_COL = 4           # E列
DEFAULT_CSV_AREA_COL = 2        # C列

def parse_args():
    parser = argparse.ArgumentParser(description="计算 RDF 配位数")
    parser.add_argument("-i", "--input", default=DEFAULT_INPUT_DIR,
                        help=f"原始数据根目录（包含子文件夹，默认: {DEFAULT_INPUT_DIR}）")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_DIR,
                        help=f"RDF 结果根目录（绝对或相对路径，默认: {DEFAULT_OUTPUT_DIR}）")
    parser.add_argument("--rmax", type=float, default=DEFAULT_RMAX,
                        help=f"RDF 计算时的最大距离（用于计算面积，默认: {DEFAULT_RMAX}）")
    parser.add_argument("--rc-method", choices=["auto", "radius"], default=DEFAULT_RC_METHOD,
                        help="接触阈值确定方法（默认: radius）")
    parser.add_argument("--radius-factor", type=float, default=DEFAULT_RADIUS_FACTOR,
                        help="半径法因子，rc = factor * 2 * mean_radius（默认: 1.2）")
    parser.add_argument("--csv-header", action="store_true", default=DEFAULT_CSV_HAS_HEADER,
                        help="CSV文件包含表头")
    parser.add_argument("--csv-no-header", dest="csv_header", action="store_false",
                        help="CSV文件无表头")
    parser.add_argument("--x-col", type=int, default=DEFAULT_CSV_X_COL,
                        help="X坐标列索引（0-based）")
    parser.add_argument("--y-col", type=int, default=DEFAULT_CSV_Y_COL,
                        help="Y坐标列索引（0-based）")
    parser.add_argument("--area-col", type=int, default=DEFAULT_CSV_AREA_COL,
                        help="面积列索引（0-based，默认: 2）")
    return parser.parse_args()

def read_points_and_area(filepath, has_header, x_col, y_col, area_col):
    df = pd.read_csv(filepath, header=0 if has_header else None)
    x = pd.to_numeric(df.iloc[:, x_col], errors='coerce')
    y = pd.to_numeric(df.iloc[:, y_col], errors='coerce')
    area = pd.to_numeric(df.iloc[:, area_col], errors='coerce')
    valid = ~(np.isnan(x) | np.isnan(y) | np.isnan(area))
    x = x[valid]
    y = y[valid]
    area = area[valid]
    if len(x) == 0:
        raise ValueError("无有效数据")
    points = np.column_stack((x, y))
    return points, area

def find_first_valley(r, g):
    """直接找到第一峰后的最小值（谷底）"""
    peak_idx = np.argmax(g)
    after_peak = g[peak_idx+1:]
    if len(after_peak) == 0:
        return r[-1], len(r)-1
    valley_idx = np.argmin(after_peak) + peak_idx + 1
    return r[valley_idx], valley_idx

def compute_coordination_number(r, g, density, rc):
    idx = np.searchsorted(r, rc)
    integrand = g[:idx] * r[:idx]
    integral = np.trapz(integrand, r[:idx])
    CN = 2 * np.pi * density * integral
    return CN

def process_subfolder(subfolder, base_dir, rdf_dir, area, rc_method, radius_factor,
                      csv_has_header, csv_x_col, csv_y_col, csv_area_col):
    subfolder_path = os.path.join(rdf_dir, subfolder)
    if not os.path.isdir(subfolder_path):
        print(f"警告：RDF 子文件夹 {subfolder_path} 不存在，跳过")
        return
    rdf_files = [f for f in os.listdir(subfolder_path) if f.endswith("_rdf.txt")]
    if not rdf_files:
        print(f"子文件夹 {subfolder} 中没有 _rdf.txt 文件，跳过")
        return

    results = []
    for rdf_file in rdf_files:
        base_name = rdf_file.replace("_rdf.txt", "")
        # 原始文件路径（CSV 或 TXT）
        original_candidates = [
            os.path.join(base_dir, subfolder, base_name + ".csv"),
            os.path.join(base_dir, subfolder, base_name + ".txt")
        ]
        orig_file = None
        for cand in original_candidates:
            if os.path.exists(cand):
                orig_file = cand
                break
        if orig_file is None:
            print(f"  警告：找不到原始文件 {base_name}，跳过")
            continue

        try:
            points, areas = read_points_and_area(orig_file, csv_has_header,
                                                 csv_x_col, csv_y_col, csv_area_col)
        except Exception as e:
            print(f"  读取 {orig_file} 失败: {e}")
            continue

        N = len(points)
        if N < 2:
            continue
        density = N / area

        radii = np.sqrt(areas / np.pi)
        mean_radius = np.mean(radii)

        # 读取 RDF 数据
        rdf_path = os.path.join(subfolder_path, rdf_file)
        data = np.loadtxt(rdf_path, skiprows=1)
        r = data[:, 0]
        g = data[:, 1]

        if rc_method == 'auto':
            rc, _ = find_first_valley(r, g)
        else:  # radius
            rc = radius_factor * 2 * mean_radius

        CN = compute_coordination_number(r, g, density, rc)

        results.append({
            "file": base_name,
            "rc": rc,
            "CN": CN,
            "N": N,
            "density": density,
            "mean_radius": mean_radius
        })

    if results:
        output_file = os.path.join(rdf_dir, subfolder + ".txt")
        with open(output_file, "w") as f:
            f.write("File\tContact_Threshold(rc)\tCoordination_Number(CN)\tNumber_of_Points(N)\tGlobal_Density(rho)\tMean_Radius\n")
            for res in results:
                f.write(f"{res['file']}\t{res['rc']:.6f}\t{res['CN']:.6f}\t{res['N']}\t{res['density']:.6f}\t{res['mean_radius']:.6f}\n")
        print(f"子文件夹 {subfolder} 的结果已保存到 {output_file}")

def main():
    args = parse_args()
    # 系统面积：使用圆形近似（若已知实际面积可修改）
    area = np.pi * args.rmax ** 2
    rdf_dir_abs = os.path.abspath(args.output)
    if not os.path.isdir(rdf_dir_abs):
        print(f"错误：RDF 结果目录 {rdf_dir_abs} 不存在")
        return
    base_dir_abs = os.path.abspath(args.input)
    if not os.path.isdir(base_dir_abs):
        print(f"错误：原始数据根目录 {base_dir_abs} 不存在")
        return
    # 列出原始数据根目录下的子文件夹
    subfolders = [d for d in os.listdir(base_dir_abs) if os.path.isdir(os.path.join(base_dir_abs, d))]
    for sub in subfolders:
        process_subfolder(sub, base_dir_abs, rdf_dir_abs, area,
                          args.rc_method, args.radius_factor,
                          args.csv_header, args.x_col, args.y_col, args.area_col)
    print("全部处理完成！")

if __name__ == "__main__":
    main()

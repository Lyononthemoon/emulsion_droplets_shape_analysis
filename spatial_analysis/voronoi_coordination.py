"""
voronoi_coordination.py
计算二维点集的 Voronoi 配位数（每个点的自然邻居数）。
批量处理所有子文件夹中的 CSV 文件。
"""

import os
import numpy as np
import pandas as pd
import argparse
from scipy.spatial import Voronoi

DEFAULT_BASE_DIR = "."          # 项目根目录
DEFAULT_OUTPUT_FILE = "voronoi_coordination.txt"
DEFAULT_CSV_HAS_HEADER = True
DEFAULT_CSV_X_COL = 4
DEFAULT_CSV_Y_COL = 5

def parse_args():
    parser = argparse.ArgumentParser(description="计算 Voronoi 配位数")
    parser.add_argument("-b", "--base-dir", default=DEFAULT_BASE_DIR,
                        help=f"项目根目录（默认: {DEFAULT_BASE_DIR}）")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_FILE,
                        help=f"输出文件名（默认: {DEFAULT_OUTPUT_FILE}）")
    parser.add_argument("--csv-header", action="store_true", default=DEFAULT_CSV_HAS_HEADER,
                        help="CSV文件包含表头")
    parser.add_argument("--csv-no-header", dest="csv_header", action="store_false",
                        help="CSV文件无表头")
    parser.add_argument("--x-col", type=int, default=DEFAULT_CSV_X_COL,
                        help="X坐标列索引（0-based）")
    parser.add_argument("--y-col", type=int, default=DEFAULT_CSV_Y_COL,
                        help="Y坐标列索引（0-based）")
    return parser.parse_args()

def read_points_from_csv(filepath, has_header, x_col, y_col):
    df = pd.read_csv(filepath, header=0 if has_header else None)
    x = pd.to_numeric(df.iloc[:, x_col], errors='coerce')
    y = pd.to_numeric(df.iloc[:, y_col], errors='coerce')
    valid = ~(np.isnan(x) | np.isnan(y))
    x = x[valid]
    y = y[valid]
    if len(x) == 0:
        raise ValueError("无有效坐标")
    return np.column_stack((x, y))

def voronoi_coordination_numbers(points):
    vor = Voronoi(points)
    cn = np.zeros(len(points), dtype=int)
    for i, j in vor.ridge_points:
        cn[i] += 1
        cn[j] += 1
    return cn

def main():
    args = parse_args()
    # 收集所有 CSV 文件（跳过输出目录，若输出在 base_dir 内）
    all_files = []
    for root, dirs, files in os.walk(args.base_dir):
        # 可选：跳过包含输出文件的目录（如果输出文件就在 base_dir 下）
        if args.output in files:
            continue
        for f in files:
            if f.endswith(".csv"):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, args.base_dir)
                subfolder = os.path.dirname(rel_path)
                all_files.append((full_path, subfolder, f))

    results = []
    for filepath, subfolder, filename in all_files:
        print(f"处理: {filepath}")
        try:
            points = read_points_from_csv(filepath, args.csv_header, args.x_col, args.y_col)
            if len(points) < 3:
                print(f"  点数不足 3，跳过")
                continue
            cn_array = voronoi_coordination_numbers(points)
            mean_cn = np.mean(cn_array)
            std_cn = np.std(cn_array)
            results.append({
                "subfolder": subfolder,
                "file": filename,
                "points": len(points),
                "mean_voronoi_cn": mean_cn,
                "std_voronoi_cn": std_cn
            })
        except Exception as e:
            print(f"  处理失败: {e}")

    if results:
        df = pd.DataFrame(results)
        df = df.sort_values(["subfolder", "file"])
        output_path = os.path.join(args.base_dir, args.output)
        df.to_csv(output_path, sep="\t", index=False)
        print(f"结果已保存至: {output_path}")
    else:
        print("未找到有效 CSV 文件")

if __name__ == "__main__":
    main()

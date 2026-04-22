"""
RDF_calculate.py
计算二维点集的径向分布函数 (RDF)，支持批量处理子文件夹。
输入：CSV 或 TXT 文件，CSV 中可指定坐标列（默认 E、F 列）。
输出：每个文件对应的 RDF 数据（.txt）和图像（.png），保持子文件夹结构。
"""

import os
import math
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# ========== 默认配置（可通过命令行覆盖） ==========
DEFAULT_INPUT_DIR = "."          # 输入根目录（包含子文件夹）
DEFAULT_OUTPUT_DIR = "rdf_results"
DEFAULT_RMAX = 20.0              # 最大距离
DEFAULT_DR = 0.05                # 距离步长
DEFAULT_CSV_HAS_HEADER = True
DEFAULT_CSV_X_COL = 4            # E列（0-based）
DEFAULT_CSV_Y_COL = 5            # F列

def parse_args():
    parser = argparse.ArgumentParser(description="计算二维点集的径向分布函数")
    parser.add_argument("-i", "--input", default=DEFAULT_INPUT_DIR,
                        help=f"输入根目录（默认: {DEFAULT_INPUT_DIR}）")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_DIR,
                        help=f"输出根目录（默认: {DEFAULT_OUTPUT_DIR}）")
    parser.add_argument("--rmax", type=float, default=DEFAULT_RMAX,
                        help=f"最大距离（默认: {DEFAULT_RMAX}）")
    parser.add_argument("--dr", type=float, default=DEFAULT_DR,
                        help=f"距离步长（默认: {DEFAULT_DR}）")
    parser.add_argument("--csv-header", action="store_true", default=DEFAULT_CSV_HAS_HEADER,
                        help="CSV文件包含表头（默认: True）")
    parser.add_argument("--csv-no-header", dest="csv_header", action="store_false",
                        help="CSV文件无表头")
    parser.add_argument("--x-col", type=int, default=DEFAULT_CSV_X_COL,
                        help=f"X坐标列索引（0-based，默认: {DEFAULT_CSV_X_COL}）")
    parser.add_argument("--y-col", type=int, default=DEFAULT_CSV_Y_COL,
                        help=f"Y坐标列索引（0-based，默认: {DEFAULT_CSV_Y_COL}）")
    return parser.parse_args()

def radial_distribution_function(points, rmax, dr):
    N = len(points)
    if N < 2:
        return np.array([]), np.array([])
    total_density = N / (math.pi * rmax**2)
    num_bins = int(rmax / dr)
    rdf = np.zeros(num_bins)
    for i in range(N):
        xi, yi = points[i]
        for j in range(i+1, N):
            dx = xi - points[j][0]
            dy = yi - points[j][1]
            d = math.hypot(dx, dy)
            if d < rmax:
                idx = int(d / dr)
                rdf[idx] += 1
    r_vals = np.arange(0, rmax, dr)
    for i in range(num_bins):
        r = (i + 0.5) * dr
        area = 2 * math.pi * r * dr
        if area * N * total_density != 0:
            rdf[i] /= (area * N * total_density)
    return r_vals, rdf

def read_points_from_file(filepath, is_csv, has_header, x_col, y_col):
    if is_csv:
        df = pd.read_csv(filepath, header=0 if has_header else None)
        if df.shape[1] <= max(x_col, y_col):
            raise ValueError(f"列数不足，需要至少 {max(x_col, y_col)+1} 列")
        x = pd.to_numeric(df.iloc[:, x_col], errors='coerce')
        y = pd.to_numeric(df.iloc[:, y_col], errors='coerce')
        valid = ~(np.isnan(x) | np.isnan(y))
        x = x[valid]
        y = y[valid]
        if len(x) == 0:
            raise ValueError("没有有效的数值坐标")
        return np.column_stack((x, y))
    else:
        data = np.loadtxt(filepath)
        if data.ndim != 2 or data.shape[1] != 2:
            raise ValueError("TXT 文件必须包含两列数据")
        return data

def process_file(input_path, output_root, rmax, dr, csv_config):
    print(f"正在处理: {input_path}")
    try:
        ext = os.path.splitext(input_path)[1].lower()
        is_csv = ext == '.csv'
        if not is_csv and ext != '.txt':
            print(f"  跳过不支持的文件类型: {ext}")
            return
        points = read_points_from_file(input_path, is_csv,
                                       csv_config['has_header'],
                                       csv_config['x_col'],
                                       csv_config['y_col'])
        if len(points) < 2:
            print(f"  跳过（点数不足 2）")
            return
        r_vals, rdf = radial_distribution_function(points, rmax, dr)
        if len(r_vals) == 0:
            print(f"  计算失败")
            return
        # 构建输出路径（保持相对路径结构）
        rel_path = os.path.relpath(input_path, start=csv_config['input_root'])
        base_name = os.path.splitext(rel_path)[0]
        out_data = os.path.join(output_root, base_name + "_rdf.txt")
        out_plot = os.path.join(output_root, base_name + "_rdf.png")
        os.makedirs(os.path.dirname(out_data), exist_ok=True)
        data_out = np.column_stack((r_vals, rdf))
        np.savetxt(out_data, data_out, fmt='%.6f', delimiter='\t',
                   header='Distance\tg(r)')
        print(f"  数据已保存: {out_data}")
        plt.figure(figsize=(8,5))
        plt.plot(r_vals, rdf, 'b-', linewidth=1.5)
        plt.xlabel("r (μm)")
        plt.ylabel("g(r)")
        plt.title(f"Radial Distribution Function\n{os.path.basename(input_path)}")
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(out_plot, dpi=150)
        plt.close()
        print(f"  图片已保存: {out_plot}")
    except Exception as e:
        print(f"  处理失败: {e}")

def main():
    args = parse_args()
    csv_config = {
        'has_header': args.csv_header,
        'x_col': args.x_col,
        'y_col': args.y_col,
        'input_root': args.input   # 用于计算相对路径
    }
    if not os.path.isdir(args.input):
        print(f"错误：输入目录 '{args.input}' 不存在。")
        return
    for dirpath, dirnames, filenames in os.walk(args.input):
        for filename in filenames:
            if filename.endswith(('.csv', '.txt')):
                full_path = os.path.join(dirpath, filename)
                process_file(full_path, args.output, args.rmax, args.dr, csv_config)
    print("全部处理完成！")

if __name__ == "__main__":
    main()
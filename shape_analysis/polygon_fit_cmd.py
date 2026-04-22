import argparse
import numpy as np
import pandas as pd
import cv2
from shapely.geometry import Polygon, Point
from tqdm import tqdm

def convex_hull_points(points):
    hull = cv2.convexHull(points)
    return hull.squeeze()

def fit_polygon_to_contour(contour_points, n_sides, epsilon_factor=0.01):
    hull = convex_hull_points(contour_points)
    if len(hull) < n_sides:
        return None
    perimeter = cv2.arcLength(hull, True)
    epsilon = epsilon_factor * perimeter
    approx = cv2.approxPolyDP(hull, epsilon, True)
    max_iter = 100
    step = 0.95
    for _ in range(max_iter):
        if len(approx) == n_sides:
            break
        elif len(approx) > n_sides:
            epsilon *= step
        else:
            epsilon /= step
        approx = cv2.approxPolyDP(hull, epsilon, True)
        if len(approx) == n_sides:
            break
    approx = approx.squeeze()
    if approx.ndim == 1:
        approx = approx.reshape(-1, 2)
    if len(approx) != n_sides:
        return None
    return approx

def distance_point_to_polygon(point, polygon_vertices):
    if polygon_vertices is None or len(polygon_vertices) < 3:
        return float('inf')
    if polygon_vertices.ndim == 1:
        polygon_vertices = polygon_vertices.reshape(-1, 2)
    poly = Polygon(polygon_vertices)
    pt = Point(point)
    return poly.distance(pt)

def fit_best_polygon(contour_points, n_range=range(3,21), epsilon_factor=0.01):
    hull = convex_hull_points(contour_points)
    if len(hull) < min(n_range):
        return None, None, None, {}
    best_n = None
    best_error = float('inf')
    best_vertices = None
    errors = {}
    for n in n_range:
        if n > len(hull):
            errors[n] = float('inf')
            continue
        approx = fit_polygon_to_contour(contour_points, n, epsilon_factor)
        if approx is None:
            errors[n] = float('inf')
            continue
        dists = [distance_point_to_polygon(p, approx) for p in contour_points]
        rms_error = np.sqrt(np.mean(np.square(dists)))
        errors[n] = rms_error
        if rms_error < best_error:
            best_error = rms_error
            best_n = n
            best_vertices = approx
    return best_n, best_error, best_vertices, errors

def main():
    parser = argparse.ArgumentParser(description="多边形拟合：对液滴轮廓点CSV进行凸多边形最优边数拟合")
    parser.add_argument("-i", "--input", required=True, help="输入CSV文件路径（格式：roi_id,x,y，无表头，不同ROI间空行分隔）")
    parser.add_argument("-o", "--output", required=True, help="输出结果CSV文件路径")
    parser.add_argument("--n-min", type=int, default=3, help="最小拟合边数（默认3）")
    parser.add_argument("--n-max", type=int, default=20, help="最大拟合边数（默认20）")
    parser.add_argument("--min-points", type=int, default=10, help="轮廓点最少数量（默认10）")
    parser.add_argument("--epsilon-factor", type=float, default=0.01, help="多边形逼近的初始epsilon因子（默认0.01）")
    args = parser.parse_args()

    # 读取轮廓点CSV（无表头，三列：roi_id, x, y）
    df = pd.read_csv(args.input, header=None, names=["roi_id", "x", "y"])
    grouped = df.groupby("roi_id")
    n_range = range(args.n_min, args.n_max + 1)

    results = []
    for roi_id, group in tqdm(grouped, desc="Processing ROIs"):
        points = group[["x", "y"]].values.astype(np.float32)
        if len(points) < args.min_points:
            continue
        best_n, best_error, _, _ = fit_best_polygon(points, n_range=n_range, epsilon_factor=args.epsilon_factor)
        if best_n is not None:
            results.append({
                "roi_id": roi_id,
                "best_n": best_n,
                "fit_error_rms": best_error,
                "num_points": len(points)
            })

    if results:
        df_res = pd.DataFrame(results)
        df_res.to_csv(args.output, index=False)
        print(f"\n结果已保存至: {args.output}")
        print("最佳边数统计：")
        print(df_res['best_n'].value_counts().sort_index())
    else:
        print("未找到有效液滴轮廓。")

if __name__ == "__main__":
    main()
#!/bin/bash
# 全流程批处理：轮廓导出 + 多边形拟合（每个图像独立输出）
# 用法: ./run_pipeline.sh <图像目录> <输出目录>

INPUT_DIR="$1"
OUTPUT_DIR="$2"
MACRO="Export_Contours_WithEdgeFilter.ijm"
PYTHON_SCRIPT="polygon_fit_cmd.py"

if [ -z "$INPUT_DIR" ] || [ -z "$OUTPUT_DIR" ]; then
    echo "Usage: $0 <image_dir> <output_dir>"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

# 遍历所有 .tif 图像（可根据需要修改扩展名）
for img in "$INPUT_DIR"/*.tif; do
    if [ -f "$img" ]; then
        base=$(basename "$img" .tif)
        echo "=== Processing $base ==="

        # 1. 导出轮廓点（ImageJ）
        imagej --headless --console -batch "$MACRO" "$img||$OUTPUT_DIR"
        if [ $? -ne 0 ]; then
            echo "Error: ImageJ export failed for $base"
            continue
        fi

        # 2. 多边形拟合（Python）
        csv_file="$OUTPUT_DIR/${base}_contour.csv"
        if [ -f "$csv_file" ]; then
            python "$PYTHON_SCRIPT" -i "$csv_file" -o "$OUTPUT_DIR/${base}_polygon.csv"
        else
            echo "Warning: $csv_file not found, skipping fitting."
        fi
    fi
done

echo "All done. Results saved in $OUTPUT_DIR"
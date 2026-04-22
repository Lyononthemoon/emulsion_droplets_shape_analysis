#!/bin/bash

# 定义文件夹的路径
CP_DIR="/home/yang/Documents/lyon/Cellpose241105/"

# 遍历文件夹中的子目录
for subdir in "$CP_DIR"/*; do
    if [ -d "$subdir" ]; then
        # 如果子目录存在，进入子目录并执行 cellpose 命令
        subdir_name=$(basename "$subdir")
        echo "处理子目录: $subdir_name"
        
        # 在子目录中执行 cellpose 命令
        python -m cellpose --use_gpu --dir "$subdir" --diameter 0. --flow_threshold 3. --pretrained_model cyto3 --save_rois --verbose
        
        echo "完成处理子目录: $subdir_name"
    fi
done

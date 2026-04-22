import pandas as pd
import os
import sys
import glob

def filter_roundness(input_csv):
    """筛选单个CSV文件中圆度≥0.85的数据"""
    try:
        # 读取CSV文件
        df = pd.read_csv(input_csv)
        
        # 检测圆度列名（兼容不同格式）
        round_cols = [col for col in df.columns if 'round' in col.lower()]
        
        if not round_cols:
            print(f"警告: 文件 {input_csv} 中未找到圆度列。跳过处理。")
            return None
        
        round_col = round_cols[0]  # 使用第一个匹配的圆度列
        
        # 筛选圆度≥0.85的数据
        filtered_df = df[df[round_col] >= 0.85]
        
        # 创建输出文件名
        base_name, ext = os.path.splitext(input_csv)
        output_csv = f"{base_name}_s{ext}"
        
        # 保存筛选结果
        filtered_df.to_csv(output_csv, index=False)
        print(f"已筛选并保存结果至: {output_csv}")
        print(f"原始数据: {len(df)} 行, 筛选后: {len(filtered_df)} 行")
        return output_csv
    except Exception as e:
        print(f"处理文件 {input_csv} 时出错: {str(e)}")
        return None

def process_directory(directory):
    """处理单个目录中的所有CSV文件"""
    # 获取目录中所有CSV文件
    csv_files = glob.glob(os.path.join(directory, "*.csv"))
    
    # 过滤掉已处理的文件（以_s.csv结尾）
    csv_files = [f for f in csv_files if not f.endswith("_s.csv")]
    
    if not csv_files:
        print(f"在目录 {directory} 中未找到待处理的CSV文件")
        return 0
    
    print(f"\n{'='*50}")
    print(f"处理目录: {directory}")
    print(f"找到 {len(csv_files)} 个CSV文件待处理")
    
    # 处理每个文件
    processed_count = 0
    for file in csv_files:
        print("\n" + "-"*30)
        print(f"处理文件: {os.path.basename(file)}")
        result = filter_roundness(file)
        if result:
            processed_count += 1
    
    print(f"\n目录 {directory} 处理完成! 共处理 {processed_count} 个文件")
    return processed_count

def recursive_process(input_dir):
    """递归处理目录及其所有子目录"""
    total_processed = 0
    total_dirs = 0
    
    # 使用os.walk递归遍历所有子目录
    for root, dirs, files in os.walk(input_dir):
        # 处理当前目录
        processed = process_directory(root)
        if processed > 0:
            total_processed += processed
            total_dirs += 1
    
    print("\n" + "="*50)
    print("递归处理完成!")
    print(f"共处理 {total_dirs} 个目录, {total_processed} 个文件")
    return total_processed

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python recursive_filter.py <输入文件夹>")
        print("示例: python recursive_filter.py C:/实验数据/")
        sys.exit(1)
    
    input_dir = os.path.abspath(sys.argv[1])
    
    # 检查目录是否存在
    if not os.path.isdir(input_dir):
        print(f"错误: 目录 '{input_dir}' 不存在")
        sys.exit(1)
    
    print(f"开始递归处理目录: {input_dir}")
    recursive_process(input_dir)

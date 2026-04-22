// BatchMeasureFixedOrder2_withEdgeFilter.ijm
// 功能：批量处理文件夹中的图像，根据文件名索引自动设置标尺，加载同名 ROI ZIP，
//       删除边界接触的 ROI，然后测量并保存结果。

// 1. 选择包含图像和 _rois.zip 的文件夹
dir = getDirectory("Choose Directory");

// 定义 µm/pixel（可根据实际显微镜物镜调整）
scale20 = 32.0 / 100.0; // 0.32 µm/px (20×)
scale40 = 16.0 / 100.0; // 0.16 µm/px (40×)
scale80 =  8.0 / 100.0; // 0.08 µm/px (80×)

// 获取文件列表并过滤出图像文件（保持顺序）
allFiles = getFileList(dir);
imageList = newArray();
count = 0;
for (i = 0; i < allFiles.length; i++) {
    name = allFiles[i];
    if (endsWith(name, ".tif") || endsWith(name, ".tiff") ||
        endsWith(name, ".jpg") || endsWith(name, ".jpeg") ||
        endsWith(name, ".png") || endsWith(name, ".bmp")) {
        imageList[count] = name;
        count++;
    }
}

print("=== Image list (0–" + (count-1) + ") ===");
for (i = 0; i < count; i++) print(i + ": " + imageList[i]);

// 批处理主循环
for (i = 0; i < count; i++) {
    name = imageList[i];
    open(dir + name);
    
    // 根据索引设置标尺（前5张20×，接着5张40×，其余80×）
    if (i <= 4) {
        run("Set Scale...", "distance=1 known=" + scale20 + " unit=µm global");
    } else if (i <= 9) {
        run("Set Scale...", "distance=1 known=" + scale40 + " unit=µm global");
    } else {
        run("Set Scale...", "distance=1 known=" + scale80 + " unit=µm global");
    }
    
    // 加载同名 ROI ZIP 文件
    dot = lastIndexOf(name, ".");
    base = substring(name, 0, dot);
    roiZip = dir + base + "_rois.zip";
    roiManager("Reset");
    if (File.exists(roiZip)) {
        roiManager("Open", roiZip);
        print("Loaded ROI: " + roiZip);
    } else {
        print("Warning: missing ROI: " + roiZip);
        close();
        continue; // 无 ROI 则跳过该图像
    }
    
    
// ========== 边缘过滤：删除靠近图像边缘的 ROI ==========
width = getWidth();
height = getHeight();
edgeMargin = 5;   // 边缘阈值（像素），可自行调整
n = roiManager("count");
for (j = n-1; j >= 0; j--) {
    roiManager("select", j);
    Roi.getBounds(x, y, w, h);
    // 判断边界框是否靠近边缘（任一方向距离小于 edgeMargin）
    if (x < edgeMargin || y < edgeMargin || 
        (x + w) > (width - edgeMargin) || 
        (y + h) > (height - edgeMargin)) {
        roiManager("delete");
        print("  Removed edge-touching ROI #" + j);
    }
}
// ====================================================
     
    // 测量剩余 ROI
    if (roiManager("count") > 0) {
        roiManager("Measure");
        Table.applyMacro("Diameter = sqrt(4 * Area / PI);");
        // 保存结果
        saveAs("Results", dir + base + ".csv");
    } else {
        print("No ROI remaining after edge filtering for: " + name);
    }
    
    // 清理并关闭图像
    close("Results");
    roiManager("Reset");
    close();
}

print("Batch processing complete!");

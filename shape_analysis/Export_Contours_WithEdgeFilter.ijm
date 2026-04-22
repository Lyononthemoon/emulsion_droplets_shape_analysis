// Export_Contours.ijm (支持 headless 批处理，自动退出)
setBatchMode(true);

arg = getArgument();
if (arg == "") exit("No arguments.");
parts = split(arg, "||");
if (parts.length < 2) exit("Need two arguments separated by '||'");
imgPath = parts[0];
outDir = parts[1];
imgPath = replace(imgPath, "'", "");
outDir = replace(outDir, "'", "");

open(imgPath);
title = getTitle();
base = substring(title, 0, lastIndexOf(title, "."));

// 构造 ROI ZIP 路径
slash = lastIndexOf(imgPath, "/");
if (slash == -1) slash = lastIndexOf(imgPath, "\\");
if (slash == -1) {
    print("Error: cannot parse image path");
    close();
    exit();
}
dirPart = substring(imgPath, 0, slash+1);
roiZip = dirPart + base + "_rois.zip";

if (!File.exists(roiZip)) {
    print("Warning: ROI zip not found: " + roiZip);
    close();
    exit();
}
roiManager("Reset");
roiManager("Open", roiZip);

width = getWidth(); height = getHeight();

// 1. 删除与图像边界相交的 ROI（边缘效应）
for (i = roiManager("count")-1; i >= 0; i--) {
    roiManager("select", i);
    Roi.getBounds(x, y, w, h);
    if (x <= 0 || y <= 0 || x+w >= width || y+h >= height) {
        roiManager("delete");
    }
}

// 2. 删除非凸的 ROI（凹多边形）- 使用相对阈值
for (i = roiManager("count")-1; i >= 0; i--) {
    roiManager("select", i);
    getStatistics(area, mean, min, max, std, histogram);
    origArea = area;
    run("Convex Hull");
    getStatistics(area, mean, min, max, std, histogram);
    convexArea = area;
    run("Undo");
    // 使用相对比例：凸包面积超过原面积 5% 则视为凹形
    if (convexArea > origArea * 1.05) {
        roiManager("select", i);
        roiManager("delete");
        print("  Removed concave ROI #" + i + " (origArea=" + origArea + ", convexArea=" + convexArea + ")");
    }
}

remaining = roiManager("count");
if (remaining == 0) {
    print("No ROIs left after edge and convexity filtering.");
    close();
    exit();
}
outFile = outDir + "/" + base + "_contour.csv";
if (File.exists(outFile)) File.delete(outFile);
for (i = 0; i < remaining; i++) {
    roiManager("select", i);
    getSelectionCoordinates(xp, yp);
    for (j = 0; j < xp.length; j++) {
        File.append("" + i + "," + xp[j] + "," + yp[j], outFile);
    }
    File.append("", outFile);
}
close();
print("Exported: " + outFile);

exit();
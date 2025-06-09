import cv2
import numpy as np
from matplotlib import pyplot as plt

# 1. 读入图像
img = cv2.imread('3214ace3-8cf0-46b4-97b1-392d23938cdc.png')

# 2. 转灰度
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# 3. 中值滤波（降噪）
blurred = cv2.medianBlur(gray, 3)

# 4. 阈值处理（字符前景提取）
_, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# 5. 红色竖线 & 网格去除（颜色掩膜 + inpainting）
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
# 红色范围掩膜（注意红色在HSV中有两个区段）
lower_red1 = np.array([0, 70, 50])
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([170, 70, 50])
upper_red2 = np.array([180, 255, 255])
mask_red = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)

# 蓝色范围掩膜（网格线）
lower_blue = np.array([100, 80, 50])
upper_blue = np.array([140, 255, 255])
mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

# 合并干扰掩膜
mask_interference = cv2.bitwise_or(mask_red, mask_blue)

# inpainting 去除红线和网格
img_inpainted = cv2.inpaint(img, mask_interference, 3, cv2.INPAINT_TELEA)

# 6. 再次灰度化 + 二值化
gray2 = cv2.cvtColor(img_inpainted, cv2.COLOR_BGR2GRAY)
_, clean_bin = cv2.threshold(gray2, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# 7. 显示预处理结果（可选）
plt.figure(figsize=(12, 6))
plt.subplot(1, 3, 1)
plt.title("Original")
plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
plt.axis("off")

plt.subplot(1, 3, 2)
plt.title("Mask & Inpainted")
plt.imshow(cv2.cvtColor(img_inpainted, cv2.COLOR_BGR2RGB))
plt.axis("off")

plt.subplot(1, 3, 3)
plt.title("Binarized Output")
plt.imshow(clean_bin, cmap='gray')
plt.axis("off")

plt.tight_layout()
plt.show()

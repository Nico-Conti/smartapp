import cv2
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from skimage import color
from collections import Counter

def calculate_delta_e(color1_lab, color2_lab):
    """
    Calculates the Euclidean distance in LAB space (Delta E).
    Low value (< 10) means colors look the same to the human eye.
    """
    return np.linalg.norm(color1_lab - color2_lab)

def extract_smart_color_distribution(image_path, k=5, sigma_scale=0.4, bg_threshold=15.0):
    """
    Smart extraction that samples corners to detect and remove background colors.
    
    Args:
        bg_threshold: The Delta E distance. If a color is closer than this 
                      to the background, it is removed.
    """
    # --- 1. Load & Preprocess ---
    img = cv2.imread(image_path)
    if img is None: return None, None, None
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w, c = img_rgb.shape
    
    # --- 2. Step A: Detect Background Color (Corner Sampling) ---
    # We take a 50x50 patch from the top-left corner
    corner_patch = img_rgb[0:50, 0:50, :]
    corner_lab = color.rgb2lab(corner_patch).reshape(-1, 3)
    # The average color of the corner is our "Forbidden Background Color"
    bg_color_lab = np.mean(corner_lab, axis=0)

    # --- 3. Step B: Gaussian Mask (Center Focus) ---
    x = np.linspace(-1, 1, w)
    y = np.linspace(-1, 1, h)
    X, Y = np.meshgrid(x, y)
    d = np.sqrt(X*X + Y*Y)
    mask = np.exp(-(d**2 / (2.0 * sigma_scale**2)))
    
    # Mask visualization
    mask_3d = mask[:, :, np.newaxis]
    masked_img = (img_rgb.astype(float) * mask_3d).astype(np.uint8)

    # --- 4. Filter Pixels ---
    flat_img = img_rgb.reshape(-1, 3)
    flat_mask = mask.reshape(-1)
    
    # Focus only on the center area
    valid_indices = flat_mask > 0.1
    center_pixels = flat_img[valid_indices]
    
    # --- 5. K-Means Clustering ---
    pixels_lab = color.rgb2lab(center_pixels[None, :, :]).reshape(-1, 3)
    
    # We ask for k+1 clusters, anticipating we might delete the background
    kmeans = KMeans(n_clusters=k+1, n_init=10, random_state=42)
    labels = kmeans.fit_predict(pixels_lab)
    centroids_lab = kmeans.cluster_centers_

    # --- 6. Smart Filtering (The Fix) ---
    label_counts = Counter(labels)
    total_pixels = len(pixels_lab)
    
    color_data = []
    
    for i in range(k+1):
        centroid = centroids_lab[i]
        
        # Calculate distance to the Background Color we found earlier
        diff = calculate_delta_e(centroid, bg_color_lab)
        
        # IF the color is too similar to the background corner, SKIP IT.
        if diff < bg_threshold:
            continue # This removes the grey/white bar!
            
        percent = label_counts[i] / total_pixels
        color_data.append({
            'lab': centroid,
            'percent': percent, # Note: Percentages won't sum to 1.0 anymore, that's fine.
            'rgb': color.lab2rgb(centroid.reshape(1,1,3)).reshape(3)
        })
        
    # Re-normalize percentages so they sum to 1.0 again (optional but cleaner)
    current_sum = sum([x['percent'] for x in color_data])
    if current_sum > 0:
        for item in color_data:
            item['percent'] = item['percent'] / current_sum
            
    # Sort by Dominance
    color_data.sort(key=lambda x: x['percent'], reverse=True)
    
    # Keep only top K requested colors
    return color_data[:k], img_rgb, masked_img

# --- VISUALIZATION FUNCTION (Same as before) ---
def visualize_analysis(color_data, original_img, masked_img):
    if not color_data: return
    fig, ax = plt.subplots(1, 3, figsize=(18, 5))
    ax[0].imshow(original_img); ax[0].set_title("Original")
    ax[0].axis('off')
    ax[1].imshow(masked_img); ax[1].set_title("Gaussian Mask")
    ax[1].axis('off')
    
    bar_height, bar_width = 50, 300
    bar = np.zeros((bar_height, bar_width, 3), dtype='uint8')
    start_x = 0
    for item in color_data:
        end_x = start_x + (item['percent'] * bar_width)
        c_rgb = (item['rgb'] * 255).astype('uint8') 
        cv2.rectangle(bar, (int(start_x), 0), (int(end_x), bar_height), 
                      color=c_rgb.tolist(), thickness=-1)
        start_x = end_x
    ax[2].imshow(bar); ax[2].set_title("Result (Background Removed)")
    ax[2].axis('off')
    plt.tight_layout(); plt.show()

# Run
data, orig, masked = extract_smart_color_distribution('image_test5.jpg', sigma_scale=0.6)
visualize_analysis(data, orig, masked)
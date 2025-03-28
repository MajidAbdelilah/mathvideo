import numpy as np

def color_similarity(color1, color2):
    """
    Calculate the similarity between two colors using optimized Euclidean distance.
    
    Args:
        color1: RGB or RGBA color tuple/array
        color2: RGB or RGBA color tuple/array
        
    Returns:
        A value between 0.0 and 1.0, where 1.0 means identical colors
    """
    # Convert to numpy arrays if they aren't already
    # Only consider RGB components (faster)
    c1 = np.asarray(color1[:3], dtype=np.float32)
    c2 = np.asarray(color2[:3], dtype=np.float32)
    
    # Fast squared distance calculation (avoid sqrt for performance)
    # Max possible squared distance in RGB space is 3 * 255^2 = 195075
    squared_distance = np.sum((c1 - c2) ** 2)
    max_squared_distance = 195075
    
    # Convert distance to similarity (1.0 = identical, 0.0 = maximally different)
    similarity = 1.0 - np.sqrt(squared_distance / max_squared_distance)
    
    return similarity

def color_distance(color1, color2, perceptual=True):
    """
    Calculate distance between two colors, optionally using perceptual weighting.
    
    Args:
        color1: RGB or RGBA color tuple/array (0-255 or 0-1 range)
        color2: RGB or RGBA color tuple/array (same range as color1)
        perceptual: Whether to use perceptual color weighting
        
    Returns:
        Distance value (unbounded)
    """
    # Convert to numpy arrays if they aren't already
    c1 = np.asarray(color1[:3], dtype=np.float32)
    c2 = np.asarray(color2[:3], dtype=np.float32)
    
    # Scale to 0-1 range if needed
    if np.max(c1) > 1.0 or np.max(c2) > 1.0:
        c1 = c1 / 255.0
        c2 = c2 / 255.0
    
    if perceptual:
        # Apply perceptual weights based on human color perception
        # Human eyes are more sensitive to green, less to blue
        weights = np.array([0.299, 0.587, 0.114])
        diff = c1 - c2
        return np.sqrt(np.sum(weights * diff * diff))
    else:
        # Standard Euclidean distance
        return np.sqrt(np.sum((c1 - c2) ** 2))

def variance_in_region(pixels_array):
    """Calculate the color variance in a region, useful for edge detection."""
    if not pixels_array:
        return 0
    
    # Convert to numpy array for fast calculations
    pixels = np.array(pixels_array)
    
    # Calculate variance across all color channels
    variance = np.var(pixels, axis=0).sum()
    
    # Normalize by maximum possible variance
    normalized_variance = variance / (3 * 255 * 255)
    
    return normalized_variance

def calculate_edge_strength(image, x, y, kernel_size=3):
    """
    Calculate edge strength at a pixel using Sobel operator.
    
    Args:
        image: Image array
        x, y: Pixel coordinates
        kernel_size: Size of kernel to use
        
    Returns:
        Edge strength value (0.0-1.0)
    """
    h, w = image.shape[:2]
    
    # Ensure we have enough pixels around the target
    if x < kernel_size//2 or y < kernel_size//2 or x >= w - kernel_size//2 or y >= h - kernel_size//2:
        return 0.0
    
    # Extract region around pixel
    radius = kernel_size // 2
    region = image[y-radius:y+radius+1, x-radius:x+radius+1]
    
    # Simple Sobel filters
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])
    
    # Apply filters to each channel and sum
    grad_x = 0
    grad_y = 0
    
    for channel in range(min(3, region.shape[2])):  # Only use RGB channels
        channel_data = region[:, :, channel].astype(float)
        grad_x += np.abs(np.sum(channel_data * sobel_x))
        grad_y += np.abs(np.sum(channel_data * sobel_y))
    
    # Calculate gradient magnitude and normalize
    gradient = np.sqrt(grad_x**2 + grad_y**2)
    max_gradient = 1.0 * kernel_size * kernel_size * 255 * 4  # Approximate maximum
    
    return min(1.0, gradient / max_gradient)

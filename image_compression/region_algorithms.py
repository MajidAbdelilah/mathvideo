import numpy as np
from collections import deque
import logging
from utils import color_similarity, color_distance

logger = logging.getLogger('region_algorithms')

class AdaptiveRegionGrower:
    """
    An advanced region growing algorithm that uses adaptive thresholds
    and considers both color similarity and local gradients.
    """
    
    def __init__(self, image_array, similarity_threshold=0.9, 
                 max_region_size=None, adaptive_mode=True):
        """
        Initialize the region grower.
        
        Args:
            image_array: NumPy array representing the image
            similarity_threshold: Value between 0.0 and 1.0, base threshold for similarity
            max_region_size: Maximum number of pixels in a region
            adaptive_mode: Whether to use adaptive thresholding based on local image characteristics
        """
        self.image = image_array
        self.height, self.width = image_array.shape[:2]
        self.base_threshold = similarity_threshold
        self.max_region_size = max_region_size or min(20000, (self.width * self.height) // 10)
        self.adaptive_mode = adaptive_mode
        self.similarity_cache = {}
        
    def get_cached_similarity(self, color1, color2):
        """Get color similarity from cache or calculate and cache it."""
        try:
            # Convert arrays to tuples for cache key
            c1_tuple = tuple(map(int, color1[:3]))  # Only use RGB values
            c2_tuple = tuple(map(int, color2[:3]))
            
            # Order doesn't matter for similarity, so sort for consistent cache keys
            cache_key = (c1_tuple, c2_tuple) if c1_tuple <= c2_tuple else (c2_tuple, c1_tuple)
            
            if cache_key not in self.similarity_cache:
                self.similarity_cache[cache_key] = color_similarity(color1, color2)
            
            return self.similarity_cache[cache_key]
        except Exception as e:
            logger.error(f"Error in color similarity calculation: {e}")
            # Fallback: direct calculation without caching
            return color_similarity(color1, color2)
    
    def calculate_adaptive_threshold(self, x, y, radius=3):
        """
        Calculate an adaptive threshold based on local image characteristics.
        
        Args:
            x, y: Center pixel coordinates
            radius: Radius to consider for local analysis
            
        Returns:
            Adjusted similarity threshold
        """
        # Get the local region
        x_min, x_max = max(0, x - radius), min(self.width - 1, x + radius)
        y_min, y_max = max(0, y - radius), min(self.height - 1, y + radius)
        
        # Sample pixels in the local region
        local_colors = []
        for ly in range(y_min, y_max + 1):
            for lx in range(x_min, x_max + 1):
                local_colors.append(self.image[ly, lx])
        
        # Calculate local variance
        local_colors = np.array(local_colors)
        variance = np.var(local_colors, axis=0).mean() / 255.0
        
        # Adjust threshold based on local variance
        # Higher variance (more texture/detail) -> stricter threshold
        # Lower variance (flat areas) -> more relaxed threshold
        variance_factor = min(1.0, variance * 2.0)
        adjusted_threshold = self.base_threshold + (1.0 - self.base_threshold) * (1.0 - variance_factor) * 0.3
        
        return adjusted_threshold
    
    def expand_region(self, seed_x, seed_y, processed_mask=None):
        """
        Grow a region starting from the seed point using advanced region growing.
        
        Args:
            seed_x, seed_y: Seed pixel coordinates
            processed_mask: Boolean array marking already processed pixels
            
        Returns:
            List of (x, y) coordinates in the region
        """
        try:
            # Get the seed pixel color
            seed_color = self.image[seed_y, seed_x]
            
            # Initialize region and priority queue
            region = set([(seed_x, seed_y)])
            region_list = [(seed_x, seed_y)]
            
            # Priority queue for region growing
            # We'll use higher priority for better matches (unlike traditional A*)
            priority_queue = []
            
            # Add neighbors of the seed to the priority queue
            for nx, ny in self._get_neighbors(seed_x, seed_y):
                if processed_mask is None or not processed_mask[ny, nx]:
                    neighbor_color = self.image[ny, nx]
                    similarity = self.get_cached_similarity(seed_color, neighbor_color)
                    # Higher similarity = higher priority
                    priority_queue.append((1.0 - similarity, nx, ny, similarity))
            
            # Sort by priority (lower value = higher priority)
            priority_queue.sort()
            
            # Calculate base adaptive threshold at seed point
            base_adaptive_threshold = self.calculate_adaptive_threshold(seed_x, seed_y) if self.adaptive_mode else self.base_threshold
            
            # Main region growing loop
            while priority_queue and len(region) < self.max_region_size:
                # Get highest priority pixel
                _, current_x, current_y, parent_similarity = priority_queue.pop(0)
                
                # Skip if already in region or processed
                if (current_x, current_y) in region or (processed_mask is not None and processed_mask[current_y, current_x]):
                    continue
                
                # Get current pixel color
                current_color = self.image[current_y, current_x]
                
                # Calculate similarity to seed color
                similarity_to_seed = self.get_cached_similarity(seed_color, current_color)
                
                # Calculate adaptive threshold for this pixel
                if self.adaptive_mode:
                    # Scale threshold based on distance from seed and local characteristics
                    local_threshold = self.calculate_adaptive_threshold(current_x, current_y)
                    # Blend with base threshold, favoring stricter values as we get further from seed
                    adaptive_threshold = min(base_adaptive_threshold, local_threshold)
                else:
                    adaptive_threshold = self.base_threshold
                
                # Add to region if similarity is good enough
                if similarity_to_seed >= adaptive_threshold:
                    region.add((current_x, current_y))
                    region_list.append((current_x, current_y))
                    
                    # Add neighbors to priority queue
                    for nx, ny in self._get_neighbors(current_x, current_y):
                        if (nx, ny) not in region and (processed_mask is None or not processed_mask[ny, nx]):
                            neighbor_color = self.image[ny, nx]
                            # Check similarity to both seed and current pixel
                            similarity_to_seed = self.get_cached_similarity(seed_color, neighbor_color)
                            similarity_to_current = self.get_cached_similarity(current_color, neighbor_color)
                            
                            # Use the better of the two similarities
                            best_similarity = max(similarity_to_seed, similarity_to_current)
                            
                            # Only add to queue if it passes a minimum threshold
                            if best_similarity >= adaptive_threshold * 0.8:
                                # Priority is inverse of similarity (lower value = higher priority)
                                priority_queue.append((1.0 - best_similarity, nx, ny, best_similarity))
                    
                    # Keep the queue sorted by priority
                    priority_queue.sort()
            
            return region_list
            
        except Exception as e:
            logger.error(f"Error in expand_region: {e}")
            return []
    
    def _get_neighbors(self, x, y, connectivity=8):
        """
        Get neighboring pixels.
        
        Args:
            x, y: Pixel coordinates
            connectivity: 4 for cardinal directions only, 8 for diagonals too
            
        Returns:
            Generator yielding valid neighbor coordinates
        """
        if connectivity == 4:
            offsets = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # N, S, W, E
        else:  # connectivity == 8
            offsets = [(0, -1), (0, 1), (-1, 0), (1, 0),  # N, S, W, E
                      (-1, -1), (-1, 1), (1, -1), (1, 1)]  # NW, SW, NE, SE
            
        for dx, dy in offsets:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                yield (nx, ny)

class MeanShiftSegmenter:
    """
    Mean-shift based segmentation algorithm that identifies regions
    by clustering pixels in color space.
    """
    
    def __init__(self, image_array, color_bandwidth=0.1, spatial_bandwidth=0.05, 
                 max_region_size=None):
        """
        Initialize the segmenter.
        
        Args:
            image_array: NumPy array representing the image
            color_bandwidth: Bandwidth for color similarity (0.0-1.0)
            spatial_bandwidth: Bandwidth for spatial proximity (0.0-1.0)
            max_region_size: Maximum number of pixels in a region
        """
        self.image = image_array
        self.height, self.width = image_array.shape[:2]
        self.color_bandwidth = color_bandwidth 
        self.spatial_bandwidth = spatial_bandwidth
        self.max_region_size = max_region_size or min(20000, (self.width * self.height) // 10)
        self.spatial_scale = max(self.width, self.height)
        
    def find_region(self, seed_x, seed_y, processed_mask=None):
        """
        Find a region using mean-shift segmentation starting from a seed point.
        
        Args:
            seed_x, seed_y: Seed pixel coordinates
            processed_mask: Boolean array marking already processed pixels
            
        Returns:
            List of (x, y) coordinates in the region
        """
        try:
            # Get the seed pixel color
            seed_color = self.image[seed_y, seed_x].astype(np.float32) / 255.0
            
            # Initialize region
            region = set([(seed_x, seed_y)])
            region_list = [(seed_x, seed_y)]
            
            # Queue for breadth-first expansion
            queue = deque([(seed_x, seed_y)])
            
            # Mean color of the region (starts with seed color)
            mean_color = seed_color.copy()
            num_pixels = 1
            
            # Process queue
            while queue and len(region) < self.max_region_size:
                current_x, current_y = queue.popleft()
                
                # Check neighbors
                for nx, ny in self._get_neighbors(current_x, current_y):
                    # Skip if already in region or processed
                    if (nx, ny) in region or (processed_mask is not None and processed_mask[ny, nx]):
                        continue
                    
                    # Get normalized color
                    pixel_color = self.image[ny, nx].astype(np.float32) / 255.0
                    
                    # Calculate color distance
                    color_dist = np.sqrt(np.sum((pixel_color - mean_color) ** 2))
                    
                    # Calculate spatial distance (normalized by image size)
                    dx, dy = (nx - seed_x) / self.spatial_scale, (ny - seed_y) / self.spatial_scale
                    spatial_dist = np.sqrt(dx*dx + dy*dy)
                    
                    # Combine distances with weighting
                    combined_dist = (color_dist / self.color_bandwidth + 
                                   spatial_dist / self.spatial_bandwidth)
                    
                    # Add to region if within threshold
                    if combined_dist < 1.0:
                        region.add((nx, ny))
                        region_list.append((nx, ny))
                        queue.append((nx, ny))
                        
                        # Update mean color (incremental average)
                        mean_color = (mean_color * num_pixels + pixel_color) / (num_pixels + 1)
                        num_pixels += 1
            
            return region_list
            
        except Exception as e:
            logger.error(f"Error in mean-shift region finding: {e}")
            return []
    
    def _get_neighbors(self, x, y):
        """Get 8-connected neighbors."""
        offsets = [(0, -1), (0, 1), (-1, 0), (1, 0),  # N, S, W, E
                  (-1, -1), (-1, 1), (1, -1), (1, 1)]  # NW, SW, NE, SE
            
        for dx, dy in offsets:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                yield (nx, ny)

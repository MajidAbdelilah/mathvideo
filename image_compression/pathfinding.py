import numpy as np
from utils import color_similarity
from collections import deque
import threading
import logging

logger = logging.getLogger('pathfinding')

class RegionPathfinder:
    """
    An optimized algorithm that finds regions of similar color in an image.
    Uses a modified breadth-first flood fill that's more efficient than A* for this task.
    """
    
    # Thread lock for any shared operations
    _lock = threading.Lock()
    
    def __init__(self, image_array, similarity_threshold=0.9, max_region_size=None):
        """
        Initialize the pathfinder.
        
        Args:
            image_array: NumPy array representing the image
            similarity_threshold: Value between 0.0 and 1.0, higher values = more strict matching
            max_region_size: Maximum number of pixels in a region (None for unlimited)
        """
        self.image = image_array
        self.height, self.width = image_array.shape[:2]
        self.similarity_threshold = similarity_threshold
        # Set a reasonable default max region size to prevent excessive growth
        self.max_region_size = max_region_size or min(10000, (self.width * self.height) // 20)
        # Cache for color similarities to avoid recalculations
        self.similarity_cache = {}
        
    def get_neighbors(self, x, y):
        """Get 4-directional neighbors (left, right, up, down)."""
        # Pre-compute offsets for performance
        offsets = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # up, down, left, right
        for dx, dy in offsets:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                yield (nx, ny)
    
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
    
    def find_region(self, start_x, start_y, processed=None):
        """
        Find a region of similar colors using optimized breadth-first flood fill.
        
        Args:
            start_x, start_y: Starting pixel coordinates
            processed: Array marking pixels that are already processed
        
        Returns:
            A list of (x, y) tuples representing pixels in the region.
        """
        try:
            # Get the color of the starting pixel
            start_color = self.image[start_y, start_x]
            
            # Queue for flood fill (much faster than A* priority queue for this purpose)
            queue = deque([(start_x, start_y)])
            
            # Set for tracking which pixels are in the region
            region = set()
            region.add((start_x, start_y))
            
            # Track the region as a list too (for return value)
            region_list = [(start_x, start_y)]
            
            while queue and len(region) < self.max_region_size:
                current_x, current_y = queue.popleft()
                
                # Process each neighbor
                for nx, ny in self.get_neighbors(current_x, current_y):
                    # Skip if already in region or globally processed
                    if (nx, ny) in region or (processed is not None and processed[ny, nx]):
                        continue
                    
                    # Get color similarity with starting pixel
                    neighbor_color = self.image[ny, nx]
                    similarity = self.get_cached_similarity(start_color, neighbor_color)
                    
                    # Add to region if similar enough
                    if similarity >= self.similarity_threshold:
                        region.add((nx, ny))
                        region_list.append((nx, ny))
                        queue.append((nx, ny))
            
            return region_list
        except Exception as e:
            logger.error(f"Error in find_region: {e}")
            return []

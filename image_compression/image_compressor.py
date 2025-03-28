from PIL import Image
import numpy as np
import os
from region_algorithms import AdaptiveRegionGrower, MeanShiftSegmenter
import time
import logging
import sys
from datetime import datetime

# Set up basic logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('image_compressor')

class CompressionStats:
    """Tracks and reports statistics about the compression process."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.total_pixels = 0
        self.processed_pixels = 0
        self.total_regions = 0
        self.largest_region = 0
        self.smallest_region = float('inf')
        self.avg_region_size = 0
        self.region_sizes = []
        self.bytes_original = 0
        self.bytes_compressed = 0  # Will be estimated
        
    def start(self, width, height):
        """Start tracking compression with the given image dimensions."""
        self.start_time = time.time()
        self.total_pixels = width * height
        self.bytes_original = width * height * 3  # Estimate: 3 bytes per pixel (RGB)
        
    def finish(self):
        """Mark the compression as finished and calculate final stats."""
        self.end_time = time.time()
        if self.region_sizes:
            self.largest_region = max(self.region_sizes)
            self.smallest_region = min(self.region_sizes)
            self.avg_region_size = sum(self.region_sizes) / len(self.region_sizes)
        
        # Fix: region_sizes contains integers (not regions), so don't call len() on them
        # Estimate compressed size: 3 bytes for color + 4 bytes per pixel coordinate pair
        self.bytes_compressed = self.total_regions * 3 + 4 * sum(self.region_sizes)
        
    def add_region(self, region):
        """Record a new region found during compression."""
        region_size = len(region)
        self.region_sizes.append(region_size)
        self.processed_pixels += region_size
        self.total_regions += 1
        
    def get_elapsed_time(self):
        """Get the elapsed time of the compression."""
        if self.start_time is None:
            return 0
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time
        
    def get_progress(self):
        """Get the current progress as a value between 0.0 and 1.0."""
        if self.total_pixels == 0:
            return 0.0
        return min(1.0, self.processed_pixels / self.total_pixels)
    
    def get_processing_rate(self):
        """Get the current processing rate in pixels per second."""
        elapsed = self.get_elapsed_time()
        if elapsed <= 0:
            return 0
        return self.processed_pixels / elapsed
    
    def get_summary(self, detailed=False):
        """
        Get a summary of the compression statistics.
        
        Args:
            detailed: Whether to include detailed statistics
            
        Returns:
            Dictionary with statistics
        """
        elapsed = self.get_elapsed_time()
        progress = self.get_progress()
        compression_ratio = self.total_pixels / max(1, self.total_regions)
        estimated_remaining = 0 if progress >= 1.0 else (elapsed / max(0.001, progress)) - elapsed
        
        summary = {
            "progress": progress,
            "elapsed_time": elapsed,
            "estimated_remaining": estimated_remaining,
            "processing_rate": self.get_processing_rate(),
            "compression_ratio": compression_ratio,
            "total_pixels": self.total_pixels,
            "processed_pixels": self.processed_pixels,
            "total_regions": self.total_regions
        }
        
        if detailed:
            summary.update({
                "largest_region": self.largest_region,
                "smallest_region": self.smallest_region,
                "avg_region_size": self.avg_region_size,
                "bytes_original": self.bytes_original,
                "bytes_compressed": self.bytes_compressed,
                "byte_ratio": self.bytes_original / max(1, self.bytes_compressed)
            })
            
        return summary
    
    def print_report(self):
        """Print a formatted report of compression statistics to console."""
        summary = self.get_summary(detailed=True)
        
        # Format elapsed time
        elapsed = summary["elapsed_time"]
        if elapsed < 60:
            elapsed_str = f"{elapsed:.2f} seconds"
        elif elapsed < 3600:
            minutes = int(elapsed // 60)
            seconds = elapsed % 60
            elapsed_str = f"{minutes} minutes, {seconds:.2f} seconds"
        else:
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = elapsed % 60
            elapsed_str = f"{hours} hours, {minutes} minutes, {seconds:.2f} seconds"
            
        # Format sizes
        def format_bytes(bytes):
            if bytes < 1024:
                return f"{bytes} bytes"
            elif bytes < 1024 * 1024:
                return f"{bytes/1024:.2f} KB"
            else:
                return f"{bytes/(1024*1024):.2f} MB"
        
        print("\n" + "="*60)
        print(" "*20 + "COMPRESSION REPORT")
        print("="*60)
        print(f"Total time:          {elapsed_str}")
        print(f"Processing rate:     {summary['processing_rate']:.0f} pixels/second")
        print(f"Image dimensions:    {int(np.sqrt(summary['total_pixels'])):.0f}x{int(np.sqrt(summary['total_pixels'])):.0f} (approx) = {summary['total_pixels']} pixels")
        print(f"Regions identified:  {summary['total_regions']}")
        print(f"Compression ratio:   {summary['compression_ratio']:.2f}:1")
        print(f"Data size ratio:     {summary['byte_ratio']:.2f}:1")
        print("-"*60)
        print(f"Original size:       {format_bytes(summary['bytes_original'])}")
        print(f"Compressed size:     {format_bytes(summary['bytes_compressed'])}")
        print(f"Space saved:         {format_bytes(summary['bytes_original'] - summary['bytes_compressed'])} ({(1-1/summary['byte_ratio'])*100:.1f}%)")
        print("-"*60)
        print(f"Largest region:      {summary['largest_region']} pixels")
        print(f"Smallest region:     {summary['smallest_region']} pixels")
        print(f"Average region size: {summary['avg_region_size']:.2f} pixels")
        print("="*60)
        
        # Also log the report
        logger.info(f"Compression complete: {summary['compression_ratio']:.2f}:1 ratio, {summary['total_regions']} regions, {elapsed_str}")

class ImageCompressor:
    def __init__(self, similarity_threshold=0.9, max_region_size=None, 
                 progress_callback=None, algorithm='adaptive', adaptive_mode=True):
        """
        Initialize the image compressor.
        
        Args:
            similarity_threshold (float): Value between 0.0 and 1.0 for color similarity
            max_region_size (int): Maximum pixels in a region
            progress_callback (callable): Function to call with progress updates
            algorithm (str): Region-finding algorithm: 'adaptive', 'meanshift'
            adaptive_mode (bool): Whether to use adaptive thresholding
        """
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError("Similarity threshold must be between 0.0 and 1.0")
        
        self.similarity_threshold = similarity_threshold
        self.max_region_size = max_region_size
        self.progress_callback = progress_callback
        self.algorithm = algorithm.lower()
        self.adaptive_mode = adaptive_mode
        self.regions = []
        self.region_colors = []
        
        # Initialize compression statistics
        self.stats = CompressionStats()
        
        # Progress update frequency control
        self.progress_update_interval = 0.5  # seconds
        self.last_progress_update = 0
        
        logger.info(f"Initialized compressor with {self.algorithm} algorithm")
    
    def load_image(self, image_path):
        """Load an image from file path."""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        self.image = Image.open(image_path)
        self.pixels = np.array(self.image)
        self.height, self.width = self.pixels.shape[:2]
        logger.info(f"Loaded image: {image_path}, size: {self.width}x{self.height}")
        return self.pixels
    
    def compress(self, image_path=None):
        """Compress the image by finding regions of similar colors."""
        if image_path is not None:
            self.load_image(image_path)
        
        if not hasattr(self, 'pixels'):
            raise ValueError("No image loaded. Call load_image() first.")
        
        # Reset regions and stats
        self.regions = []
        self.region_colors = []
        self.stats = CompressionStats()
        self.stats.start(self.width, self.height)
        
        # Create a mask to track which pixels have been processed
        processed = np.zeros((self.height, self.width), dtype=bool)
        
        # Initialize the appropriate region finder
        if self.algorithm == 'meanshift':
            region_finder = MeanShiftSegmenter(
                self.pixels,
                color_bandwidth=1.0 - self.similarity_threshold,
                max_region_size=self.max_region_size
            )
        else:  # default to adaptive
            region_finder = AdaptiveRegionGrower(
                self.pixels,
                similarity_threshold=self.similarity_threshold,
                max_region_size=self.max_region_size,
                adaptive_mode=self.adaptive_mode
            )
        
        logger.info(f"Starting compression with {self.algorithm} algorithm")
        self._update_progress()
        
        # Process the image pixel by pixel
        for y in range(self.height):
            for x in range(self.width):
                # Skip if this pixel is already processed
                if processed[y, x]:
                    continue
                
                # Find a region using the selected algorithm
                if self.algorithm == 'meanshift':
                    region = region_finder.find_region(x, y, processed)
                else:  # adaptive
                    region = region_finder.expand_region(x, y, processed)
                
                # Skip if region is empty
                if not region:
                    continue
                
                # Calculate average color for the region
                region_pixels = [self.pixels[p[1], p[0]] for p in region]
                avg_color = np.mean(region_pixels, axis=0, dtype=int)
                
                # Store the region and its color
                self.regions.append(region)
                self.region_colors.append(tuple(avg_color))
                
                # Update statistics
                self.stats.add_region(region)
                
                # Mark all pixels in this region as processed
                for px, py in region:
                    if 0 <= py < self.height and 0 <= px < self.width:
                        processed[py, px] = True
                
                # Periodically update progress
                now = time.time()
                if now - self.last_progress_update >= self.progress_update_interval:
                    self._update_progress()
                    self.last_progress_update = now
        
        # Finalize statistics and ensure progress shows 100%
        self.stats.finish()
        self._update_progress(force=True)
        
        # Print the final report
        self.stats.print_report()
        
        return self.regions, self.region_colors
    
    def _update_progress(self, force=False):
        """Update the progress display."""
        if not self.progress_callback and not force:
            return
            
        # Get current stats
        summary = self.stats.get_summary()
        progress = summary["progress"]
        
        # Update the console title
        sys.stdout.write(f"\033]0;Compressing: {progress*100:.1f}% complete\007")
        
        # Call the progress callback if provided
        if self.progress_callback:
            try:
                # Send both the simple progress value and detailed stats
                self.progress_callback(progress, summary)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
                
        # Log progress periodically
        if force or (self.stats.total_regions > 0 and self.stats.total_regions % 100 == 0):
            elapsed = summary["elapsed_time"]
            rate = summary["processing_rate"]
            pixels = summary["processed_pixels"]
            regions = summary["total_regions"]
            logger.info(f"Progress: {progress*100:.1f}% - {pixels}/{self.stats.total_pixels} pixels, "
                       f"{regions} regions, {rate:.0f} px/sec, {elapsed:.1f} sec elapsed")
    
    def save_compressed_image(self, output_path):
        """Save the compressed image to a file."""
        if not self.regions:
            raise ValueError("No compression data available. Call compress() first.")
        
        logger.info(f"Saving compressed image to {output_path}")
        
        # Create a new image with the same dimensions
        result = np.zeros_like(self.pixels)
        
        # Fill each region with its average color
        for region, color in zip(self.regions, self.region_colors):
            for x, y in region:
                if 0 <= y < self.height and 0 <= x < self.width:
                    result[y, x] = color
        
        # Save the image
        output_image = Image.fromarray(result.astype(np.uint8))
        output_image.save(output_path)
        logger.info(f"Compressed image saved successfully to {output_path}")
        
        # Collect additional metadata about the saved file
        file_size = os.path.getsize(output_path)
        print(f"File size: {file_size / 1024:.2f} KB")
        
        # Create a timestamp for the output file
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create a metadata report about the compression
        metadata_path = f"{os.path.splitext(output_path)[0]}_info.txt"
        with open(metadata_path, 'w') as f:
            f.write(f"Image Compression Report\n")
            f.write(f"======================\n\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Algorithm: {self.algorithm}\n")
            f.write(f"Similarity threshold: {self.similarity_threshold}\n")
            f.write(f"Adaptive mode: {self.adaptive_mode}\n\n")
            
            f.write(f"Original dimensions: {self.width}x{self.height} = {self.width*self.height} pixels\n")
            f.write(f"Regions identified: {len(self.regions)}\n")
            f.write(f"Compression ratio: {(self.width*self.height)/len(self.regions):.2f}:1\n\n")
            
            f.write(f"Processing time: {self.stats.get_elapsed_time():.2f} seconds\n")
            f.write(f"Processing rate: {self.stats.get_processing_rate():.0f} pixels/second\n\n")
            
            f.write(f"Output file size: {file_size / 1024:.2f} KB\n")
        
        logger.info(f"Compression metadata saved to {metadata_path}")
        
        return output_path

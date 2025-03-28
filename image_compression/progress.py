import sys
import time
import threading
import logging
from datetime import timedelta

logger = logging.getLogger('progress')

class ProgressBar:
    """A console-based progress bar for displaying task progress."""
    
    def __init__(self, total_width=50, description="Progress"):
        """
        Initialize the progress bar.
        
        Args:
            total_width (int): Width of the progress bar in characters
            description (str): Text to display before the progress bar
        """
        self.total_width = total_width
        self.description = description
        self.start_time = None
        self.last_update_time = 0
        self.current_progress = 0
        self._lock = threading.Lock()
    
    def start(self):
        """Start the progress tracking."""
        self.start_time = time.time()
        self.update(0)
    
    def update(self, progress, stats=None):
        """
        Update the progress bar display.
        
        Args:
            progress (float): Current progress value between 0.0 and 1.0
            stats (dict): Optional dictionary of additional statistics to display
        """
        with self._lock:
            try:
                # Only update the display if enough time has passed (avoid flickering)
                current_time = time.time()
                min_update_interval = 0.2  # seconds
                
                if (current_time - self.last_update_time < min_update_interval) and (progress < 1.0):
                    return
                
                self.last_update_time = current_time
                self.current_progress = progress
                
                # Calculate elapsed time and ETA
                elapsed = current_time - self.start_time
                eta = 0 if progress <= 0.001 else elapsed / progress - elapsed
                
                # Build the progress bar
                filled_width = int(self.total_width * progress)
                bar = '█' * filled_width + '░' * (self.total_width - filled_width)
                
                # Format percentage and timing information
                percent = progress * 100
                elapsed_str = self._format_time(elapsed)
                eta_str = self._format_time(eta) if progress < 1.0 else "Complete"
                
                # Base progress bar
                progress_line = f"\r{self.description}: [{bar}] {percent:6.2f}% | {elapsed_str} elapsed | ETA: {eta_str}"
                
                # Add additional statistics if provided
                if stats and isinstance(stats, dict):
                    # Include processing rate and regions if available
                    if 'processing_rate' in stats:
                        progress_line += f" | {stats['processing_rate']:.0f} px/sec"
                    if 'total_regions' in stats:
                        progress_line += f" | {stats['total_regions']} regions"
                
                # Print the progress bar
                sys.stdout.write(progress_line)
                sys.stdout.flush()
                
                # Print a newline when complete
                if progress >= 1.0:
                    sys.stdout.write("\n")
                    sys.stdout.flush()
            except Exception as e:
                logger.error(f"Error updating progress bar: {e}")
    
    def _format_time(self, seconds):
        """Format a time in seconds to a human-readable string."""
        if seconds < 0:
            return "Unknown"
        
        # Using timedelta for cleaner formatting
        td = timedelta(seconds=seconds)
        
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if td.days > 0:
            return f"{td.days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds:.1f}s"

class ProgressCallback:
    """Progress callback handler that manages progress reporting."""
    
    def __init__(self, description="Processing", console=True, total_width=50, callback=None):
        """
        Initialize the progress handler.
        
        Args:
            description (str): Description to show for the progress
            console (bool): Whether to show a console progress bar
            total_width (int): Width of the console progress bar
            callback (callable): Optional external callback function to also receive progress updates
        """
        self.description = description
        self.console = console
        self.callback = callback
        
        if console:
            self.progress_bar = ProgressBar(total_width=total_width, description=description)
            self.progress_bar.start()
    
    def __call__(self, progress, stats=None):
        """
        Handle a progress update.
        
        Args:
            progress (float): Current progress value between 0.0 and 1.0
            stats (dict): Optional dictionary of additional statistics
        """
        try:
            # Update the console progress bar
            if self.console:
                self.progress_bar.update(progress, stats)
            
            # Call the external callback if provided
            if self.callback:
                self.callback(progress, stats)
        except Exception as e:
            logger.error(f"Error in progress callback: {e}")

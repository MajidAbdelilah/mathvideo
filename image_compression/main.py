import argparse
import os
import sys
import logging
from image_compressor import ImageCompressor
from progress import ProgressCallback

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

def main():
    parser = argparse.ArgumentParser(description='Compress images using advanced region finding to identify areas of similar colors.')
    parser.add_argument('input_image', help='Path to the input image file')
    parser.add_argument('-o', '--output', help='Path to save the compressed image (default: adds "_compressed" to the input filename)')
    parser.add_argument('-t', '--threshold', type=float, default=0.9, 
                        help='Similarity threshold (0.0-1.0). Higher values = stricter matching, less compression (default: 0.9)')
    parser.add_argument('-m', '--max-region-size', type=int, default=None,
                        help='Maximum number of pixels in a region (default: calculated based on image size)')
    parser.add_argument('-a', '--algorithm', choices=['adaptive', 'meanshift'], default='adaptive',
                        help='Region-finding algorithm to use (default: adaptive)')
    parser.add_argument('--no-adaptive', action='store_true',
                        help='Disable adaptive thresholding (for adaptive algorithm)')
    parser.add_argument('--no-progress', action='store_true',
                        help='Disable progress bar display')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--report-only', action='store_true',
                        help='Only generate a report without saving the image')
    
    args = parser.parse_args()
    
    # Set logging level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input file
    if not os.path.exists(args.input_image):
        print(f"Error: Input file '{args.input_image}' not found")
        return 1
    
    logger.info(f"Starting compression of {args.input_image} using {args.algorithm} algorithm")
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        filename, ext = os.path.splitext(args.input_image)
        output_path = f"{filename}_compressed_{args.algorithm}{ext}"
    
    # Create progress callback if not disabled
    progress = None
    if not args.no_progress:
        try:
            progress = ProgressCallback(description=f"Compressing image ({args.algorithm})")
        except Exception as e:
            logger.error(f"Failed to initialize progress bar: {e}")
            logger.info("Continuing without progress bar")
    
    # Create and run the compressor
    try:
        print(f"Loading image: {args.input_image}")
        
        # Create the compressor with proper parameters
        compressor = ImageCompressor(
            similarity_threshold=args.threshold, 
            max_region_size=args.max_region_size,
            progress_callback=progress,
            algorithm=args.algorithm,
            adaptive_mode=not args.no_adaptive
        )
        
        # Load the image
        compressor.load_image(args.input_image)
        
        # Compress the image
        compressor.compress()
        
        # Save the compressed image unless report-only mode is specified
        if not args.report_only:
            print(f"Saving compressed image to: {output_path}")
            compressor.save_compressed_image(output_path)
            print(f"Success! Compressed image saved to '{output_path}'")
        else:
            print("Report-only mode: Image was not saved")
            
        return 0
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        logger.exception("Error during compression")
        print(f"\nError during compression: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

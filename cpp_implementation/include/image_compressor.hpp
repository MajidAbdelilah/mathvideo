#pragma once

#include "utils/image_utils.hpp"
#include "algorithms/region_grower.hpp"
#include <vector>
#include <string>
#include <functional>
#include <chrono>
#include <memory>

namespace ic {

// Stats class to track compression statistics
class CompressionStats {
public:
    CompressionStats();
    
    void start(int width, int height);
    void finish();
    void addRegion(const std::vector<Point>& region);
    
    double getElapsedTime() const;
    double getProgress() const;
    double getProcessingRate() const;
    
    // Get a dictionary of stats for reporting
    std::unordered_map<std::string, double> getSummary(bool detailed = false) const;
    
    // Print a formatted report
    void printReport() const;
    
private:
    std::chrono::time_point<std::chrono::high_resolution_clock> startTime_;
    std::chrono::time_point<std::chrono::high_resolution_clock> endTime_;
    bool finished_ = false;
    
    int totalPixels_ = 0;
    int processedPixels_ = 0;
    int totalRegions_ = 0;
    int largestRegion_ = 0;
    int smallestRegion_ = std::numeric_limits<int>::max();
    double avgRegionSize_ = 0.0;
    std::vector<int> regionSizes_;
    
    int64_t bytesOriginal_ = 0;
    int64_t bytesCompressed_ = 0;
    
    // Helper for formatting byte sizes
    std::string formatBytes(int64_t bytes) const;
    std::string formatTime(double seconds) const;
};

// Callback type for progress updates
using ProgressCallback = std::function<void(double progress, const std::unordered_map<std::string, double>& stats)>;

// Main compressor class
class ImageCompressor {
public:
    enum class Algorithm {
        ADAPTIVE,
        MEAN_SHIFT
    };
    
    ImageCompressor(double similarityThreshold = 0.9, 
                   int maxRegionSize = 0,
                   ProgressCallback progressCallback = nullptr,
                   Algorithm algorithm = Algorithm::ADAPTIVE,
                   bool adaptiveMode = true);
    
    // Load an image from file
    bool loadImage(const std::string& imagePath);
    
    // Compress the loaded image
    bool compress();
    
    // Save the compressed image
    bool saveCompressedImage(const std::string& outputPath);
    
private:
    double similarityThreshold_;
    int maxRegionSize_;
    ProgressCallback progressCallback_;
    Algorithm algorithm_;
    bool adaptiveMode_;
    
    // Image data
    std::shared_ptr<Image> image_ = nullptr;
    int width_ = 0;
    int height_ = 0;
    
    // Compression results
    std::vector<std::vector<Point>> regions_;
    std::vector<Color> regionColors_;
    
    // Statistics
    CompressionStats stats_;
    
    // Last progress update time
    std::chrono::time_point<std::chrono::high_resolution_clock> lastProgressUpdate_;
    double progressUpdateInterval_ = 0.5; // seconds
    
    // Update progress display
    void updateProgress(bool force = false);
};

} // namespace ic

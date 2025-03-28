#pragma once

#include "utils/image_utils.hpp"
#include <vector>
#include <unordered_set>
#include <unordered_map>
#include <memory>
#include <string>

namespace ic {

// Base class for region growing algorithms
class RegionGrower {
public:
    RegionGrower(const Image& image, double similarityThreshold, int maxRegionSize = 0);
    virtual ~RegionGrower() = default;
    
    // Find a region starting from a seed point
    virtual std::vector<Point> findRegion(int seedX, int seedY, 
                                         const std::vector<std::vector<bool>>& processed) = 0;
                                         
protected:
    const Image& image_;
    double similarityThreshold_;
    int maxRegionSize_;
    int width_;
    int height_;
    
    // Helper method to get neighboring pixels
    std::vector<Point> getNeighbors(int x, int y, bool include8Connected = false) const;
    
    // Check if coordinates are valid
    bool isValidCoordinate(int x, int y) const {
        return x >= 0 && x < width_ && y >= 0 && y < height_;
    }
};

// Adaptive region growing algorithm
class AdaptiveRegionGrower : public RegionGrower {
public:
    AdaptiveRegionGrower(const Image& image, double similarityThreshold, 
                        int maxRegionSize = 0, bool adaptiveMode = true);
    
    std::vector<Point> findRegion(int seedX, int seedY, 
                                 const std::vector<std::vector<bool>>& processed) override;
    
private:
    bool adaptiveMode_;
    // Use string keys for the cache (much simpler)std::unordered_map<std::pair<Color, Color>, double, ColorPairHash> similarityCache_;
    std::unordered_map<std::string, double> similarityCache_;
    
    // Calculate adaptive threshold based on local image characteristicsdouble calculateAdaptiveThreshold(int x, int y, int radius = 3) const;
    double calculateAdaptiveThreshold(int x, int y, int radius = 3) const;
    
    // Get cached similarity value  double getCachedSimilarity(const Color& c1, const Color& c2);
    double getCachedSimilarity(const Color& c1, const Color& c2);};
};

// Mean-shift based segmentationeanShiftSegmenter : public RegionGrower {
class MeanShiftSegmenter : public RegionGrower {
public:
    MeanShiftSegmenter(const Image& image, double colorBandwidth,                   double spatialBandwidth, int maxRegionSize = 0);
                      double spatialBandwidth, int maxRegionSize = 0);
    
    std::vector<Point> findRegion(int seedX, int seedY,                              const std::vector<std::vector<bool>>& processed) override;
                                 const std::vector<std::vector<bool>>& processed) override;
    
private:
    double colorBandwidth_;width_;
    double spatialBandwidth_;  int spatialScale_;
    int spatialScale_;};
};
} // namespace ic


} // namespace ic
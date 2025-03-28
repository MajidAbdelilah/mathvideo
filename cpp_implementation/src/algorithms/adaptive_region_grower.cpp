#include "algorithms/region_grower.hpp"
#include <queue>
#include <algorithm>
#include <unordered_set>
#include <unordered_map>
#include <functional>
#include <string>

namespace ic {

AdaptiveRegionGrower::AdaptiveRegionGrower(const Image& image, double similarityThreshold, 
                                         int maxRegionSize, bool adaptiveMode)
    : RegionGrower(image, similarityThreshold, maxRegionSize), adaptiveMode_(adaptiveMode) {   // Initialize with a reasonable size to avoid too many rehashes
    // Initialize with a reasonable size to avoid too many rehashes    similarityCache_.reserve(1000);
    similarityCache_.reserve(1000);
}
n local image characteristics
// Calculate adaptive threshold based on local image characteristicsreshold(int x, int y, int radius) const {
double AdaptiveRegionGrower::calculateAdaptiveThreshold(int x, int y, int radius) const {
    int xMin = std::max(0, x - radius);
    int xMax = std::min(width_ - 1, x + radius);int yMin = std::max(0, y - radius);
    int yMin = std::max(0, y - radius); radius);
    int yMax = std::min(height_ - 1, y + radius);
    
    // Sample pixels in the local region
    std::vector<Color> localColors;
    for (int ly = yMin; ly <= yMax; ++ly) {or (int lx = xMin; lx <= xMax; ++lx) {
        for (int lx = xMin; lx <= xMax; ++lx) {       localColors.push_back(image_.getPixel(lx, ly));
            localColors.push_back(image_.getPixel(lx, ly));    }
        }
    }
    
    // Calculate average colorotalG = 0, totalB = 0;
    uint32_t totalR = 0, totalG = 0, totalB = 0; : localColors) {
    for (const auto& color : localColors) {
        totalR += color.r;   totalG += color.g;
        totalG += color.g;
        totalB += color.b;
    }int count = static_cast<int>(localColors.size());
    int count = static_cast<int>(localColors.size()); / count, totalG / count, totalB / count);
    Color avgColor(totalR / count, totalG / count, totalB / count);
    
    // Calculate variance
    double variance = 0.0;
    for (const auto& color : localColors) {
        double dr = static_cast<double>(color.r) - avgColor.r;r.g) - avgColor.g;
        double dg = static_cast<double>(color.g) - avgColor.g;   double db = static_cast<double>(color.b) - avgColor.b;
        double db = static_cast<double>(color.b) - avgColor.b;
        variance += (dr*dr + dg*dg + db*db);}
    }// Normalize
    variance /= (count * 3.0 * 255.0 * 255.0); // Normalize
    
    // Adjust threshold based on local variancehreshold
    // Higher variance (more texture/detail) -> stricter threshold
    // Lower variance (flat areas) -> more relaxed thresholddouble varianceFactor = std::min(1.0, variance * 2.0);
    double varianceFactor = std::min(1.0, variance * 2.0);= similarityThreshold_ + (1.0 - similarityThreshold_) * (1.0 - varianceFactor) * 0.3;
    double adjustedThreshold = similarityThreshold_ + (1.0 - similarityThreshold_) * (1.0 - varianceFactor) * 0.3;   
        return adjustedThreshold;
    return adjustedThreshold;
}

// Get cached similarity valueCachedSimilarity(const Color& c1, const Color& c2) {
double AdaptiveRegionGrower::getCachedSimilarity(const Color& c1, const Color& c2) {
    // Create a string key for the cache (make sure color order doesn't matter)lor> key;
    Color first = c1, second = c2; < c2.r || (c1.r == c2.r && (c1.g < c2.g || (c1.g == c2.g && c1.b < c2.b)))) {
    if (c2.r < c1.r || (c2.r == c1.r && (c2.g < c1.g || (c2.g == c1.g && c2.b < c1.b)))) {
        first = c2; else {
        second = c1;    key = {c2, c1};
    }
    
    // Create a string key
    std::string key = std::to_string(first.r) + "-" + che_.find(key);
                    std::to_string(first.g) + "-" + f (it != similarityCache_.end()) {
                    std::to_string(first.b) + "_" +    return it->second;
                    std::to_string(second.r) + "-" + 
                    std::to_string(second.g) + "-" + 
                    std::to_string(second.b);
    = colorSimilarity(c1, c2);
    // Check cache   similarityCache_[key] = similarity;
    auto it = similarityCache_.find(key);    return similarity;
    if (it != similarityCache_.end()) {
        return it->second;
    }onGrower::findRegion(int seedX, int seedY, 
    nst std::vector<std::vector<bool>>& processed) {
    // Calculate and cache// Get the seed pixel color
    double similarity = colorSimilarity(c1, c2);age_.getPixel(seedX, seedY);
    similarityCache_[key] = similarity;
    return similarity;
}std::unordered_set<Point, PointHash> region;
> regionList;
std::vector<Point> AdaptiveRegionGrower::findRegion(int seedX, int seedY, 
                                                  const std::vector<std::vector<bool>>& processed) {
    // Get the seed pixel color
    Color seedColor = image_.getPixel(seedX, seedY);region.insert(seedPoint);
    
    // Initialize region
    std::unordered_set<Point, PointHash> region; region growing
    std::vector<Point> regionList;arities
    tem {
    // Add seed point     // Lower value = higher priority
    Point seedPoint(seedX, seedY);Point point;
    region.insert(seedPoint);
    regionList.push_back(seedPoint);
    ool operator>(const PriorityItem& other) const {
    // Priority queue for region growing      return priority > other.priority;
    // We'll use a custom comparator to prioritize higher similarities    }
    struct PriorityItem {
        double priority;       // Lower value = higher priority
        Point point;rityItem>, std::greater<PriorityItem>> priorityQueue;
        double similarity;
        the priority queue
        bool operator>(const PriorityItem& other) const {dX, seedY, true)) {
            return priority > other.priority;ready processed
        }f (processed[neighbor.y][neighbor.x]) {
    };    continue;
    
    std::priority_queue<PriorityItem, std::vector<PriorityItem>, std::greater<PriorityItem>> priorityQueue;
    Color neighborColor = image_.getPixel(neighbor.x, neighbor.y);
    // Add neighbors of the seed to the priority queueeighborColor);
    for (const auto& neighbor : getNeighbors(seedX, seedY, true)) {
        // Skip if already processed   // Higher similarity = higher priority (lower value)
        if (processed[neighbor.y][neighbor.x]) {    priorityQueue.push({1.0 - similarity, neighbor, similarity});
            continue;
        }
        
        Color neighborColor = image_.getPixel(neighbor.x, neighbor.y);
        double similarity = getCachedSimilarity(seedColor, neighborColor);                             ? calculateAdaptiveThreshold(seedX, seedY) 
          : similarityThreshold_;
        // Higher similarity = higher priority (lower value)
        priorityQueue.push({1.0 - similarity, neighbor, similarity});
    }.size() < static_cast<size_t>(maxRegionSize_)) {
    ity pixel
    // Calculate base adaptive threshold at seed pointauto current = priorityQueue.top();
    double baseAdaptiveThreshold = adaptiveMode_ 
                                 ? calculateAdaptiveThreshold(seedX, seedY) 
                                 : similarityThreshold_;ready in region or processed
    f (region.count(current.point) > 0 || processed[current.point.y][current.point.x]) {
    // Main region growing loop    continue;
    while (!priorityQueue.empty() && region.size() < static_cast<size_t>(maxRegionSize_)) {
        // Get highest priority pixel
        auto current = priorityQueue.top();// Get current pixel color
        priorityQueue.pop();current.point.x, current.point.y);
        
        // Skip if already in region or processed// Calculate similarity to seed color
        if (region.count(current.point) > 0 || processed[current.point.y][current.point.x]) {seedColor, currentColor);
            continue;
        }e threshold for this pixel
        
        // Get current pixel color
        Color currentColor = image_.getPixel(current.point.x, current.point.y);al characteristics
        current.point.y);
        // Calculate similarity to seed colorlend with base threshold, favoring stricter values
        double similarityToSeed = getCachedSimilarity(seedColor, currentColor);Threshold, localThreshold);
         else {
        // Calculate adaptive threshold for this pixel    adaptiveThreshold = similarityThreshold_;
        double adaptiveThreshold;
        if (adaptiveMode_) {
            // Scale threshold based on distance from seed and local characteristics good enough
            double localThreshold = calculateAdaptiveThreshold(current.point.x, current.point.y);d) {
            // Blend with base threshold, favoring stricter valuesregion.insert(current.point);
            adaptiveThreshold = std::min(baseAdaptiveThreshold, localThreshold););
        } else {
            adaptiveThreshold = similarityThreshold_;
        } true)) {
        ready in region or processed
        // Add to region if similarity is good enoughf (region.count(neighbor) > 0 || processed[neighbor.y][neighbor.x]) {
        if (similarityToSeed >= adaptiveThreshold) {    continue;
            region.insert(current.point);
            regionList.push_back(current.point);
            neighbor.y);
            // Add neighbors to priority queue
            for (const auto& neighbor : getNeighbors(current.point.x, current.point.y, true)) {
                // Skip if already in region or processeddouble similarityToSeed = getCachedSimilarity(seedColor, neighborColor);
                if (region.count(neighbor) > 0 || processed[neighbor.y][neighbor.x]) {ilarity(currentColor, neighborColor);
                    continue;
                }// Use the better of the two similarities
                milarityToCurrent);
                Color neighborColor = image_.getPixel(neighbor.x, neighbor.y);
                
                // Check similarity to both seed and current pixel
                double similarityToSeed = getCachedSimilarity(seedColor, neighborColor);   // Priority is inverse of similarity (lower value = higher priority)
                double similarityToCurrent = getCachedSimilarity(currentColor, neighborColor);       priorityQueue.push({1.0 - bestSimilarity, neighbor, bestSimilarity});
                       }
                // Use the better of the two similarities       }
                double bestSimilarity = std::max(similarityToSeed, similarityToCurrent);    }
                
                // Only add to queue if it passes a minimum threshold   
                if (bestSimilarity >= adaptiveThreshold * 0.8) {    return regionList;
                    // Priority is inverse of similarity (lower value = higher priority)
                    priorityQueue.push({1.0 - bestSimilarity, neighbor, bestSimilarity});










} // namespace ic}    return regionList;        }        }            }                }} // namespace ic

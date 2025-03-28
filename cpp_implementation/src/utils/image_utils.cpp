#include "utils/image_utils.hpp"
#include <cmath>
#include <stdexcept>
#include <algorithm>

// Include STB image - header-only library for image loading/saving
#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

namespace ic {

Image::Image(int width, int height) 
    : width_(width), height_(height), pixels_(width * height) {
    if (width <= 0 || height <= 0) {
        throw std::invalid_argument("Invalid image dimensions");
    }
}

Image::Image(const std::string& filename) {
    int channels;
    unsigned char* data = stbi_load(filename.c_str(), &width_, &height_, &channels, 3);
    
    if (!data) {
        throw std::runtime_error("Failed to load image: " + filename);
    }
    
    // Convert to our internal format
    pixels_.resize(width_ * height_);
    for (int y = 0; y < height_; ++y) {
        for (int x = 0; x < width_; ++x) {
            int idx = (y * width_ + x) * 3;
            pixels_[getIndex(x, y)] = Color(data[idx], data[idx + 1], data[idx + 2]);
        }
    }
    
    stbi_image_free(data);
}

Image::~Image() {
    // Nothing special to clean up
}

Image Image::createSimilar() const {
    return Image(width_, height_);
}

bool Image::save(const std::string& filename) const {
    // Convert our format to raw bytes
    std::vector<unsigned char> data(width_ * height_ * 3);
    for (int y = 0; y < height_; ++y) {
        for (int x = 0; x < width_; ++x) {
            Color color = getPixel(x, y);
            int idx = (y * width_ + x) * 3;
            data[idx] = color.r;
            data[idx + 1] = color.g;
            data[idx + 2] = color.b;
        }
    }
    
    // Determine file format from extension
    std::string extension = filename.substr(filename.find_last_of(".") + 1);
    std::transform(extension.begin(), extension.end(), extension.begin(), 
                   [](unsigned char c) { return std::tolower(c); });
    
    int result = 0;
    if (extension == "png") {
        result = stbi_write_png(filename.c_str(), width_, height_, 3, data.data(), width_ * 3);
    } 
    else if (extension == "jpg" || extension == "jpeg") {
        result = stbi_write_jpg(filename.c_str(), width_, height_, 3, data.data(), 90); // Quality 90
    } 
    else if (extension == "bmp") {
        result = stbi_write_bmp(filename.c_str(), width_, height_, 3, data.data());
    } 
    else {
        // Default to PNG
        result = stbi_write_png(filename.c_str(), width_, height_, 3, data.data(), width_ * 3);
    }
    
    return result != 0;
}

Color Image::getPixel(int x, int y) const {
    if (x < 0 || x >= width_ || y < 0 || y >= height_) {
        return Color(); // Return black for out of bounds
    }
    return pixels_[getIndex(x, y)];
}

void Image::setPixel(int x, int y, const Color& color) {
    if (x < 0 || x >= width_ || y < 0 || y >= height_) {
        return; // Out of bounds, do nothing
    }
    pixels_[getIndex(x, y)] = color;
}

Color Image::calculateAverageColor(const std::vector<Point>& points, const Image& image) {
    if (points.empty()) {
        return Color();
    }
    
    uint32_t totalR = 0, totalG = 0, totalB = 0;
    
    for (const auto& point : points) {
        Color color = image.getPixel(point.x, point.y);
        totalR += color.r;
        totalG += color.g;
        totalB += color.b;
    }
    
    int count = static_cast<int>(points.size());
    return Color(
        static_cast<uint8_t>(totalR / count),
        static_cast<uint8_t>(totalG / count),
        static_cast<uint8_t>(totalB / count)
    );
}

double colorSimilarity(const Color& c1, const Color& c2) {
    // Calculate Euclidean distance in RGB space
    // Max possible distance in RGB space is sqrt(255^2 * 3) = 441.67...
    const double maxDistance = 441.67;
    
    double dr = static_cast<double>(c1.r) - c2.r;
    double dg = static_cast<double>(c1.g) - c2.g;
    double db = static_cast<double>(c1.b) - c2.b;
    
    double distance = std::sqrt(dr*dr + dg*dg + db*db);
    
    // Convert distance to similarity (1.0 = identical, 0.0 = maximally different)
    return 1.0 - (distance / maxDistance);
}

double colorDistance(const Color& c1, const Color& c2, bool perceptual) {
    if (perceptual) {
        // Apply perceptual weights based on human color perception
        // Human eyes are more sensitive to green, less to blue
        const double weights[3] = {0.299, 0.587, 0.114};
        
        double dr = static_cast<double>(c1.r) - c2.r;
        double dg = static_cast<double>(c1.g) - c2.g;
        double db = static_cast<double>(c1.b) - c2.b;
        
        return std::sqrt(weights[0] * dr*dr + weights[1] * dg*dg + weights[2] * db*db);
    } 
    else {
        // Standard Euclidean distance
        double dr = static_cast<double>(c1.r) - c2.r;
        double dg = static_cast<double>(c1.g) - c2.g;
        double db = static_cast<double>(c1.b) - c2.b;
        
        return std::sqrt(dr*dr + dg*dg + db*db);
    }
}

} // namespace ic

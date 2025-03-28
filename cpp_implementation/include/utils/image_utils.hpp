#pragma once

#include <vector>
#include <cstdint>
#include <string>
#include <memory>
#include <tuple>
#include <functional> // For std::hash

namespace ic {

// RGB color representation
struct Color {
    uint8_t r, g, b;
    
    Color() : r(0), g(0), b(0) {}
    Color(uint8_t r, uint8_t g, uint8_t b) : r(r), g(g), b(b) {}
    
    // Equality operators for caching
    bool operator==(const Color& other) const {
        return r == other.r && g == other.g && b == other.b;
    }
    
    bool operator<(const Color& other) const {
        if (r != other.r) return r < other.r;
        if (g != other.g) return g < other.g;
        return b < other.b;
    }
    
    // Hash function for Color
    size_t hash() const {
        // Simple hash combining r, g, b
        return (static_cast<size_t>(r) << 16) | 
               (static_cast<size_t>(g) << 8) | 
                static_cast<size_t>(b);
    }
};

// Simple point structure
struct Point {
    int x, y;
    
    Point() : x(0), y(0) {}
    Point(int x, int y) : x(x), y(y) {}
    
    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
    
    bool operator<(const Point& other) const {
        if (x != other.x) return x < other.x;
        return y < other.y;
    }
};

// Hash function for Points to use in unordered_set/map
struct PointHash {
    std::size_t operator()(const Point& p) const {
        // Simple hash combining x and y
        return std::hash<int>()(p.x) ^ (std::hash<int>()(p.y) << 1);
    }
};

// Image class
class Image {
public:
    Image(int width, int height);
    Image(const std::string& filename);
    ~Image();
    
    // Create a new image with the same dimensions
    Image createSimilar() const;
    
    // Save to a file
    bool save(const std::string& filename) const;
    
    // Get dimensions
    int getWidth() const { return width_; }
    int getHeight() const { return height_; }
    
    // Get pixel color
    Color getPixel(int x, int y) const;
    
    // Set pixel color
    void setPixel(int x, int y, const Color& color);
    
    // Calculate average color of a set of points
    static Color calculateAverageColor(const std::vector<Point>& points, const Image& image);
    
private:
    int width_;
    int height_;
    std::vector<Color> pixels_;
    
    // Utility to convert between x,y and linear index
    size_t getIndex(int x, int y) const {
        return y * width_ + x;
    }
};

// Color similarity functions
double colorSimilarity(const Color& c1, const Color& c2);
double colorDistance(const Color& c1, const Color& c2, bool perceptual = true);

// Helper class for color pair hash
struct ColorPairHash {
    size_t operator()(const std::pair<Color, Color>& p) const {
        // Combine hashes of both colors
        size_t h1 = p.first.hash();
        size_t h2 = p.second.hash();
        return h1 ^ (h2 << 1);
    }
};

} // namespace ic

// Specialize std::hash for ic::Color
namespace std {
    template<>
    struct hash<ic::Color> {
        size_t operator()(const ic::Color& c) const {
            return c.hash();
        }
    };
}

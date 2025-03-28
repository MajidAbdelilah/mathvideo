#include "image_compressor.hpp"
#include <iostream>
#include <string>
#include <filesystem>
#include <chrono>
#include <iomanip>

// Simple command line arguments parser
class ArgumentParser {
public:
    ArgumentParser(int argc, char** argv) {
        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            
            if (arg.substr(0, 2) == "--") {
                // Handle --key=value format
                size_t equalPos = arg.find('=');
                if (equalPos != std::string::npos) {
                    std::string key = arg.substr(2, equalPos - 2);
                    std::string value = arg.substr(equalPos + 1);
                    args_[key] = value;
                }
                else {
                    // Handle --flag format (boolean)
                    std::string key = arg.substr(2);
                    args_[key] = "true";
                }
            }
            else if (arg.substr(0, 1) == "-") {
                // Handle -k value format
                if (i + 1 < argc && argv[i+1][0] != '-') {
                    std::string key = arg.substr(1);
                    std::string value = argv[++i];
                    args_[key] = value;
                }
                else {
                    // Handle -f format (boolean)
                    std::string key = arg.substr(1);
                    args_[key] = "true";
                }
            }
            else {
                // Positional argument
                positionalArgs_.push_back(arg);
            }
        }
    }
    
    bool hasOption(const std::string& key) const {
        return args_.find(key) != args_.end();
    }
    
    std::string getOption(const std::string& key, const std::string& defaultValue = "") const {
        auto it = args_.find(key);
        if (it != args_.end()) {
            return it->second;
        }
        return defaultValue;
    }
    
    double getDoubleOption(const std::string& key, double defaultValue = 0.0) const {
        auto it = args_.find(key);
        if (it != args_.end()) {
            try {
                return std::stod(it->second);
            }
            catch (...) {
                return defaultValue;
            }
        }
        return defaultValue;
    }
    
    int getIntOption(const std::string& key, int defaultValue = 0) const {
        auto it = args_.find(key);
        if (it != args_.end()) {
            try {
                return std::stoi(it->second);
            }
            catch (...) {
                return defaultValue;
            }
        }
        return defaultValue;
    }
    
    const std::vector<std::string>& getPositionalArgs() const {
        return positionalArgs_;
    }
    
private:
    std::unordered_map<std::string, std::string> args_;
    std::vector<std::string> positionalArgs_;
};

// Simple progress bar for console output
class ProgressBar {
public:
    ProgressBar(const std::string& description = "Processing", int width = 50)
        : description_(description), width_(width), startTime_(std::chrono::steady_clock::now()) {}
    
    void update(double progress, const std::unordered_map<std::string, double>& stats = {}) {
        auto now = std::chrono::steady_clock::now();
        double elapsed = std::chrono::duration<double>(now - startTime_).count();
        
        // Calculate ETA
        double eta = (progress > 0.001) ? (elapsed / progress) - elapsed : 0.0;
        
        // Build the progress bar
        int filled = static_cast<int>(width_ * progress);
        std::string bar;
        for (int i = 0; i < width_; ++i) {
            bar += (i < filled) ? "█" : "░";
        }
        
        // Format percentage
        std::ostringstream percentStr;
        percentStr << std::fixed << std::setprecision(2) << (progress * 100.0);
        
        // Base progress string
        std::ostringstream output;
        output << "\r" << description_ << ": [" << bar << "] " 
               << std::setw(6) << percentStr.str() << "% | "
               << formatTime(elapsed) << " elapsed | ETA: " << formatTime(eta);
        
        // Add additional stats if available
        if (stats.count("processing_rate") > 0) {
            output << " | " << static_cast<int>(stats.at("processing_rate")) << " px/sec";
        }
        if (stats.count("total_regions") > 0) {
            output << " | " << static_cast<int>(stats.at("total_regions")) << " regions";
        }
        
        // Print the progress
        std::cout << output.str() << std::flush;
        
        // Add a newline when complete
        if (progress >= 1.0) {
            std::cout << std::endl;
        }
    }
    
private:
    std::string description_;
    int width_;
    std::chrono::time_point<std::chrono::steady_clock> startTime_;
    
    std::string formatTime(double seconds) const {
        if (seconds < 0) return "Unknown";
        
        int hours = static_cast<int>(seconds) / 3600;
        int minutes = (static_cast<int>(seconds) % 3600) / 60;
        int secs = static_cast<int>(seconds) % 60;
        
        std::ostringstream oss;
        if (hours > 0) {
            oss << hours << "h " << minutes << "m " << secs << "s";
        }
        else if (minutes > 0) {
            oss << minutes << "m " << secs << "s";
        }
        else {
            oss << std::fixed << std::setprecision(1) << seconds << "s";
        }
        return oss.str();
    }
};

// Print usage information
void printUsage(const char* programName) {
    std::cout << "Usage: " << programName << " [options] input_image" << std::endl;
    std::cout << "Options:" << std::endl;
    std::cout << "  -o, --output=FILE           Path to save the compressed image" << std::endl;
    std::cout << "  -t, --threshold=VALUE       Similarity threshold (0.0-1.0) [default: 0.9]" << std::endl;
    std::cout << "  -m, --max-region-size=SIZE  Maximum number of pixels in a region" << std::endl;
    std::cout << "  -a, --algorithm=ALGO        Region-finding algorithm: adaptive or meanshift [default: adaptive]" << std::endl;
    std::cout << "  --no-adaptive               Disable adaptive thresholding (for adaptive algorithm)" << std::endl;
    std::cout << "  --no-progress               Disable progress bar display" << std::endl;
    std::cout << "  -v, --verbose               Enable verbose logging" << std::endl;
    std::cout << "  --report-only               Only generate a report without saving the image" << std::endl;
    std::cout << "  -h, --help                  Show this help message" << std::endl;
}

int main(int argc, char** argv) {
    // Parse command line arguments
    ArgumentParser args(argc, argv);
    
    // Check for help flag
    if (args.hasOption("h") || args.hasOption("help")) {
        printUsage(argv[0]);
        return 0;
    }
    
    // Get positional arguments
    const auto& positionalArgs = args.getPositionalArgs();
    if (positionalArgs.empty()) {
        std::cerr << "Error: No input image specified" << std::endl;
        printUsage(argv[0]);
        return 1;
    }
    
    std::string inputImage = positionalArgs[0];
    
    // Check if input file exists
    if (!std::filesystem::exists(inputImage)) {
        std::cerr << "Error: Input file '" << inputImage << "' not found" << std::endl;
        return 1;
    }
    
    // Get options
    double threshold = args.getDoubleOption("t", args.getDoubleOption("threshold", 0.9));
    int maxRegionSize = args.getIntOption("m", args.getIntOption("max-region-size", 0));
    bool noProgress = args.hasOption("no-progress");
    bool reportOnly = args.hasOption("report-only");
    bool noAdaptive = args.hasOption("no-adaptive");
    
    // Determine algorithm
    ic::ImageCompressor::Algorithm algorithm = ic::ImageCompressor::Algorithm::ADAPTIVE;
    std::string algoStr = args.getOption("a", args.getOption("algorithm", "adaptive"));
    if (algoStr == "meanshift") {
        algorithm = ic::ImageCompressor::Algorithm::MEAN_SHIFT;
    }
    
    // Determine output path
    std::string outputPath;
    if (args.hasOption("o")) {
        outputPath = args.getOption("o");
    } 
    else if (args.hasOption("output")) {
        outputPath = args.getOption("output");
    }
    else {
        // Generate default output path by adding "_compressed" to the input filename
        std::filesystem::path inputPath(inputImage);
        std::filesystem::path stem = inputPath.stem();
        std::filesystem::path extension = inputPath.extension();
        outputPath = stem.string() + "_compressed_" + algoStr + extension.string();
    }
    
    // Create a progress bar
    ProgressBar progressBar("Compressing image (" + algoStr + ")");
    
    // Create a progress callback
    ic::ProgressCallback progressCallback = [&progressBar, noProgress](double progress, 
                                                        const std::unordered_map<std::string, double>& stats) {
        if (!noProgress) {
            progressBar.update(progress, stats);
        }
    };
    
    try {
        // Create the compressor
        ic::ImageCompressor compressor(
            threshold,
            maxRegionSize,
            progressCallback,
            algorithm,
            !noAdaptive
        );
        
        // Load the image
        std::cout << "Loading image: " << inputImage << std::endl;
        if (!compressor.loadImage(inputImage)) {
            std::cerr << "Error: Failed to load image" << std::endl;
            return 1;
        }
        
        // Compress the image
        if (!compressor.compress()) {
            std::cerr << "Error: Compression failed" << std::endl;
            return 1;
        }
        
        // Save the compressed image unless report-only mode is specified
        if (!reportOnly) {
            std::cout << "Saving compressed image to: " << outputPath << std::endl;
            if (!compressor.saveCompressedImage(outputPath)) {
                std::cerr << "Error: Failed to save compressed image" << std::endl;
                return 1;
            }
            std::cout << "Success! Compressed image saved to '" << outputPath << "'" << std::endl;
        }
        else {
            std::cout << "Report-only mode: Image was not saved" << std::endl;
        }
        
        return 0;
    } 
    catch (const std::exception& e) {
        std::cerr << std::endl << "Error during compression: " << e.what() << std::endl;
        return 1;
    }
}

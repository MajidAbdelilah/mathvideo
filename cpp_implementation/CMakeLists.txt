cmake_minimum_required(VERSION 3.10)
project(ImageCompression VERSION 1.0)

# Use C++17 standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Add compile options
if(MSVC)
    add_compile_options(/W4)
else()
    add_compile_options(-Wall -Wextra -pedantic)
endif()

# Include directories
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

# Source files
file(GLOB SOURCES 
    "src/*.cpp"
    "src/algorithms/*.cpp"
    "src/utils/*.cpp"
)

# Executable
add_executable(image_compressor ${SOURCES})

# Find threads package for multi-threading support
find_package(Threads REQUIRED)
target_link_libraries(image_compressor PRIVATE Threads::Threads)

# Install target
install(TARGETS image_compressor DESTINATION bin)

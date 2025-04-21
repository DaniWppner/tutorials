#define rectangle library
add_library(
    rectangle
    rectangle.cpp
    )

#anyone linking to rectangle needs to include this dir to find the .h
target_include_directories(
    rectangle 
    INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}
    )
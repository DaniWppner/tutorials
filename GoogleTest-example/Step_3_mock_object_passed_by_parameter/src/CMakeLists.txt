#define rectangle library
add_library(
    solver_api
    solve_api.cpp
    )

#anyone linking to rectangle needs to include this dir to find the .h
target_include_directories(
    solver_api
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}
    )
# Add the test executable for GoogleTest
add_executable(
    solve_api_test
    test_solve_api.cpp
)

# Link the necessary libraries
target_link_libraries(
    solve_api_test
    solver_api
    GTest::gtest_main
    GTest::gmock_main
)

# Enable testing
include(GoogleTest)
gtest_discover_tests(solve_api_test)

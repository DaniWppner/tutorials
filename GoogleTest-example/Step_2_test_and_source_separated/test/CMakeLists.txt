# Add the test executable for GoogleTest
add_executable(
    rectangle_test
    test_rectangle.cpp
)

# Link the necessary libraries
target_link_libraries(
    rectangle_test
    rectangle
    GTest::gtest_main
)

# Enable testing
include(GoogleTest)
gtest_discover_tests(rectangle_test)

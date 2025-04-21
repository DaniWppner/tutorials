add_executable(test_custom_pass
            ${CMAKE_CURRENT_SOURCE_DIR}/test_custom_pass.cpp)

target_link_libraries(test_custom_pass
                     custom_pass_process
                     GTest::gtest_main
                     GTest::gmock_main)

include(GoogleTest)
gtest_discover_tests(test_custom_pass)
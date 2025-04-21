#include "custom_pass_process.h"
#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include <string>

class MockFunction {
    public:
        MOCK_METHOD(llvm::StringRef, getName, (), (const));
};

TEST(CustomPassTest, CustomPassReturnsNameOfF) {
    MockFunction mock_function;
    CustomPassMethods<MockFunction> runner;

    std::string expected = "foo_and_bar";
    EXPECT_CALL(mock_function, getName()).WillOnce(testing::Return(expected));
    std::string expected_result = "Hello from: " + expected + "\n";

    std::string result = runner.process(mock_function);
    EXPECT_EQ(result, expected_result);
}

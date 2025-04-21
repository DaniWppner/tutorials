#include <gtest/gtest.h>
#include <gmock/gmock.h>
#include "solve_api.h"


TEST(SolveAPITest, HandleRequestReturnsErrorMessageWhenResultIsNeg1) {
    solver_api api();
    EXPECT_CALL(mock_solver, solve(7,8,9)).WillOnce(testing::Return(-1));
    std::string reply = api.handle_solve_request("7-8-9");
    EXPECT_EQ(reply, "There was an error in finding the solution.\n");
  }

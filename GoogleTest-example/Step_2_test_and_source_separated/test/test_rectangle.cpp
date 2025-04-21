#include <gtest/gtest.h>
#include "rectangle.h"


TEST(RectangleTest, PerimeterIsSumOfSides) {
    rectangle rect = rectangle(7,2);
    EXPECT_EQ(rect.get_perimeter(), 18);
  }

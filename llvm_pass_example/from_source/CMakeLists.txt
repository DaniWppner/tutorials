cmake_minimum_required(VERSION 3.17)
project(llvm_example)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

include(FetchContent)
set(FETCHCONTENT_QUIET FALSE)
### Fetch LLVM files (earliest version equal to or later than v9.0.0 available on github is v10.0.0)
# LLVM v10.0.0 tag on github: d32170dbd5b0d54436537b6b75beaf44324e0c28
# LLVM V20.1.2 tag on github: 58df0ef89dd64126512e4ee27b4ac3fd8ddf6247
# LLVM github repo : git@github.com:llvm/llvm-project.git
# LLLVM v9.0.0 tarball url : https://releases.llvm.org/9.0.0/clang+llvm-9.0.0-x86_64-pc-linux-gnu.tar.xz
set(CMAKE_BUILD_TYPE Release)
FetchContent_Declare(
  llvm_project
  GIT_REPOSITORY https://github.com/llvm/llvm-project.git
  GIT_TAG 58df0ef89dd64126512e4ee27b4ac3fd8ddf6247
  GIT_PROGRESS TRUE
)
FetchContent_MakeAvailable(llvm_project)

# Add the main LLVM project to build
add_subdirectory(${llvm_project_SOURCE_DIR}/llvm ${llvm_project_BINARY_DIR}/llvm-build)

# Set up LLVM CMake config
set(LLVM_DIR ${llvm_project_BINARY_DIR}/llvm-build/lib/cmake/llvm)


find_package(LLVM REQUIRED CONFIG)

message(STATUS "Found LLVM ${LLVM_PACKAGE_VERSION}")
message(STATUS "Using LLVMConfig.cmake in: ${LLVM_DIR}")

# Add LLVM headers to link with our own source code
include_directories(${LLVM_INCLUDE_DIRS})
separate_arguments(LLVM_DEFINITIONS_LIST NATIVE_COMMAND ${LLVM_DEFINITIONS})
add_definitions(${LLVM_DEFINITIONS_LIST})

# Add cmake modules to include our pass into llvm
list(APPEND CMAKE_MODULE_PATH "${LLVM_CMAKE_DIR}")
include(AddLLVM)

add_subdirectory(custom_hello)

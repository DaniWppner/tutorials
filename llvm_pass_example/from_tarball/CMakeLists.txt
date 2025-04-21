cmake_minimum_required(VERSION 3.14)
project(llvm_example)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

### Fetch LLVM files (earliest version equal to or later than v9.0.0 available on github is v10.0.0)
# LLVM v10.0.0 tag on github: d32170dbd5b0d54436537b6b75beaf44324e0c28
# LLVM github repo : git@github.com:llvm/llvm-project.git
# LLLVM v9.0.0 tarball url : https://releases.llvm.org/9.0.0/clang+llvm-9.0.0-x86_64-pc-linux-gnu.tar.xz 

# Where to put the downloaded and extracted LLVM binaries
set(LLVM_ROOT "${CMAKE_BINARY_DIR}/llvm")
set(LLVM_ARCHIVE_URL "https://releases.llvm.org/9.0.0/clang+llvm-9.0.0-x86_64-pc-linux-gnu.tar.xz")
set(LLVM_ARCHIVE_PATH "${CMAKE_BINARY_DIR}/llvm.tar.xz")

# Download the tarball if it's not already there
if(NOT EXISTS "${LLVM_ARCHIVE_PATH}")
  message(STATUS "Downloading LLVM binary tarball...")
  file(DOWNLOAD
    ${LLVM_ARCHIVE_URL}
    ${LLVM_ARCHIVE_PATH}
    SHOW_PROGRESS
    EXPECTED_HASH SHA256=616c5f75418c88a72613b6d0a93178028f81357777226869ea6b34c23d08a12d # discovered manually and hard coded
    STATUS DOWNLOAD_STATUS
  )
endif()

# Extract if not already done
if(NOT EXISTS "${LLVM_ROOT}/bin")
  message(STATUS "Extracting LLVM tarball...")
  execute_process(
    COMMAND ${CMAKE_COMMAND} -E tar xzf ${LLVM_ARCHIVE_PATH}
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
  )
  file(GLOB EXTRACTED_DIR "${CMAKE_BINARY_DIR}/clang+llvm-*")
  file(RENAME "${EXTRACTED_DIR}" "${LLVM_ROOT}")
endif()

# Tell CMake where to find LLVMConfig.cmake
set(LLVM_DIR "${LLVM_ROOT}/lib/cmake/llvm")

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

add_subdirectory(hello_llvm_pass)
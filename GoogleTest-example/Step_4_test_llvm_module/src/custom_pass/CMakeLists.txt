add_library(custom_pass_process INTERFACE)
target_include_directories(custom_pass_process INTERFACE ${CMAKE_CURRENT_SOURCE_DIR})

llvm_map_components_to_libnames(llvm_libs Core Support)
target_link_libraries(custom_pass_process INTERFACE ${llvm_libs})

add_llvm_library(custom_pass
                 MODULE 
                 ${CMAKE_CURRENT_SOURCE_DIR}/custom_pass.cpp)

add_llvm_library(hello_llvm MODULE hello_llvm_pass.cpp)
llvm_map_components_to_libnames(llvm_libs core irreader support)
target_link_libraries(hello_llvm ${llvm_libs})
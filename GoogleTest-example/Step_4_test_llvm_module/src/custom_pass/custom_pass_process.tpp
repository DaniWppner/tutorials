template<class llvmFunctionImpl>
std::string CustomPassMethods<llvmFunctionImpl>::process (llvmFunctionImpl &F){
    std::string res = "Hello from: " +  std::string(F.getName()) + "\n";
    return res;
}

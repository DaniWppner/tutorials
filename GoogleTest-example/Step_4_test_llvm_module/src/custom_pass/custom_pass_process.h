#include <string>
#include "llvm/IR/Function.h"


template<class llvmFunctionImpl>
class VCustomPassMethods {
    public:
        VCustomPassMethods(){}
        virtual ~VCustomPassMethods(){}
        virtual std::string process(llvmFunctionImpl &F) = 0;    
};

template<class llvmFunctionImpl>
class CustomPassMethods : public VCustomPassMethods<llvmFunctionImpl> {
    public:
        std::string process (llvmFunctionImpl &F);
};

#include "custom_pass_process.tpp"
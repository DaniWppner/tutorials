#include "llvm/Pass.h"
#include "llvm/IR/Function.h"
#include "llvm/Support/raw_ostream.h"

class HelloWorldPass : public llvm::FunctionPass {
  public:
    static char ID;
    HelloWorldPass() : llvm::FunctionPass(ID) {}
    bool runOnFunction(llvm::Function &F);
};

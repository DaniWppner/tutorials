#include "hello_llvm_pass.h"

bool HelloWorldPass::runOnFunction(llvm::Function &F) {
    llvm::errs() << F.getName() << "\n";
    return false;
}

static llvm::RegisterPass<HelloWorldPass> XXX("hello", "HelloWorldPass", false, false);

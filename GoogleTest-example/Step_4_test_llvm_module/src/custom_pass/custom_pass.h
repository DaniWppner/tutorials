#ifndef CUSTOM_PASS_H
#define CUSTOM_PASS_H

#include "llvm/IR/Function.h"
#include "llvm/IR/PassManager.h"

class CustomThing : public llvm::PassInfoMixin<CustomThing> {
public:
    llvm::PreservedAnalyses run(llvm::Function &F, llvm::FunctionAnalysisManager &AM);
};

#endif // CUSTOM_PASS_H

#include "custom_thing.h"

PreservedAnalyses CustomThing::run(Function &F, FunctionAnalysisManager &) {
    errs() << "Hello from: " << F.getName() << "\n";
    return PreservedAnalyses::all();
}

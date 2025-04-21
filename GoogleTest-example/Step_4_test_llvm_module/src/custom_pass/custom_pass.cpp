#include "custom_pass.h"
#include "custom_pass_process.h"

#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include "llvm/Support/raw_ostream.h"


llvm::PreservedAnalyses CustomThing::run(llvm::Function &F, llvm::FunctionAnalysisManager &) {
    CustomPassMethods<llvm::Function> methods;
    llvm::errs() << methods.process(F);
    return llvm::PreservedAnalyses::all();
}

// New PM plugin registration entry point
extern "C" LLVM_ATTRIBUTE_WEAK ::llvm::PassPluginLibraryInfo llvmGetPassPluginInfo() {
    return {
        LLVM_PLUGIN_API_VERSION, "CustomThing", "v0.1",
        [](llvm::PassBuilder &PB) {
            PB.registerPipelineParsingCallback(
                [](llvm::StringRef Name, llvm::FunctionPassManager &FPM,
                   llvm::ArrayRef<llvm::PassBuilder::PipelineElement>) {
                    if (Name == "customThing") {
                        FPM.addPass(CustomThing());
                        return true;
                    }
                    return false;
                });
        }
    };
}

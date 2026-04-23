#include "llvm/IR/Function.h"
#include "llvm/IR/PassManager.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include "llvm/Support/raw_ostream.h"

/*
 * A simple Function pass using the New Pass Manager
 */
struct HelloWorldPass
    : public llvm::PassInfoMixin<HelloWorldPass>
{

  llvm::PreservedAnalyses
  run(llvm::Function &F, llvm::FunctionAnalysisManager &)
  {
    llvm::errs() << "Hello from function: " << F.getName() << "\n";
    return llvm::PreservedAnalyses::all();
  }
};

/*
 * Plugin registration hook
 * THIS is what -load-pass-plugin looks for
 */
extern "C" LLVM_ATTRIBUTE_WEAK llvm::PassPluginLibraryInfo llvmGetPassPluginInfo() 
{
  return {
      LLVM_PLUGIN_API_VERSION,
      "hello-llvm",
      LLVM_VERSION_STRING,
      [](llvm::PassBuilder &PB)
      {
        PB.registerPipelineParsingCallback(
            [](llvm::StringRef Name,
               llvm::FunctionPassManager &FPM,
               llvm::ArrayRef<llvm::PassBuilder::PipelineElement>)
            {
              if (Name == "hello-llvm")
              {
                FPM.addPass(HelloWorldPass());
                return true;
              }
              return false;
            });
      }};
}

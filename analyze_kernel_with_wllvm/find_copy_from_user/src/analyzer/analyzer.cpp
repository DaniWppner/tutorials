#include "llvm/IR/Function.h"
#include "llvm/IR/PassManager.h"
#include "llvm/Passes/PassBuilder.h"
#include "llvm/Passes/PassPlugin.h"
#include "llvm/Support/raw_ostream.h"


struct CopyFromUserInfo
{
  llvm::Function *Func;
};

struct DetectCopyFromUserAnalysis : public llvm::AnalysisInfoMixin<DetectCopyFromUserAnalysis>
{
  CopyFromUserInfo run(llvm::Module &M, llvm::ModuleAnalysisManager &MAM){
    CopyFromUserInfo Info;
    bool found = false;
    for (llvm::Function &F : M.functions())
    {
      if (F.getName() == "copy_from_user")
      {
        Info.Func = &F;
        llvm::errs() << "INFO: Found function " << F.getName() << "\n";
        found = true;
      }
    }
    if (!found)
    {
      llvm::errs() << "WARNING: copy_from_user not found.\n";
      Info.Func = nullptr;
    }
    return Info;
  }

};

struct FindInFunction : public llvm::PassInfoMixin<FindInFunction> {
  llvm::PreservedAnalyses run(llvm::Function &F,
                              llvm::FunctionAnalysisManager &FAM) {
    auto &MAMProxy = FAM.getResult<llvm::ModuleAnalysisManagerFunctionProxy>(F);
    auto &MAM = MAMProxy.getManager();

    // Fetch the helper function from the module analysis
    auto &Res = MAM.getResult<DetectCopyFromUserAnalysis>(*F.getParent());
    llvm::Function *copyFromUser = Res.Func;

    return llvm::PreservedAnalyses::none();
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
      "copy_from_user_analyzer",
      LLVM_VERSION_STRING,
      // The meat is in a lambda that given a PassBuilder,
      // adds the passes we are interested in
      [](llvm::PassBuilder &PB)
      {
        PB.registerPipelineParsingCallback(
            [](llvm::StringRef Name,
               llvm::ModulePassManager &MAM,
               llvm::ArrayRef<llvm::PassBuilder::PipelineElement>)
            {
              if (Name == "copy_from_user_analyzer")
              {
                MAM.addPass(DetectCopyFromUserAnalysis());
                return true;
              }
              return false;
            });
      }};
}

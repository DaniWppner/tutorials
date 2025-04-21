This is a sample project that defines a function pass and registers it into llvm by including llvm as a dependency in cmake.

This version does so by downloading a pre-compiled tarball of the llvm project, which might be unstable due to differences between the host compiler and the current system.

For example the package `zlib3` is missing from default Ubuntu installations, which makes this project fail to build.

#!/usr/bin/env bash
# Builds the rustsharp compiler from the Roslyn fork as one self-contained executable, ./rustsharp.
# It needs no installed .NET runtime and finds the core library in ./corelib next to itself.
# Usage: tools/build.sh [Debug|Release] [output directory]   (the Dockerfile runs the same)
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
out="${2:-$root}"
cd "$root/roslyn"
dotnet publish src/Compilers/CSharp/rustsharp/rustsharp.csproj -c "${1:-Release}" -r linux-x64 --self-contained \
  -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -p:UseAppHost=true \
  -p:RunAnalyzers=false -p:UseSharedCompilation=false -p:TreatWarningsAsErrors=false \
  -p:EnableXlfLocalization=false -p:GenerateDocumentationFile=false -v:q -nologo \
  -o "$root/roslyn/artifacts/publish/rustsharp"
install -m 755 "$root/roslyn/artifacts/publish/rustsharp/rustsharp" "$out/rustsharp"

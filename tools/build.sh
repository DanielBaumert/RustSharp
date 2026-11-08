#!/usr/bin/env bash
# Builds the rustsharp native compiler from the Roslyn fork. Usage: tools/build.sh [Debug|Release]
set -euo pipefail
cd "$(dirname "$0")/../roslyn"
exec dotnet build src/Compilers/CSharp/rustsharp/rustsharp.csproj -c "${1:-Debug}" \
  -p:RunAnalyzers=false -p:UseSharedCompilation=false -p:TreatWarningsAsErrors=false \
  -p:EnableXlfLocalization=false -p:GenerateDocumentationFile=false -v:q -nologo

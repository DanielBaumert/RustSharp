#!/usr/bin/env bash
# Compiles a program with the fork's regular C# compiler and runs it on real .NET. Usage: run_dotnet.sh file.cs workdir
set -e
root="$(cd "$(dirname "$0")/../.." && pwd)"; src="$1"; out="$2"; mkdir -p "$out"
ref=$(ls -d /usr/share/dotnet/packs/Microsoft.NETCore.App.Ref/*/ref/net*/ | tail -1)
refs=$(ls "$ref"*.dll | sed 's/^/-r:/' | tr '\n' ' ')
dotnet "$root/roslyn/artifacts/bin/csc/Release/net9.0/csc.dll" -nologo -nostdlib -unsafe -nowarn:CS8500 $refs -out:"$out/prog.dll" "$src" >"$out/csc.log" || { cat "$out/csc.log"; exit 1; }
echo '{"runtimeOptions":{"tfm":"net10.0","framework":{"name":"Microsoft.NETCore.App","version":"10.0.0"}}}' > "$out/prog.runtimeconfig.json"
dotnet exec "$out/prog.dll"

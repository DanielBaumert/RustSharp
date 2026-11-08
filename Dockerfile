# Builds the rustsharp compiler: one self-contained executable that needs no installed .NET.
#
#   git clone --recurse-submodules https://github.com/DanielBaumert/RustSharp.git && cd RustSharp
#
# Only the compiler, written to ./rustsharp (needs clang on the host to link programs):
#   docker build --target export --output . .
#   ./rustsharp examples/demo.rscs -o demo && ./demo
#
# Or an image with the compiler and clang:
#   docker build -t rustsharp .
#   docker run --rm -v "$PWD":/work -w /work rustsharp examples/demo.rscs -o demo && ./demo

# ---- build: the Roslyn fork in the submodule `roslyn`, with the SDK its global.json pins
FROM ubuntu:24.04 AS build
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git libicu74 \
 && rm -rf /var/lib/apt/lists/*
COPY roslyn/global.json /tmp/global.json
RUN curl -sSL --retry 5 --retry-all-errors https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh \
 && bash /tmp/dotnet-install.sh --jsonfile /tmp/global.json --install-dir /usr/share/dotnet \
 && rm /tmp/dotnet-install.sh
ENV PATH=/usr/share/dotnet:$PATH DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
WORKDIR /src
COPY roslyn/ roslyn/
COPY tools/build.sh tools/
RUN mkdir /out && tools/build.sh Release /out

# ---- export: `docker build --target export --output . .` writes ./rustsharp
FROM scratch AS export
COPY --from=build /out/rustsharp /rustsharp

# ---- image: the compiler, its core library, and clang to turn LLVM IR into native code
FROM ubuntu:24.04
RUN apt-get update \
 && apt-get install -y --no-install-recommends clang libclang-rt-18-dev libicu74 \
 && rm -rf /var/lib/apt/lists/*
# The same layout as the repository: rustsharp finds corelib/ next to itself.
COPY --from=build /out/rustsharp /opt/rustsharp/rustsharp
COPY corelib/ /opt/rustsharp/corelib/
ENV PATH=/opt/rustsharp:$PATH

# Smoke test: the image can compile and run a program.
COPY examples/demo.rscs /tmp/demo.rscs
RUN rustsharp /tmp/demo.rscs -o /tmp/demo && /tmp/demo > /dev/null && rm -f /tmp/demo /tmp/demo.rscs

WORKDIR /work
ENTRYPOINT ["rustsharp"]

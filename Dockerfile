# The RustSharp compiler with clang in one image.
#
#   git clone --recurse-submodules https://github.com/DanielBaumert/RustSharp.git && cd RustSharp
#   docker build -t rustsharp .
#   docker run --rm -v "$PWD":/work -w /work rustsharp examples/demo.rscs -o demo && ./demo

# ---- build: the Roslyn fork in the submodule `roslyn`
FROM ubuntu:24.04 AS build
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git libicu74 \
 && rm -rf /var/lib/apt/lists/*
# The SDK that roslyn/global.json pins (the sdk images only track the newest feature band),
# and the .NET 9 runtime that rustsharp targets.
COPY roslyn/global.json /tmp/global.json
RUN curl -sSL --retry 5 --retry-all-errors https://dot.net/v1/dotnet-install.sh -o /tmp/dotnet-install.sh \
 && bash /tmp/dotnet-install.sh --jsonfile /tmp/global.json --install-dir /usr/share/dotnet \
 && bash /tmp/dotnet-install.sh --runtime dotnet --channel 9.0 --install-dir /usr/share/dotnet \
 && rm /tmp/dotnet-install.sh
ENV PATH=/usr/share/dotnet:$PATH DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
WORKDIR /src
COPY roslyn/ roslyn/
COPY tools/build.sh tools/
RUN tools/build.sh Release

# ---- runtime: the compiler, its core library, and clang to turn LLVM IR into native code
FROM mcr.microsoft.com/dotnet/runtime:9.0-noble
RUN apt-get update \
 && apt-get install -y --no-install-recommends clang libclang-rt-18-dev \
 && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/roslyn/artifacts/bin/rustsharp/Release/net9.0/ /opt/rustsharp/bin/
COPY corelib/ /opt/rustsharp/corelib/
ENV RUSTSHARP_CORELIB=/opt/rustsharp/corelib
RUN printf '#!/bin/sh\nexec dotnet /opt/rustsharp/bin/rustsharp.dll "$@"\n' > /usr/local/bin/rustsharp \
 && chmod +x /usr/local/bin/rustsharp

# Smoke test: the image can compile and run a program.
COPY examples/demo.rscs /tmp/demo.rscs
RUN rustsharp /tmp/demo.rscs -o /tmp/demo && /tmp/demo > /dev/null && rm -f /tmp/demo /tmp/demo.rscs

WORKDIR /work
ENTRYPOINT ["rustsharp"]

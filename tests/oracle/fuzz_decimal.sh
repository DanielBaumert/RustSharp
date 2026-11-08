#!/usr/bin/env bash
# Differential test: generated decimal arithmetic must print exactly what real .NET prints.
# Usage: tests/oracle/fuzz_decimal.sh workdir [seed...]
root="$(cd "$(dirname "$0")/../.." && pwd)"; w="$1"; shift; mkdir -p "$w"; total=0; bad=0
for seed in "${@:-1}"; do
  python3 "$root/tests/oracle/gen_decimal.py" "$seed" 1500 rustsharp > "$w/d$seed.rscs"
  python3 "$root/tests/oracle/gen_decimal.py" "$seed" 1500 dotnet > "$w/d$seed.net.cs"
  "$root/rustsharp" "$w/d$seed.rscs" -o "$w/d$seed" -O0 || exit 1
  "$w/d$seed" > "$w/d$seed.mine" 2>&1
  "$root/tests/oracle/run_dotnet.sh" "$w/d$seed.net.cs" "$w/net$seed" > "$w/d$seed.net"
  n=$(wc -l < "$w/d$seed.net"); d=$(diff "$w/d$seed.net" "$w/d$seed.mine" | grep -c '^<')
  echo "seed $seed: $n Ergebnisse, $d Abweichungen"; total=$((total+n)); bad=$((bad+d))
done
echo "gesamt: $total Ergebnisse, $bad Abweichungen"; [ "$bad" -eq 0 ]

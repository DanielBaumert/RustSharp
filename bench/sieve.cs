using System;
using System.Collections.Generic;
class Item { public int V; public Item(int v) { V = v; } }
class P
{
    static int Sieve(int n)
    {
        mut var flags = new bool[n + 1];
        mut int count = 0;
        for (mut int i = 2; i <= n; i++)
        {
            if (flags[i]) continue;
            count++;
            for (mut long j = (long)i * i; j <= n; j += i) flags[j] = true;
        }
        return count;
    }
    static long Owned(int rounds)
    {
        mut long sum = 0;
        for (mut int r = 0; r < rounds; r++)
        {
            mut var list = new List<Item>();
            for (mut int i = 0; i < 1000; i++) list.Add(new Item(i));
            foreach (ref readonly var it in list) sum += it.V;
        }
        return sum;
    }
    static void Main()
    {
        Console.WriteLine(Sieve(100000000));
        Console.WriteLine(Owned(20000));
    }
}

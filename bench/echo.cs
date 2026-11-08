using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Sockets;
using System.Threading.Tasks;
class P
{
    const int Connections = 64, Rounds = 20000, Size = 64;
    static async Task<Result<int, IoError>> Echo(TcpStream s)
    {
        mut byte[] buf = new byte[1024];
        while (true)
        {
            int n = (await s.ReadAsync(ref buf))?;
            if (n == 0) return Result<int, IoError>.Ok(0);
            (await s.WriteAsync(in buf, n))?;
        }
    }
    static async Task<Result<int, IoError>> Serve(TcpListener l)
    {
        for (mut int i = 0; i < Connections; i++)
        {
            var conn = (await l.AcceptAsync())?;
            Task.Run(move () => Echo(conn));
        }
        return Result<int, IoError>.Ok(0);
    }
    static async Task<Result<int, IoError>> Client(int port)
    {
        var c = (await TcpStream.ConnectAsync("127.0.0.1", port))?;
        byte[] msg = new byte[Size];
        mut byte[] back = new byte[Size];
        for (mut int r = 0; r < Rounds; r++)
        {
            (await c.WriteAsync(in msg, Size))?;
            mut int got = 0;
            while (got < Size) got += (await c.ReadAsync(ref back))?;
        }
        return Result<int, IoError>.Ok(0);
    }
    static async Task Main()
    {
        var l = TcpListener.Bind("127.0.0.1", 0).Unwrap();
        int port = l.LocalPort;
        Task.Run(move () => Serve(l));
        long start = Runtime.NowMs();
        mut var clients = new List<JoinHandle<Result<int, IoError>>>();
        for (mut int i = 0; i < Connections; i++) clients.Add(Task.Run(move () => Client(port)));
        for (mut int i = 0; i < clients.Count; i++) (await Mem.Take(ref clients[i])).Unwrap().Unwrap();
        long ms = Runtime.NowMs() - start;
        Console.WriteLine(ms);
    }
}

use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::{TcpListener, TcpStream};
const CONNECTIONS: usize = 64;
const ROUNDS: usize = 20000;
const SIZE: usize = 64;
async fn echo(mut s: TcpStream) {
    s.set_nodelay(true).unwrap();
    let mut buf = [0u8; 1024];
    loop {
        let n = s.read(&mut buf).await.unwrap();
        if n == 0 { return; }
        s.write_all(&buf[..n]).await.unwrap();
    }
}
async fn client(port: u16) {
    let mut c = TcpStream::connect(("127.0.0.1", port)).await.unwrap();
    c.set_nodelay(true).unwrap();
    let msg = [0u8; SIZE];
    let mut back = [0u8; SIZE];
    for _ in 0..ROUNDS {
        c.write_all(&msg).await.unwrap();
        let mut got = 0;
        while got < SIZE { got += c.read(&mut back).await.unwrap(); }
    }
}
fn main() {
    let rt = tokio::runtime::Builder::new_multi_thread().worker_threads(8).enable_all().build().unwrap();
    rt.block_on(async {
        let l = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let port = l.local_addr().unwrap().port();
        tokio::spawn(async move {
            for _ in 0..CONNECTIONS {
                let (s, _) = l.accept().await.unwrap();
                tokio::spawn(echo(s));
            }
        });
        let start = std::time::Instant::now();
        let hs: Vec<_> = (0..CONNECTIONS).map(|_| tokio::spawn(client(port))).collect();
        for h in hs { h.await.unwrap(); }
        println!("{}", start.elapsed().as_millis());
    });
}

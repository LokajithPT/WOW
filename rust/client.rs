use std::io::{BufRead, BufReader, Write};
use std::net::TcpStream;
use std::thread::sleep;
use std::time::{Duration, Instant};
use std::env;

fn main() {
    let args: Vec<String> = env::args().collect();
    let addr = &args[1];
    let interval_ms: u64 = args[2].parse().expect("Invalid interval_ms");
    let count: u32 = args.get(3).map(|s| s.parse().unwrap()).unwrap_or(1000);

    let mut stream = TcpStream::connect(addr).expect("Failed to connect");
    stream.set_nodelay(true).ok();
    stream.set_read_timeout(Some(Duration::from_secs(5))).ok();
    let mut reader = BufReader::new(stream.try_clone().unwrap());
    let mut response = String::new();

    for seq in 1u32..=count {
        let send_ts = Instant::now();
        let msg = format!("{}:{}\n", seq, seq);
        stream.write_all(msg.as_bytes()).unwrap();
        stream.flush().unwrap();

        response.clear();
        match reader.read_line(&mut response) {
            Ok(0) | Err(_) => break,
            Ok(_) => {}
        }

        let recv_ts = Instant::now();
        let latency = recv_ts.duration_since(send_ts);
        let latency_ns = latency.as_nanos();

        println!("SEQ:{}:{}", seq, latency_ns);

        if seq < count {
            sleep(Duration::from_millis(interval_ms));
        }
    }
    println!("DONE");
}
